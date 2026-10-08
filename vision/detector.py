"""
DETECTOR DE DESENHOS (usa o model.h5 e o classes.json gerados pelo treinar.py)

Como módulo (no seu código principal):

    from detector import Detector, desenhar
    from config_camera import abrir_camera, ler_frame, recortar_quadrado

    det = Detector()                          # carrega model.h5 + classes.json
    cap, cfg = abrir_camera()
    while True:
        frame = ler_frame(cap, cfg)
        roi, caixa = recortar_quadrado(frame, cfg)
        r = det.detectar(roi)                 # <- faz tudo
        if r.mudou:                           # True só quando o resultado estabiliza e muda
            print(r.texto())                  # ex.: "gato (87%)"
        # r.nome       -> "gato" (ou None se não reconheceu)
        # r.confianca  -> 0.87
        # r.top        -> [("gato", 0.87), ("tigre", 0.06), ...]
        # r.contornos  -> contornos dos traços pretos (use no gerar_svg)
        # r.estavel    -> último nome confirmado (não pisca)

Como programa (demo com câmera, contornos, debug e texto no terminal):
    py -3.10 detector.py
    py -3.10 detector.py --cam 1 --sem-debug

Teclas: q = sair | d = debug | c = contornos | s = salvar print
"""
import argparse
import json
import os
import sys
import time
import unicodedata
from collections import deque
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import cv2
import numpy as np

# ------------------------------------------------------------------ ajustes
MIN_CONFIDENCE = 0.55    # abaixo disso o resultado é "não reconheci"
MIN_INK_PIXELS = 60      # mínimo de tinta para considerar que há desenho
MIN_CONTOUR_AREA = 40    # ignora manchas de tinta menores que isso (ruído)
SMOOTH_FRAMES = 6        # média das últimas N previsões
STABLE_FRAMES = 8        # frames iguais seguidos para "confirmar" um resultado

# --- detecção dos traços pretos
LIMIAR_TINTA = 170       # 0-255: pixel mais escuro que isso (vs. papel) é tinta. Menor = mais exigente
SO_PRETO = True          # ignora tinta colorida (caneta azul/vermelha)
SATURACAO_MAX = 120      # acima disso o traço é considerado colorido
MARGEM_BORDA = 0.02      # fração do recorte descartada nas bordas (sombras, moldura)


