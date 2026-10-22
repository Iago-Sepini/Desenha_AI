import os
import sys
import time
import math
from pathlib import Path
import cv2
import numpy as np
import serial

# ==============================================================================
# CONFIGURAÇÕES DA CNC E DA ÁREA DE DESENHO
# ==============================================================================
PORTA_SERIAL = "COM18"  # Troque pela porta da sua CNC (ex: COM3, COM18, /dev/ttyUSB0)
BAUDRATE = 115200

# Limites físicos da CNC (em mm)
MAX_X = 16.0
MAX_Y = 24.0

# Área útil de desenho (em mm)
DRAW_W = 14.0
DRAW_H = 21.0
MARGIN_X = 1.0
MARGIN_Y = 1.5

# Posições do eixo Z (em mm)
Z_UP = 0.0     # Caneta levantada (sem tocar no papel)
Z_DOWN = 20.0  # Caneta abaixada (escrevendo no papel)

# Velocidades de movimento (mm/min)
F_DRAW = 100    # Velocidade desenhando
F_TRAVEL = 200  # Velocidade com caneta no ar

# Resolução de amostragem do traço (mm)
SAMPLE_MM = 0.35
COMPRIMENTO_MIN_TRAÇO = 1.5  # Ignora ruidinhos menores que 1.5 mm


