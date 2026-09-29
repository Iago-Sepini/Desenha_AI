"""
Reconhecimento de desenhos pela CAMERA, 100% local (sem internet, sem navegador).

Pré-requisito: rodar train.py antes (gera model.h5 e classes.json).

Instalar:
    pip install tensorflow==2.15.0 opencv-python numpy

Rodar:
    python camera.py

Como usar:
    - Desenhe com caneta escura em papel branco.
    - Segure o papel dentro do quadrado verde da janela "Camera".
    - A janela "O que o modelo ve" mostra a imagem 28x28 que vai para a IA.

Teclas:  q = sair   |   m = espelhar a imagem   |   +/- = tamanho do quadrado
"""
import json
import os
import unicodedata
from collections import deque

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import cv2
import numpy as np
from tensorflow import keras

CAM_INDEX = 0          # troque para 1 se usar camera externa
MIN_CONFIDENCE = 0.55  # abaixo disso mostra "?"
MIN_INK_PIXELS = 60    # minimo de tinta para considerar que ha desenho
SMOOTH_FRAMES = 6      # media das ultimas N previsoes (deixa estavel)


def sem_acento(texto):
    """cv2.putText nao desenha acentos, entao removemos."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


model = keras.models.load_model("model.h5")
with open("classes.json", encoding="utf-8") as f:
    classes = [sem_acento(c) for c in json.load(f)]


def preprocess(roi):
    """Imagem do papel -> bitmap 28x28 (tracos brancos em fundo preto, como o QuickDraw).
    Retorna (bitmap28, mascara_de_tinta) ou (None, mascara) se nao houver desenho."""
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    # tinta escura em papel claro -> tinta branca (funciona com luz irregular)
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12)
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    ys, xs = np.nonzero(ink)
    if len(xs) < MIN_INK_PIXELS:
        return None, ink

    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    crop = ink[y0:y1 + 1, x0:x1 + 1]

    # deixa quadrado e centralizado
    h, w = crop.shape
    side = max(h, w)
    square = np.zeros((side, side), np.uint8)
    square[(side - h) // 2:(side - h) // 2 + h,
           (side - w) // 2:(side - w) // 2 + w] = crop

    # engrossa o traco (no QuickDraw o traco e grosso em 28x28)
    k = max(3, side // 12)
    square = cv2.dilate(square, np.ones((k, k), np.uint8))

    small = cv2.resize(square, (24, 24), interpolation=cv2.INTER_AREA)
    bitmap = np.zeros((28, 28), np.uint8)
    bitmap[2:26, 2:26] = small
    return bitmap, ink


def predict(bitmap):
    x = bitmap.astype("float32") / 255.0
    return model.predict(x.reshape(1, 28, 28, 1), verbose=0)[0]


def main():
    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        raise SystemExit("Nao consegui abrir a camera. Tente CAM_INDEX = 1.")

    mirror = False
    box_frac = 0.6
    history = deque(maxlen=SMOOTH_FRAMES)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if mirror:
            frame = cv2.flip(frame, 1)

        H, W = frame.shape[:2]
        side = int(min(H, W) * box_frac)
        x0, y0 = (W - side) // 2, (H - side) // 2
        roi = frame[y0:y0 + side, x0:x0 + side]

        bitmap, ink = preprocess(roi)

        view = frame.copy()
        cv2.rectangle(view, (x0, y0), (x0 + side, y0 + side), (0, 255, 0), 2)

        if bitmap is None:
            history.clear()
            cv2.putText(view, "Desenhe algo no quadrado", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
            model_view = np.zeros((280, 280), np.uint8)
        else:
            history.append(predict(bitmap))
            probs = np.mean(history, axis=0)
            order = np.argsort(probs)[::-1][:3]

            best = order[0]
            title = classes[best] if probs[best] >= MIN_CONFIDENCE else "?"
            cv2.putText(view, f"{title}  {probs[best] * 100:.0f}%", (10, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 0), 3)
            for i, idx in enumerate(order):
                y = 65 + i * 26
                cv2.rectangle(view, (10, y), (10 + int(probs[idx] * 160), y + 16),
                              (255, 140, 40), -1)
                cv2.putText(view, f"{classes[idx]} {probs[idx] * 100:.0f}%",
                            (180, y + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                            (255, 255, 255), 1)
            model_view = cv2.resize(bitmap, (280, 280), interpolation=cv2.INTER_NEAREST)

        ink_view = cv2.resize(ink, (280, 280))
        panel = np.hstack([ink_view, model_view])

        cv2.imshow("Camera", view)
        cv2.imshow("O que o modelo ve (esquerda: tinta detectada | direita: 28x28)", panel)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("m"):
            mirror = not mirror
        elif key in (ord("+"), ord("=")):
            box_frac = min(0.95, box_frac + 0.05)
        elif key == ord("-"):
            box_frac = max(0.2, box_frac - 0.05)

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
