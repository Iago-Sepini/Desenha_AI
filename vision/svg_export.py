# vision/svg_export.py
"""
Contornos -> SVG de LINHA ÚNICA (centro do traço) para a CNC desenhar.

Pipeline:
  contornos -> máscara de tinta -> esqueleto (centro do traço) -> caminhos (1 passada)
  -> poda de rebarbas -> simplifica -> ordena (menos deslocamento da caneta) -> SVG
"""

import os

import cv2
import numpy as np
import svgwrite

COMPRIMENTO_MIN = 4     # caminhos ligados ao desenho menores que isso (px) são rebarba e somem
PODA_RAMO = 6           # ramos soltos curtos (px) saindo de um traço = ruído do esqueleto
EPSILON = 0.7           # simplificação dos caminhos (px); maior = menos pontos, CNC mais rápida
ESPESSURA = 2           # espessura padrão do traço no SVG (só se não der para medir)
TAM_PONTO = 1.5         # meia-largura (px) do risquinho que representa um ponto (olho etc.)

_VIZ = [(-1, 0), (0, -1), (0, 1), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]  # 4-vizinhos primeiro


# ---------------------------------------------------------------- esqueleto
def esqueletizar(binaria):
    """Esqueleto de 1 px (0/255). skimage (está no requirements) > ximgproc > fallback."""
    try:
        from skimage.morphology import skeletonize
        return (skeletonize(binaria > 0).astype(np.uint8)) * 255
    except Exception:
        pass
    try:
        return cv2.ximgproc.thinning(binaria, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)
    except Exception:
        skel = np.zeros(binaria.shape, np.uint8)
        el = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        img = binaria.copy()
        while cv2.countNonZero(img):
            er = cv2.erode(img, el)
            skel = cv2.bitwise_or(skel, cv2.subtract(img, cv2.dilate(er, el)))
            img = er
        return skel


# ---------------------------------------------------------------- percorrer o esqueleto
def _percorrer(skel):
    """Percorre cada pixel do esqueleto UMA vez e devolve (caminhos, fechados, soltos).

    caminhos: lista de arrays (N,2) com (x, y)
    fechados: lista de bool (o caminho dá a volta e fecha)
    soltos:   lista de bool (componente isolado, ou seja, um desenho de verdade, não rebarba)
    """
    ys, xs = np.nonzero(skel)
    pix = set(zip(ys.tolist(), xs.tolist()))
    if not pix:
        return [], [], []

    def vizinhos(p):
        return [(p[0] + dy, p[1] + dx) for dy, dx in _VIZ if (p[0] + dy, p[1] + dx) in pix]

    visitado = set()
    caminhos, fechados, soltos = [], [], []

    def andar(inicio, anterior=None):
        """Anda pelo esqueleto escolhendo sempre a continuação mais reta."""
        cam = [inicio]
        visitado.add(inicio)
        atual, dir_ant = inicio, None
        if anterior is not None:
            dir_ant = np.array([inicio[0] - anterior[0], inicio[1] - anterior[1]], float)
        while True:
            livres = [v for v in vizinhos(atual) if v not in visitado]
            if not livres:
                break
            if dir_ant is None:
                prox = livres[0]
            else:
                def reta(v):
                    d = np.array([v[0] - atual[0], v[1] - atual[1]], float)
                    return d @ dir_ant / (np.linalg.norm(d) * np.linalg.norm(dir_ant))
                prox = max(livres, key=reta)
            dir_ant = np.array([prox[0] - atual[0], prox[1] - atual[1]], float)
            visitado.add(prox)
            cam.append(prox)
            atual = prox
        return cam

    def guardar(cam, solto, anterior=None):
        # fecha se a ponta voltou a encostar no começo (círculo, olho oco...)
        fechado = (anterior is None and len(cam) > 6 and
                   max(abs(cam[0][0] - cam[-1][0]), abs(cam[0][1] - cam[-1][1])) <= 1)
        pts = np.array([(x, y) for y, x in cam], float)
        if anterior is not None:                       # liga o ramo ao ponto de onde saiu
            pts = np.vstack([[anterior[1], anterior[0]], pts])
        caminhos.append(pts)
        fechados.append(fechado)
        soltos.append(solto)

    # 1) começa pelas pontas (pixels com 1 vizinho): traços abertos
    for p in sorted(pix):
        if p not in visitado and len(vizinhos(p)) == 1:
            guardar(andar(p), solto=True)

    # 2) ramos que saem do meio de traços já percorridos (cruzamentos)
    achou = True
    while achou:
        achou = False
        for p in sorted(pix - visitado):
            ligado = [v for v in vizinhos(p) if v in visitado]
            if ligado:
                guardar(andar(p, ligado[0]), solto=False, anterior=ligado[0])
                achou = True
                break

    # 3) o que sobrou são laços fechados sem ponta (círculo, pontos isolados)
    for p in sorted(pix - visitado):
        if p not in visitado:
            guardar(andar(p), solto=True)

    return caminhos, fechados, soltos