# ==============================================================================
# 1. PROCESSAMENTO DE IMAGEM PARA LINHAS DE ROSTO
# ==============================================================================
def extrair_linhas_rosto(frame):
    """
    Extrai os traços principais do rosto eliminando ruídos geométricos,
    quadrados e triangulinhos indesejados no cabelo ou na pele.
    """
    # 1. Recorta um quadrado central da câmera
    h, w, _ = frame.shape
    lado = min(h, w)
    x0, y0 = (w - lado) // 2, (h - lado) // 2
    roi = frame[y0:y0 + lado, x0:x0 + lado]

    # Redimensiona para uma resolução controlada
    roi = cv2.resize(roi, (400, 400), interpolation=cv2.INTER_AREA)

    # 2. Converte para escala de cinzas
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # 3. CLAHE para realçar olhos, boca e contornos faciais
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    contraste = clahe.apply(gray)

    # 4. Suavização para tirar texturas ásperas da pele
    blurred = cv2.GaussianBlur(contraste, (5, 5), 0)

    # 5. Canny para detectar os traços
    edges = cv2.Canny(blurred, threshold1=50, threshold2=140)

    # 6. Limpeza morfológica para unir traços dos olhos e boca sem criar formas fechadas
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    limpo = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # 7. Extração de Contornos
    contornos, _ = cv2.findContours(limpo, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    traços_finais = []
    for c in contornos:
        # Calcula a área e o comprimento do contorno para filtrar "sujeiras"
        area = cv2.contourArea(c)
        perimetro = cv2.arcLength(c, True)

        # REGRAS DE FILTRAGEM ANTI-RABISCOS:
        # - Descarta contornos microscópicos (pontinhos e triangulinhos de ruído)
        # - Descarta contornos muito pequenos com área fechada excessiva (quadrados)
        if perimetro < 8.0 or area < 3.0:
            continue

        # Simplifica o traço mantendo as linhas firmes
        approx = cv2.approxPolyDP(c, 1.8, False)
        pts = approx.reshape(-1, 2)

        if len(pts) >= 2:
            traços_finais.append(pts)

    return roi, limpo, traços_finais


# ==============================================================================
# 2. GERAÇÃO DE G-CODE DIRETO (img.gcode)
# ==============================================================================
def gerar_gcode_direto(tracos, img_size=(400, 400), arquivo_saida="img.gcode"):
    """
    Converte diretamente as coordenadas de pixels da imagem em coordenadas mm
    da CNC sem passar por arquivos SVG.
    """
    if not tracos:
        raise ValueError("Nenhum traço foi encontrado na imagem.")

    w_img, h_img = img_size

    # Calcula escala proporcional para a área de 14x21mm
    scale = min(DRAW_W / w_img, DRAW_H / h_img)
    drawn_w = w_img * scale
    drawn_h = h_img * scale

    offset_x = MARGIN_X + (DRAW_W - drawn_w) / 2.0
    offset_y = MARGIN_Y + (DRAW_H - drawn_h) / 2.0

    def pixel_para_cnc(px, py):
        # Mapeia X e inverte Y (coordenadas cartesianas da CNC)
        x = offset_x + (px * scale)
        y = offset_y + ((h_img - py) * scale)
        return x, y

    linhas_gcode = [
        "; G-code gerado diretamente para CNC",
        "; Limites fisicos: X16 mm, Y24 mm",
        "; Area de desenho: 14 x 21 mm",
        "G21",         # Unidades em milímetros
        "G90",         # Posicionamento absoluto
        "G17",         # Plano XY
        "G94",         # Avanço em mm/min
        f"G0 Z{Z_UP:.3f}"  # Garante caneta levantada
    ]

    total_tracos = 0

    for pts in tracos:
        pontos_mm = [pixel_para_cnc(x, y) for x, y in pts]

        # Calcula o comprimento total do traço
        comp_total = 0.0
        for i in range(len(pontos_mm) - 1):
            p1, p2 = pontos_mm[i], pontos_mm[i + 1]
            comp_total += math.hypot(p2[0] - p1[0], p2[1] - p1[1])

        # Descarta ruídos muito pequenos
        if comp_total < COMPRIMENTO_MIN_TRAÇO:
            continue

        # Validação de segurança dos limites
        for x, y in pontos_mm:
            if not (0 <= x <= MAX_X and 0 <= y <= MAX_Y):
                raise ValueError(f"Ponto fora dos limites físicos da máquina: X{x:.2f} Y{y:.2f}")

        # Início do traço
        x_start, y_start = pontos_mm[0]
        linhas_gcode.append(f"G0 Z{Z_UP:.3f}")
        linhas_gcode.append(f"G0 X{x_start:.3f} Y{y_start:.3f} F{F_TRAVEL}")
        linhas_gcode.append(f"G1 Z{Z_DOWN:.3f} F{F_DRAW}")

        # Desenha os pontos subsequentes
        for x, y in pontos_mm[1:]:
            linhas_gcode.append(f"G1 X{x:.3f} Y{y:.3f} F{F_DRAW}")

        linhas_gcode.append(f"G0 Z{Z_UP:.3f}")
        total_tracos += 1

    linhas_gcode.append("M2")  # Fim do programa

    Path(arquivo_saida).write_text("\n".join(linhas_gcode) + "\n", encoding="ascii")
    print(f"[OK] G-code salvo em '{arquivo_saida}' ({total_tracos} traços válidos).")
    return arquivo_saida


# ==============================================================================
# 3. ENVIO SERIAL PARA A CNC (GRBL)
# ==============================================================================
def enviar_gcode_cnc(caminho_gcode, porta=PORTA_SERIAL, baudrate=BAUDRATE):
    """Envia o arquivo G-code para a CNC via conexão Serial."""
    if not os.path.exists(caminho_gcode):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_gcode}")

    comandos = []
    for line in Path(caminho_gcode).read_text(encoding="ascii").splitlines():
        cmd = line.strip()
        if cmd and not cmd.startswith(";") and not cmd.startswith("("):
            comandos.append(cmd)

    print(f"\n[CNC] Conectando na porta {porta} ({baudrate} baud)...")
    try:
        with serial.Serial(porta, baudrate, timeout=5) as cnc:
            time.sleep(2)  # Aguarda reinicialização do GRBL
            cnc.reset_input_buffer()

            print(f"[CNC] Enviando {len(comandos)} comandos...")
            for i, cmd in enumerate(comandos, 1):
                cnc.write((cmd + "\n").encode("ascii"))
                cnc.flush()

                # Aguarda confirmação 'ok' do GRBL
                inicio = time.monotonic()
                ok = False
                while time.monotonic() - inicio < 5:
                    resp = cnc.readline().decode("ascii", errors="replace").strip()
                    if resp == "ok":
                        ok = True
                        break
                    if resp.startswith("error") or resp.startswith("ALARM"):
                        raise RuntimeError(f"Erro GRBL no comando '{cmd}': {resp}")

                if not ok:
                    raise TimeoutError(f"Sem resposta para o comando: {cmd}")

                if i % 20 == 0 or i == len(comandos):
                    print(f"[CNC] Progresso: {i}/{len(comandos)} comandos enviados.")

        print("[CNC] Desenho concluído com sucesso!")
    except Exception as e:
        print(f"[ERRO CNC] Falha ao enviar para a porta serial: {e}")


