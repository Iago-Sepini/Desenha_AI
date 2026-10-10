"""
svg_cnc_duas_funcoes.py

Duas funções:
1) converter_svg_para_gcode(): transforma um arquivo SVG em G-code e salva.
2) executar_cnc(): envia um arquivo G-code para uma CNC GRBL pela serial.

Instalação (Windows / Python 3.12):
    py -3.12 -m pip install svgpathtools pyserial

Uso:
    from svg_cnc_duas_funcoes import converter_svg_para_gcode, executar_cnc

    gcode = converter_svg_para_gcode("desenho.svg")  # só converte; não move a CNC
    executar_cnc(gcode)                              # envia para COM18

Configuração:
    X máximo = 16 mm; Y máximo = 24 mm
    Área de desenho = 14 x 21 mm, com margens
    Z0 = caneta levantada; Z20 = caneta abaixada
    Porta serial = COM18; baudrate = 115200

IMPORTANTE:
- Confirme que a máquina realmente levanta em Z0 e abaixa em Z20.
- Faça um teste com a caneta longe do papel e mantenha o botão de emergência acessível.
- Feche Candle, UGS ou qualquer programa que esteja usando COM18.
- SVGs devem ter seus elementos convertidos em <path>. O script lê caminhos SVG.
"""

from pathlib import Path
import math
import re
import time

import serial
from svgpathtools import svg2paths2


# ---------------- CONFIGURAÇÃO DA CNC ----------------
MAX_X = 16.0
MAX_Y = 24.0

DRAW_W = 14.0
DRAW_H = 21.0
MARGIN_X = 1.0
MARGIN_Y = 1.5

Z_UP = 0.0
Z_DOWN = 20.0

F_DRAW = 100
F_TRAVEL = 200

SAMPLE_MM = 0.35
PORTA_PADRAO = "COM18"
BAUDRATE_PADRAO = 115200


