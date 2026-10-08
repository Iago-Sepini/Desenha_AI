import os

import cv2
import numpy as np
import svgwrite

COMPRIMENTO_MIN = 15   # ignora contornos com perímetro menor que isso (px)
EPSILON = 1.2          # simplificação dos pontos em px (maior = menos pontos)
ESPESSURA = 2          # largura do traço no SVG


def _caminho_reto(pts):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"


def _caminho_suave(pts):
    """Contorno fechado -> curvas Bézier cúbicas (Catmull-Rom)."""
    n = len(pts)
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = p1 + (p2 - p0) / 6.0
        c2 = p2 - (p3 - p1) / 6.0
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d + " Z"


def _ordenar(lista):
    """Ordena pelo vizinho mais próximo e gira cada contorno para começar perto
    do ponto anterior: o robô percorre menos distância com a caneta levantada."""
    restantes, ordem, atual = list(lista), [], np.zeros(2)
    while restantes:
        i = min(range(len(restantes)),
                key=lambda k: np.min(np.linalg.norm(restantes[k] - atual, axis=1)))
        pts = restantes.pop(i)
        j = int(np.argmin(np.linalg.norm(pts - atual, axis=1)))
        pts = np.roll(pts, -j, axis=0)
        ordem.append(pts)
        atual = pts[0]
    return ordem


def gerar_svg(contornos, tamanho, caminho="desenho.svg", suavizar=True, fundo=True):
    """Contornos do OpenCV -> arquivo SVG. Devolve o caminho, ou None se não há traços."""
    lista = []
    for c in contornos:
        if cv2.arcLength(c, True) < COMPRIMENTO_MIN:
            continue
        c = cv2.approxPolyDP(c, EPSILON, True)
        pts = c.reshape(-1, 2).astype(np.float64)
        if len(pts) >= 3:
            lista.append(pts)
    if not lista:
        return None

    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)

    dwg = svgwrite.Drawing(caminho, size=(f"{tamanho}px", f"{tamanho}px"),
                           viewBox=f"0 0 {tamanho} {tamanho}")
    if fundo:
        dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill="white"))

    for pts in _ordenar(lista):
        d = _caminho_suave(pts) if suavizar else _caminho_reto(pts)
        dwg.add(dwg.path(d=d, stroke="black", fill="none", stroke_width=ESPESSURA,
                         stroke_linejoin="round", stroke_linecap="round"))
    dwg.save()
    return caminho