# ==============================================================================
# 4. LOOP PRINCIPAL DE CAPTURA E INTERAÇÃO
# ==============================================================================
def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro: Não foi possível acessar a câmera.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("SISTEMA DE RETRATO CNC")
    print("Posicione o rosto no centro da tela.")
    print("Pressione 'ESPAÇO' para capturar a foto.")
    print("Pressione 'Q' para sair.")
    print("=" * 60 + "\n")

    while True:
        foto_capturada = None
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Erro ao ler frame da câmera.")
                cap.release()
                sys.exit(1)

            # Inverte espelhado para facilitar o enquadramento
            frame = cv2.flip(frame, 1)

            # 1. Pega a foto PURA antes de desenhar qualquer texto por cima
            frame_limpo = frame.copy()

            # Desenha guia visual e texto APENAS na tela de exibição da câmera
            h, w, _ = frame.shape
            lado = min(h, w)
            x0, y0 = (w - lado) // 2, (h - lado) // 2
            cv2.rectangle(frame, (x0, y0), (x0 + lado, y0 + lado), (0, 255, 0), 2)
            cv2.putText(
                frame, "Pressione ESPACO para capturar", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2
            )

            cv2.imshow("Camera - Retrato CNC", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):  # Tecla ESPAÇO
                # Salva a cópia limpa (sem o retângulo verde e sem o texto escritos)
                foto_capturada = frame_limpo
                print("\n[CAPTURADO] Foto registrada com sucesso!")
                break
            elif key == ord('q'):
                print("Encerrado pelo usuário.")
                cap.release()
                cv2.destroyAllWindows()
                sys.exit(0)

        # Fecha a janela da câmera temporariamente para mostrar o resultado
        cv2.destroyAllWindows()

        print("[PROCESSANDO] Extraindo detalhes do rosto para vetores...")
        _, visao_preto_branco, tracos = extrair_linhas_rosto(foto_capturada)

        # Exibe a imagem processada em preto e branco
        cv2.imshow("Pre-visualizacao (Preto e Branco)", visao_preto_branco)
        print("\n" + "-" * 50)
        print("[TECLAS] S = imprimir na CNC | N = tirar outra foto | Q = sair")
        print("-" * 50)

        # Pergunta ao operador pela própria janela do OpenCV (sem input(),
        # para não competir com o console do main.py)
        while True:
            k = cv2.waitKey(0) & 0xFF
            if k in (ord('s'), 13):  # S ou Enter
                opcao = 's'
                break
            elif k == ord('n'):
                opcao = 'n'
                break
            elif k == ord('q'):
                print("Encerrado pelo usuário.")
                cap.release()
                cv2.destroyAllWindows()
                sys.exit(0)

        cv2.destroyAllWindows()

        if opcao == 's':
            try:
                # Gera o G-code em 'img.gcode' e envia para a CNC
                gcode_file = gerar_gcode_direto(tracos, img_size=(400, 400), arquivo_saida="img.gcode")
                enviar_gcode_cnc(gcode_file)
            except Exception as e:
                print(f"\n[ERRO CRÍTICO]: {e}")
            # Termina após imprimir: o controle volta para o main.py (Max)
            break
        else:
            print("\n[INFO] Descartando foto. Retornando para nova captura...\n")
            continue

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()