def _limites_dos_caminhos(paths):
    """Retorna xmin, xmax, ymin, ymax dos caminhos SVG."""
    boxes = [path.bbox() for path in paths]
    return (
        min(b[0] for b in boxes),
        max(b[1] for b in boxes),
        min(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def converter_svg_para_gcode(svg_path, output_path=None):
    """
    FUNÇÃO 1: converte um SVG em G-code, salva o arquivo e retorna seu caminho.

    Exemplo:
        gcode = converter_svg_para_gcode("desenho.svg")
        # Resultado: "desenho.gcode" (não executa a máquina)
    """
    svg_path = Path(svg_path)
    if not svg_path.is_file():
        raise FileNotFoundError(f"Não encontrei o SVG: {svg_path}")

    paths, attributes, svg_attributes = svg2paths2(str(svg_path))
    paths = [p for p in paths if len(p) > 0]
    if not paths:
        raise ValueError(
            "O SVG não contém elementos <path>. No Inkscape, selecione os "
            "objetos e use Caminho > Objeto para caminho, depois salve como SVG."
        )

    xmin, xmax, ymin, ymax = _limites_dos_caminhos(paths)
    width = xmax - xmin
    height = ymax - ymin
    if width <= 0 or height <= 0:
        raise ValueError("O desenho SVG tem largura ou altura inválida.")

    # Ajusta proporcionalmente à área 14 x 21 mm, sem deformar o desenho.
    scale = min(DRAW_W / width, DRAW_H / height)
    drawn_w = width * scale
    drawn_h = height * scale
    offset_x = MARGIN_X + (DRAW_W - drawn_w) / 2
    offset_y = MARGIN_Y + (DRAW_H - drawn_h) / 2

    def transformar(point):
        # Inverte o eixo Y do SVG para coordenadas cartesianas da CNC.
        x = offset_x + (point.real - xmin) * scale
        y = offset_y + (ymax - point.imag) * scale
        return x, y

    lines = [
        "; SVG para G-code - svg_cnc_duas_funcoes.py",
        "; Limites fisicos: X16 mm, Y24 mm",
        "; Area do desenho: 14 x 21 mm",
        "; Z0 = caneta levantada; Z20 = caneta abaixada",
        "G21",
        "G90",
        "G17",
        "G94",
        f"G0 Z{Z_UP:.3f}",
    ]

    for path in paths:
        try:
            length = path.length(error=1e-3)
        except Exception:
            length = 0

        if length <= 0:
            continue

        count = max(2, min(20000, math.ceil(length * scale / SAMPLE_MM)))
        points = [transformar(path.point(i / count)) for i in range(count + 1)]

        for x, y in points:
            if not (0 <= x <= MAX_X and 0 <= y <= MAX_Y):
                raise ValueError(
                    f"Coordenada fora dos limites: X{x:.3f} Y{y:.3f}"
                )

        x_start, y_start = points[0]
        lines.append(f"G0 Z{Z_UP:.3f}")
        lines.append(f"G0 X{x_start:.3f} Y{y_start:.3f} F{F_TRAVEL}")
        lines.append(f"G1 Z{Z_DOWN:.3f} F{F_DRAW}")

        for x, y in points[1:]:
            lines.append(f"G1 X{x:.3f} Y{y:.3f} F{F_DRAW}")

        lines.append(f"G0 Z{Z_UP:.3f}")

    lines.append("M2")

    if output_path is None:
        output_path = svg_path.with_suffix(".gcode")
    output_path = Path(output_path)
    output_path.write_text("\n".join(lines) + "\n", encoding="ascii")

    print(f"G-code salvo em: {output_path}")
    return str(output_path)


def executar_cnc(gcode_path, porta=PORTA_PADRAO, baudrate=BAUDRATE_PADRAO,
                 timeout=5, relatorio=True):
    """
    FUNÇÃO 2: envia G-code para a CNC GRBL pela serial.

    Exemplo:
        executar_cnc("desenho.gcode")  # COM18, 115200 baud
    """
    gcode_path = Path(gcode_path)
    if not gcode_path.is_file():
        raise FileNotFoundError(f"Não encontrei o G-code: {gcode_path}")

    comandos = []
    for raw in gcode_path.read_text(encoding="ascii").splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("("):
            continue
        line = re.sub(r";.*$", "", line).strip()
        if line:
            comandos.append(line)

    if not comandos:
        raise ValueError("O arquivo G-code está vazio.")

    if relatorio:
        print(f"Conectando à CNC em {porta} ({baudrate} baud)...")

    with serial.Serial(
        port=porta,
        baudrate=baudrate,
        timeout=timeout,
        write_timeout=timeout,
    ) as cnc:
        # A placa GRBL pode reiniciar quando a serial abre.
        time.sleep(2)
        cnc.reset_input_buffer()

        if relatorio:
            print(f"Enviando {len(comandos)} comandos...")

        for numero, comando in enumerate(comandos, start=1):
            cnc.write((comando + "\n").encode("ascii"))
            cnc.flush()

            inicio = time.monotonic()
            recebeu_ok = False

            while time.monotonic() - inicio < timeout:
                resposta = cnc.readline().decode(
                    "ascii", errors="replace"
                ).strip()

                if resposta == "ok":
                    recebeu_ok = True
                    break

                if resposta.startswith("error") or resposta.startswith("ALARM"):
                    raise RuntimeError(
                        f"GRBL respondeu '{resposta}' ao comando: {comando}"
                    )

            if not recebeu_ok:
                raise TimeoutError(
                    f"Sem resposta para o comando: {comando}. "
                    "O envio foi interrompido."
                )

            if relatorio and (numero % 25 == 0 or numero == len(comandos)):
                print(f"{numero}/{len(comandos)} comandos enviados")

    if relatorio:
        print("Envio concluído.")


if __name__ == "__main__":
    print("Módulo SVG -> G-code -> CNC")
    print("Importe as funções converter_svg_para_gcode() e executar_cnc()")
    print("Exemplo:")
    print('  gcode = converter_svg_para_gcode("desenho.svg")')
    print("  executar_cnc(gcode)  # usa COM18")