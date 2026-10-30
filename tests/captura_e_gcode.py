"""
tests/captura_e_gcode.py — Script independente de captura por webcam com
opção de escolha entre modo Rosto (Retrato) ou modo Desenho (com limpeza de ruídos).
"""

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
PORTA_SERIAL = "COM20"
BAUDRATE = 115200

MAX_X = 9.0
MAX_Y = 16.0

DRAW_W = 5.0
DRAW_H = 10.0
MARGIN_X = 1.0
MARGIN_Y = 1.5

Z_UP = 0.0
Z_DOWN = 10.0
MAX_Z = 15.0

F_DRAW = 100
F_TRAVEL = 200

SAMPLE_MM = 0.35
COMPRIMENTO_MIN_TRAÇO = 2.0  # Descarta ruidinhos curtos menores que 2 mm


# ==============================================================================
# 1. PROCESSAMENTO DE IMAGEM PARA ROSTO
# ==============================================================================
def extrair_linhas_rosto(frame):
    h, w, _ = frame.shape
    lado = min(h, w)
    x0, y0 = (w - lado) // 2, (h - lado) // 2
    roi = frame[y0:y0 + lado, x0:x0 + lado]

    roi = cv2.resize(roi, (400, 400), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    contraste = clahe.apply(gray)

    blurred = cv2.GaussianBlur(contraste, (5, 5), 0)
    edges = cv2.Canny(blurred, threshold1=60, threshold2=150)

    # Limpeza morfológica para eliminar pontos isolados
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    limpo = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    limpo = cv2.morphologyEx(limpo, cv2.MORPH_OPEN, kernel)

    contornos, _ = cv2.findContours(limpo, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    traços_finais = []
    for c in contornos:
        area = cv2.contourArea(c)
        perimetro = cv2.arcLength(c, True)

        if perimetro < 12.0 or area < 5.0:
            continue

        approx = cv2.approxPolyDP(c, 2.0, False)
        pts = approx.reshape(-1, 2)

        if len(pts) >= 2:
            traços_finais.append(pts)

    return roi, limpo, traços_finais


# ==============================================================================
# 2. PROCESSAMENTO DE IMAGEM PARA DESENHO (Com remoção agressiva de fundo)
# ==============================================================================
def extrair_linhas_desenho(frame):
    h, w, _ = frame.shape
    lado = min(h, w)
    x0, y0 = (w - lado) // 2, (h - lado) // 2
    roi = frame[y0:y0 + lado, x0:x0 + lado]

    roi = cv2.resize(roi, (400, 400), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 15, 6
    )

    kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    
    limpo = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_close)
    limpo = cv2.morphologyEx(limpo, cv2.MORPH_OPEN, kernel_open)  # Apaga os pontinhos soltos

    contornos, _ = cv2.findContours(limpo, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    traços_finais = []
    for c in contornos:
        area = cv2.contourArea(c)
        perimetro = cv2.arcLength(c, True)

        if perimetro < 10.0 or area < 4.0:
            continue

        approx = cv2.approxPolyDP(c, 1.8, False)
        pts = approx.reshape(-1, 2)

        if len(pts) >= 2:
            traços_finais.append(pts)

    return roi, limpo, traços_finais


# ==============================================================================
# 3. GERAÇÃO DE G-CODE DIRETO (Gravado em UTF-8)
# ==============================================================================
def gerar_gcode_direto(tracos, img_size=(400, 400), arquivo_saida="img.gcode"):
    if not tracos:
        raise ValueError("Nenhum traço válido foi encontrado após a limpeza.")

    w_img, h_img = img_size

    if (2 * MARGIN_X + DRAW_W > MAX_X + 1e-9 or 2 * MARGIN_Y + DRAW_H > MAX_Y + 1e-9
            or not (0 <= Z_UP <= MAX_Z) or not (0 <= Z_DOWN <= MAX_Z)):
        raise ValueError("Configuração da CNC inconsistente: área de desenho, margens ou Z passam do limite.")

    scale = min(DRAW_W / w_img, DRAW_H / h_img)
    drawn_w = w_img * scale
    drawn_h = h_img * scale

    offset_x = MARGIN_X + (DRAW_W - drawn_w) / 2.0
    offset_y = MARGIN_Y + (DRAW_H - drawn_h) / 2.0

    def pixel_para_cnc(px, py):
        x = offset_x + (px * scale)
        y = offset_y + ((h_img - py) * scale)
        return x, y

    linhas_gcode = [
        "; G-code gerado para CNC (sem ruídos)",
        f"; Limites fisicos: X{MAX_X:g} mm, Y{MAX_Y:g} mm",
        "G21",
        "G90",
        "G17",
        "G94",
        f"G0 Z{Z_UP:.3f}"
    ]

    total_tracos = 0

    for pts in tracos:
        pontos_mm = [pixel_para_cnc(x, y) for x, y in pts]

        comp_total = 0.0
        for i in range(len(pontos_mm) - 1):
            p1, p2 = pontos_mm[i], pontos_mm[i + 1]
            comp_total += math.hypot(p2[0] - p1[0], p2[1] - p1[1])

        if comp_total < COMPRIMENTO_MIN_TRAÇO:
            continue

        for x, y in pontos_mm:
            if not (-1e-3 <= x <= MAX_X + 1e-3 and -1e-3 <= y <= MAX_Y + 1e-3):
                raise ValueError(f"Ponto fora dos limites físicos: X{x:.2f} Y{y:.2f}")

        x_start, y_start = pontos_mm[0]
        linhas_gcode.append(f"G0 Z{Z_UP:.3f}")
        linhas_gcode.append(f"G0 X{x_start:.3f} Y{y_start:.3f} F{F_TRAVEL}")
        linhas_gcode.append(f"G1 Z{Z_DOWN:.3f} F{F_DRAW}")

        for x, y in pontos_mm[1:]:
            linhas_gcode.append(f"G1 X{x:.3f} Y{y:.3f} F{F_DRAW}")

        linhas_gcode.append(f"G0 Z{Z_UP:.3f}")
        total_tracos += 1

    linhas_gcode.append(f"G0 Z{Z_UP:.3f}")
    linhas_gcode.append(f"G0 X0 Y0 F{F_TRAVEL}")
    linhas_gcode.append("M2")

    # Correção da codificação UTF-8
    Path(arquivo_saida).write_text("\n".join(linhas_gcode) + "\n", encoding="utf-8")
    print(f"[OK] G-code salvo em '{arquivo_saida}' ({total_tracos} traços limpos).")
    return arquivo_saida


# ==============================================================================
# 4. ENVIO SERIAL PARA A CNC (Lido em UTF-8)
# ==============================================================================
def _status(cnc):
    cnc.write(b"?")
    cnc.flush()
    fim = time.monotonic() + 3
    while time.monotonic() < fim:
        r = cnc.readline().decode("utf-8", errors="replace").strip()
        if r.startswith("<"):
            return r
    return ""


def enviar_gcode_cnc(caminho_gcode, porta=PORTA_SERIAL, baudrate=BAUDRATE):
    if not os.path.exists(caminho_gcode):
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_gcode}")

    comandos = []
    # Correção da codificação UTF-8
    for line in Path(caminho_gcode).read_text(encoding="utf-8").splitlines():
        cmd = line.strip()
        if cmd and not cmd.startswith(";") and not cmd.startswith("("):
            comandos.append(cmd)

    print(f"\n[CNC] Conectando na porta {porta} ({baudrate} baud)...")
    try:
        with serial.Serial(porta, baudrate, timeout=5) as cnc:
            time.sleep(2)
            cnc.reset_input_buffer()

            st = _status(cnc)
            print(f"[CNC] Estado inicial: {st or 'sem resposta'}")
            if not st:
                raise RuntimeError("A CNC não respondeu. Confira a porta e se o GRBL está ligado.")
            if st.startswith("<Alarm"):
                raise RuntimeError("A CNC está em ALARME. Destrave ($X) antes de continuar.")

            print(f"[CNC] Enviando {len(comandos)} comandos...")
            for i, cmd in enumerate(comandos, 1):
                cnc.write((cmd + "\n").encode("ascii", errors="ignore"))
                cnc.flush()

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

                if i % 25 == 0 or i == len(comandos):
                    print(f"[CNC] Progresso: {i}/{len(comandos)} comandos enviados.")

        print("[CNC] Desenho concluído com sucesso!")
    except Exception as e:
        print(f"[ERRO CNC] Falha ao enviar para a porta serial: {e}")


# ==============================================================================
# 5. LOOP PRINCIPAL
# ==============================================================================
def main():
    print("\n" + "=" * 60)
    print(" SISTEMA DE IMPRESSÃO CNC - ESCOLHA O MODO")
    print("=" * 60)
    print(" [1] Tirar foto de um ROSTO (Retrato)")
    print(" [2] Tirar foto de um DESENHO (Papel)")
    print(" [Q] Sair")
    print("-" * 60)

    escolha = input("Digite a opção desejada (1, 2 ou Q): ").strip().lower()
    if escolha == '1':
        modo = "rosto"
        print("\n[MODO] Selecionado: Retrato de Rosto.")
    elif escolha == '2':
        modo = "desenho"
        print("\n[MODO] Selecionado: Cópia de Desenho.")
    else:
        print("Encerrando...")
        sys.exit(0)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro: Não foi possível acessar a câmera.")
        sys.exit(1)

    print("\nPosicione o item no centro da câmera.")
    print("Pressione 'ESPAÇO' para capturar ou 'Q' para sair.\n")

    foto_capturada = None
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erro ao ler frame da câmera.")
            break

        frame = cv2.flip(frame, 1)
        frame_limpo = frame.copy()

        h, w, _ = frame.shape
        lado = min(h, w)
        x0, y0 = (w - lado) // 2, (h - lado) // 2
        cv2.rectangle(frame, (x0, y0), (x0 + lado, y0 + lado), (0, 255, 0), 2)
        cv2.putText(
            frame, f"Modo: {modo.upper()} - ESPACO para capturar", (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
        )

        cv2.imshow("Camera - CNC", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            foto_capturada = frame_limpo
            print("\n[CAPTURADO] Foto registrada com sucesso!")
            break
        elif key == ord('q'):
            print("Encerrado pelo usuário.")
            cap.release()
            cv2.destroyAllWindows()
            sys.exit(0)

    cap.release()
    cv2.destroyAllWindows()

    if foto_capturada is not None:
        print(f"[PROCESSANDO] Extraindo traços limpos no modo '{modo}'...")
        if modo == "rosto":
            _, visao_pb, tracos = extrair_linhas_rosto(foto_capturada)
        else:
            _, visao_pb, tracos = extrair_linhas_desenho(foto_capturada)

        cv2.imshow("Pre-visualizacao (Sem Ruido)", visao_pb)
        print("\n" + "-" * 50)
        print("[TECLAS] S = Enviar para CNC | N = Cancelar | Q = Sair")
        print("-" * 50)

        while True:
            k = cv2.waitKey(0) & 0xFF
            if k in (ord('s'), 13):
                try:
                    gcode_file = gerar_gcode_direto(tracos, img_size=(400, 400), arquivo_saida="img.gcode")
                    enviar_gcode_cnc(gcode_file)
                except Exception as e:
                    print(f"\n[ERRO CRÍTICO]: {e}")
                break
            elif k in (ord('n'), ord('q')):
                print("Operação cancelada.")
                break

        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()