def _comprimento(pts, fechado):
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1).sum() if len(pts) > 1 else 0.0
    return seg + (np.linalg.norm(pts[0] - pts[-1]) if fechado and len(pts) > 1 else 0.0)


def _tinta(contornos, tamanho):
    """Região de tinta REAL: preenchimento par-ímpar dos contornos (buracos continuam buracos)."""
    tinta = np.zeros((tamanho, tamanho), np.uint8)
    for c in contornos:
        tmp = np.zeros_like(tinta)
        cv2.drawContours(tmp, [c], -1, 255, thickness=cv2.FILLED)
        tinta ^= tmp
    return tinta


def _estender(pts, d):
    """Alonga a ponta final do traço em d px (o esqueleto encurta as pontas em ~metade da espessura)."""
    k = min(len(pts) - 1, 4)
    v = pts[-1] - pts[-1 - k]
    n = np.linalg.norm(v)
    return np.vstack([pts, pts[-1] + v / n * d]) if n > 0 else pts


def extrair_tracos(contornos, tamanho=300):
    """Contornos -> (lista de (pontos(N,2), fechado), largura_do_traco_px). Linha única."""
    tinta = _tinta(contornos, tamanho)
    if not tinta.any():
        return [], float(ESPESSURA)

    # espessura real do traço de caneta (mediana da distância ao fundo ao longo do esqueleto)
    dist = cv2.distanceTransform(tinta, cv2.DIST_L2, 3)
    sk0 = esqueletizar(tinta) > 0
    raio = float(np.median(dist[sk0])) if sk0.any() else 1.0
    raio = max(raio, 1.0)

    # "bolas" (maçaneta, olho, miolo cheio): partes mais grossas que o traço
    d_bola = int(round(raio * 2 * 1.8)) | 1
    bolas = cv2.morphologyEx(tinta, cv2.MORPH_OPEN,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d_bola, d_bola)))
    tracos = []
    n_cc, rot = cv2.connectedComponents(bolas)
    for i in range(1, n_cc):
        comp = (rot == i).astype(np.uint8) * 255
        k = int(round(raio))
        nucleo = cv2.erode(comp, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1)))
        cs, _ = cv2.findContours(nucleo if nucleo.any() else comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not cs:
            continue
        c = max(cs, key=cv2.contourArea)
        pts = c.reshape(-1, 2).astype(np.float32)
        if len(pts) >= 6:                              # contorno fechado da bola
            s = cv2.approxPolyDP(pts.reshape(-1, 1, 2), EPSILON, True).reshape(-1, 2).astype(float)
            if len(s) >= 3:
                tracos.append((s, True))
                continue
        cx = pts.mean(axis=0)                           # bola minúscula: um ponto
        tracos.append((np.array([cx - [TAM_PONTO, 0], cx + [TAM_PONTO, 0]], float), False))

    # traços finos: o que sobra tirando as bolas -> esqueleto -> caminhos
    finos = cv2.bitwise_and(tinta, cv2.bitwise_not(bolas))
    caminhos, fechados, soltos = _percorrer(esqueletizar(finos))
    for pts, fechado, solto in zip(caminhos, fechados, soltos):
        comp = _comprimento(pts, fechado)
        if solto and comp < COMPRIMENTO_MIN:
            c = pts.mean(axis=0)
            tracos.append((np.array([c - [TAM_PONTO, 0], c + [TAM_PONTO, 0]]), False))
            continue
        if not solto and comp < max(PODA_RAMO, raio * 2):
            continue                                   # rebarba do esqueleto
        if not fechado and len(pts) >= 2:              # devolve o que o esqueleto encurtou
            if solto:
                pts = _estender(_estender(pts[::-1], raio * 0.8)[::-1], raio * 0.8)
            else:
                pts = _estender(pts, raio * 0.8)
        if len(pts) >= 3:
            s = cv2.approxPolyDP(pts.astype(np.float32).reshape(-1, 1, 2), EPSILON, fechado)
            pts = s.reshape(-1, 2).astype(float)
        if len(pts) >= 2:
            tracos.append((pts, fechado))
    return tracos, 2.0 * raio


# ---------------------------------------------------------------- caminhos SVG
def _caminho_reto(pts, fechado=True):
    cmd = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return cmd + " Z" if fechado else cmd


def _caminho_suave(pts, fechado=True):
    n = len(pts)
    if n < 3:
        return _caminho_reto(pts, fechado=fechado)

    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    limite = n if fechado else n - 1

    for i in range(limite):
        p0 = pts[i - 1] if i > 0 or fechado else pts[0]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (i + 2) < n or fechado else pts[-1]

        c1 = p1 + (p2 - p0) / 6.0
        c2 = p2 - (p3 - p1) / 6.0
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"

    return d + " Z" if fechado else d


def _ordenar(lista):
    """Vizinho mais próximo: a caneta começa sempre perto de onde parou.
    Traços abertos podem ser percorridos de trás para frente; fechados começam no ponto mais perto."""
    restantes, ordem, atual = list(lista), [], np.zeros(2)
    while restantes:
        melhor, melhor_d = 0, float("inf")
        for k, (pts, fechado) in enumerate(restantes):
            d = (np.min(np.linalg.norm(pts - atual, axis=1)) if fechado
                 else min(np.linalg.norm(pts[0] - atual), np.linalg.norm(pts[-1] - atual)))
            if d < melhor_d:
                melhor, melhor_d = k, d
        pts, fechado = restantes.pop(melhor)
        if fechado:
            pts = np.roll(pts, -int(np.argmin(np.linalg.norm(pts - atual, axis=1))), axis=0)
        elif np.linalg.norm(pts[-1] - atual) < np.linalg.norm(pts[0] - atual):
            pts = pts[::-1]
        ordem.append((pts, fechado))
        atual = pts[0] if fechado else pts[-1]
    return ordem


# ---------------------------------------------------------------- API (mesma de antes)
def gerar_svg(contornos, tamanho=300, caminho="desenho.svg", suavizar=True, fundo=True):
    """Gera o SVG com traço de linha única. Mesma assinatura de antes."""
    if contornos is None or len(contornos) == 0:
        return None

    tracos, largura = extrair_tracos(contornos, tamanho)
    if not tracos:
        return None

    pasta = os.path.dirname(caminho)
    if pasta:
        os.makedirs(pasta, exist_ok=True)

    dwg = svgwrite.Drawing(caminho, size=(f"{tamanho}px", f"{tamanho}px"),
                           viewBox=f"0 0 {tamanho} {tamanho}")
    if fundo:
        dwg.add(dwg.rect(insert=(0, 0), size=("100%", "100%"), fill="white"))

    for pts, fechado in _ordenar(tracos):
        d = _caminho_suave(pts, fechado) if suavizar else _caminho_reto(pts, fechado)
        dwg.add(dwg.path(d=d, stroke="black", fill="none", stroke_width=round(largura, 1),
                         stroke_linejoin="round", stroke_linecap="round"))

    dwg.save()
    return caminho