def sem_acento(texto):
    """cv2.putText não desenha acentos."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


# ------------------------------------------------------------------ traços pretos
def extrair_tinta(roi):
    """Imagem do papel -> máscara (255 = traço preto, 0 = papel), mesmo tamanho do recorte."""
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Estima o fundo (papel): o fechamento remove os traços escuros finos e
    # o blur suaviza. Dividir pelo fundo elimina sombra e luz irregular.
    k = max(15, (min(h, w) // 8) | 1)
    fundo = cv2.morphologyEx(gray, cv2.MORPH_CLOSE,
                             cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    fundo = cv2.GaussianBlur(fundo, (0, 0), k / 3)
    norm = cv2.divide(gray, np.maximum(fundo, 1), scale=255)
    norm = cv2.GaussianBlur(norm, (3, 3), 0)
    tinta = ((norm < LIMIAR_TINTA).astype(np.uint8)) * 255

    # só traço preto: descarta o que tem cor
    if SO_PRETO:
        sat = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)[:, :, 1]
        tinta[sat > SATURACAO_MAX] = 0

    # descarta as bordas do recorte
    m = int(min(h, w) * MARGEM_BORDA)
    if m > 0:
        tinta[:m, :] = 0
        tinta[-m:, :] = 0
        tinta[:, :m] = 0
        tinta[:, -m:] = 0

    # fecha furinhos no traço e remove pontos soltos (ruído)
    tinta = cv2.morphologyEx(tinta, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, rotulos, stats, _ = cv2.connectedComponentsWithStats(tinta, connectivity=8)
    limpa = np.zeros_like(tinta)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= MIN_CONTOUR_AREA:
            limpa[rotulos == i] = 255
    return limpa


# ------------------------------------------------------------------ pré-processamento
def preprocessar(roi):
    """Imagem do papel -> (bitmap 28x28 ou None, máscara de tinta, contornos).
    Traços brancos em fundo preto, como no QuickDraw. Não precisa de TensorFlow."""
    tinta = extrair_tinta(roi)

    contornos, _ = cv2.findContours(tinta, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contornos = [c for c in contornos if cv2.contourArea(c) >= MIN_CONTOUR_AREA]

    ys, xs = np.nonzero(tinta)
    if len(xs) < MIN_INK_PIXELS:
        return None, tinta, contornos

    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    recorte = tinta[y0:y1 + 1, x0:x1 + 1]

    # quadrado e centralizado
    h, w = recorte.shape
    lado = max(h, w)
    quadrado = np.zeros((lado, lado), np.uint8)
    quadrado[(lado - h) // 2:(lado - h) // 2 + h,
             (lado - w) // 2:(lado - w) // 2 + w] = recorte

    # engrossa o traço (no QuickDraw o traço é grosso em 28x28)
    k = max(3, lado // 12)
    quadrado = cv2.dilate(quadrado, np.ones((k, k), np.uint8))

    pequeno = cv2.resize(quadrado, (24, 24), interpolation=cv2.INTER_AREA)
    bitmap = np.zeros((28, 28), np.uint8)
    bitmap[2:26, 2:26] = pequeno
    return bitmap, tinta, contornos


# ------------------------------------------------------------------ resultado
@dataclass
class Resultado:
    nome: Optional[str] = None                  # classe reconhecida (None = não reconheci)
    confianca: float = 0.0                      # 0.0 a 1.0 da melhor classe
    top: List[Tuple[str, float]] = field(default_factory=list)   # 3 melhores
    contornos: list = field(default_factory=list)
    bitmap: Any = None                          # 28x28 que foi para a IA
    tinta: Any = None                           # máscara de tinta (debug)
    estavel: Optional[str] = None               # último nome confirmado
    mudou: bool = False                         # True no frame em que o estável mudou

    @property
    def tem_desenho(self):
        return self.bitmap is not None

    def texto(self):
        if not self.tem_desenho:
            return "Nenhum desenho"
        if self.nome is None:
            if self.top:
                return f"Não reconheci (talvez {self.top[0][0]} {self.top[0][1] * 100:.0f}%)"
            return "Não reconheci"
        return f"{self.nome} ({self.confianca * 100:.0f}%)"


# ------------------------------------------------------------------ detector
class Detector:
    def __init__(self, modelo="model.h5", classes="classes.json",
                 confianca_min=MIN_CONFIDENCE, suavizar=SMOOTH_FRAMES,
                 frames_estavel=STABLE_FRAMES):
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
        from tensorflow import keras   # import aqui: preprocessar() funciona sem TensorFlow

        if not (os.path.exists(modelo) and os.path.exists(classes)):
            raise FileNotFoundError(
                f"Não achei {modelo} e/ou {classes}. Rode antes: py -3.10 treinar.py")
        self.modelo = keras.models.load_model(modelo)
        with open(classes, encoding="utf-8") as f:
            self.classes = json.load(f)

        saidas = self.modelo.output_shape[-1]
        if saidas != len(self.classes):
            raise ValueError(
                f"O modelo tem {saidas} saídas mas o classes.json tem {len(self.classes)} nomes. "
                "Eles precisam ser da MESMA execução de treino.")

        self.confianca_min = confianca_min
        self.frames_estavel = frames_estavel
        self._hist = deque(maxlen=suavizar)
        self._cand = None
        self._cand_n = 0
        self._ultimo = None

    def reset(self):
        self._hist.clear()
        self._cand, self._cand_n, self._ultimo = None, 0, None

    def detectar(self, roi):
        """Recebe o recorte (imagem BGR do quadrado) e devolve um Resultado."""
        bitmap, tinta, contornos = preprocessar(roi)
        r = Resultado(contornos=contornos, bitmap=bitmap, tinta=tinta)

        if bitmap is None:
            self._hist.clear()
        else:
            x = (bitmap.astype("float32") / 255.0).reshape(1, 28, 28, 1)
            self._hist.append(self.modelo(x, training=False).numpy()[0])
            probs = np.mean(self._hist, axis=0)
            ordem = np.argsort(probs)[::-1][:3]
            r.top = [(self.classes[i], float(probs[i])) for i in ordem]
            melhor, conf = r.top[0]
            r.confianca = conf
            r.nome = melhor if conf >= self.confianca_min else None

        # confirma o resultado só depois de N frames iguais (evita piscar)
        if r.nome == self._cand:
            self._cand_n += 1
        else:
            self._cand, self._cand_n = r.nome, 1
        if self._cand_n == self.frames_estavel and self._cand != self._ultimo:
            self._ultimo = self._cand
            r.mudou = True
        r.estavel = self._ultimo
        return r


# ------------------------------------------------------------------ desenho (opcional)
def desenhar(frame, r, caixa, mostrar_contornos=True):
    """Desenha quadrado, contornos, nome e top-3 em cima do frame (modifica o frame)."""
    x0, y0, lado = caixa
    cv2.rectangle(frame, (x0, y0), (x0 + lado, y0 + lado), (0, 255, 0), 2)

    if mostrar_contornos and r.contornos:
        deslocados = [c + np.array([[x0, y0]]) for c in r.contornos]
        cv2.drawContours(frame, deslocados, -1, (0, 255, 255), 2)
        for c in deslocados:
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 255), 1)
        x, y, w, h = cv2.boundingRect(np.vstack(deslocados))
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

    if not r.tem_desenho:
        cv2.putText(frame, "Desenhe algo no quadrado", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
        return frame

    titulo = sem_acento(r.nome) if r.nome else "?"
    cv2.putText(frame, f"{titulo}  {r.confianca * 100:.0f}%", (10, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 3)
    for i, (nome, p) in enumerate(r.top):
        y = 65 + i * 26
        cv2.rectangle(frame, (10, y), (10 + int(p * 160), y + 16), (255, 140, 40), -1)
        cv2.putText(frame, f"{sem_acento(nome)} {p * 100:.0f}%", (180, y + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return frame


def painel_debug(r, tamanho=280):
    """Imagem de debug: à esquerda tinta+contornos, à direita o 28x28 da IA, embaixo números."""
    if r.tinta is None:
        esq = np.zeros((tamanho, tamanho, 3), np.uint8)
    else:
        esq = cv2.cvtColor(r.tinta, cv2.COLOR_GRAY2BGR)
        cv2.drawContours(esq, r.contornos, -1, (0, 255, 255), 2)
        for c in r.contornos:
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(esq, (x, y), (x + w, y + h), (255, 0, 255), 1)
        esq = cv2.resize(esq, (tamanho, tamanho))
    if r.bitmap is None:
        dir_ = np.zeros((tamanho, tamanho, 3), np.uint8)
    else:
        dir_ = cv2.cvtColor(cv2.resize(r.bitmap, (tamanho, tamanho),
                                       interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)
    painel = np.hstack([esq, dir_])

    info = np.zeros((90, painel.shape[1], 3), np.uint8)
    pixels = int(np.count_nonzero(r.tinta)) if r.tinta is not None else 0
    linhas = [f"Contornos validos: {len(r.contornos)}",
              f"Pixels de tinta: {pixels} (min {MIN_INK_PIXELS})",
              f"Confirmado: {sem_acento(r.estavel) if r.estavel else '-'}"]
    for i, t in enumerate(linhas):
        cv2.putText(info, t, (8, 22 + i * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    return np.vstack([painel, info])


# ------------------------------------------------------------------ demo
def demo():
    from config_camera import abrir_camera, carregar_config, ler_frame, recortar_quadrado

    try:
        sys.stdout.reconfigure(encoding="utf-8")   # acentos no CMD
    except Exception:
        pass

    p = argparse.ArgumentParser(description="Demo do detector com a câmera")
    p.add_argument("--cam", type=int, help="índice da câmera (senão usa camera_config.json)")
    p.add_argument("--modelo", default="model.h5")
    p.add_argument("--classes", default="classes.json")
    p.add_argument("--sem-debug", action="store_true", help="não abre a janela de debug")
    args = p.parse_args()

    cfg = carregar_config()
    if args.cam is not None:
        cfg["indice"] = args.cam
    det = Detector(args.modelo, args.classes)
    cap, cfg = abrir_camera(cfg)

    debug, contornos = not args.sem_debug, True
    JANELA_DEBUG = "DEBUG (esq: tinta+contornos | dir: 28x28 da IA)"
    print("Câmera iniciada. Desenhe algo no quadrado verde. (q para sair)\n")

    while True:
        frame = ler_frame(cap, cfg)
        if frame is None:
            break
        roi, caixa = recortar_quadrado(frame, cfg)
        r = det.detectar(roi)

        if r.mudou:
            hora = time.strftime("%H:%M:%S")
            if r.estavel is None:
                print(f"[{hora}] Nada reconhecido")
            else:
                print(f"[{hora}] Estou vendo: {r.estavel} ({r.confianca * 100:.0f}%) "
                      f"| contornos: {len(r.contornos)}")

        desenhar(frame, r, caixa, contornos)
        cv2.imshow("Detector", frame)
        if debug:
            cv2.imshow(JANELA_DEBUG, painel_debug(r))

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("c"):
            contornos = not contornos
        elif key == ord("d"):
            debug = not debug
            if not debug:
                cv2.destroyWindow(JANELA_DEBUG)
        elif key == ord("s"):
            os.makedirs("capturas", exist_ok=True)
            nome = os.path.join("capturas", time.strftime("%Y%m%d_%H%M%S") + ".png")
            cv2.imwrite(nome, frame)
            print(f"Print salvo em {nome}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    demo()