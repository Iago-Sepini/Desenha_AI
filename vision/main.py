"""
MAIN - junta o treino (train.py) e a camera (camera.py) em um unico programa.

Uso:
    py -3.11 main.py              -> treina se ainda nao existir model.h5, depois abre a camera
    py -3.11 main.py --treinar    -> forca re-treinar e depois abre a camera
    py -3.11 main.py --camera     -> so abre a camera (precisa do model.h5)
    py -3.11 main.py --treinar --sem-camera   -> so treina
    py -3.11 main.py --web        -> tambem exporta para TensorFlow.js (precisa do tensorflowjs)
    py -3.11 main.py --cam 1      -> usa a camera de indice 1

Teclas na camera:
    q = sair | m = espelhar | + / - = tamanho do quadrado
    d = debug | c = contornos | s = salvar print
"""
import argparse
import json
import os
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

import cv2
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

try:
    sys.stdout.reconfigure(encoding="utf-8")  # acentos no CMD
except Exception:
    pass

# =====================================================================
# CONFIGURACOES
# =====================================================================
# Classes: nome oficial do QuickDraw (ingles) -> nome mostrado na tela
from classes_quickdraw import TODAS_AS_CLASSES, CLASSES_MEDIAS, CLASSES_BASICAS

CLASSES = dict(TODAS_AS_CLASSES)   # padrão: todas (use --medio ou --basico para menos)
SAMPLES_PER_CLASS = 1500           # imagens por classe (com poucas classes, pode subir p/ 5000)
EPOCHS = 10
BASE_URL = "https://storage.googleapis.com/quickdraw_dataset/full/numpy_bitmap/"
MODEL_PATH = "model.h5"
CLASSES_PATH = "classes.json"

# Camera
MIN_CONFIDENCE = 0.55   # abaixo disso mostra "?"
MIN_INK_PIXELS = 60     # minimo de tinta para considerar que ha desenho
MIN_CONTOUR_AREA = 40   # ignora contornos pequenos (ruido)
SMOOTH_FRAMES = 6       # media das ultimas N previsoes
STABLE_FRAMES = 8       # frames iguais seguidos para anunciar no terminal


def sem_acento(texto):
    """cv2.putText nao desenha acentos."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


# =====================================================================
# PARTE 1 - TREINO
# =====================================================================
def treinar(exportar_web=False):
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # 1. Baixar e montar o dataset (pula classes que falharem)
    X, y, validos = [], [], []
    total = len(CLASSES)
    for n, name in enumerate(list(CLASSES.keys()), 1):
        path = data_dir / f"{name}.npy"
        if not path.exists():
            url = BASE_URL + urllib.parse.quote(name) + ".npy"
            print(f"[{n}/{total}] Baixando {name}...")
            try:
                urllib.request.urlretrieve(url, path)
            except Exception as e:
                print(f"   ! pulando '{name}': {e}")
                path.unlink(missing_ok=True)
                continue
        try:
            arr = np.array(np.load(path, mmap_mode="r")[:SAMPLES_PER_CLASS], dtype=np.uint8)
        except Exception as e:
            print(f"   ! arquivo '{name}.npy' corrompido, apagando e pulando: {e}")
            path.unlink(missing_ok=True)
            continue
        X.append(arr)
        y.append(np.full(len(arr), len(validos)))
        validos.append(name)

    if len(validos) < 2:
        raise SystemExit("Menos de 2 classes disponíveis. Verifique a internet.")
    nomes_pt = [CLASSES[v] for v in validos]
    print(f"\n{len(validos)} classes prontas para treinar.")

    X = np.concatenate(X).reshape(-1, 28, 28, 1)   # uint8 (economiza RAM)
    y = np.concatenate(y)

    perm = np.random.permutation(len(X))
    X, y = X[perm], y[perm]
    split = int(0.9 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # converte para float32 /255 aos poucos (lote a lote), sem estourar a memória
    def norm(x, label):
        return tf.cast(x, tf.float32) / 255.0, label

    ds_train = (tf.data.Dataset.from_tensor_slices((X_train, y_train))
                .shuffle(20000).batch(128).map(norm).prefetch(tf.data.AUTOTUNE))
    ds_test = (tf.data.Dataset.from_tensor_slices((X_test, y_test))
               .batch(256).map(norm).prefetch(tf.data.AUTOTUNE))

    # 2. Modelo maior, para aguentar centenas de classes
    model = keras.Sequential([
        layers.Input(shape=(28, 28, 1)),
        layers.Conv2D(32, 3, padding="same", activation="relu"),
        layers.Conv2D(32, 3, padding="same", activation="relu"),
        layers.MaxPooling2D(),
        layers.Conv2D(64, 3, padding="same", activation="relu"),
        layers.Conv2D(64, 3, padding="same", activation="relu"),
        layers.MaxPooling2D(),
        layers.Conv2D(128, 3, padding="same", activation="relu"),
        layers.MaxPooling2D(),
        layers.Flatten(),
        layers.Dense(512, activation="relu"),
        layers.Dropout(0.4),
        layers.Dense(len(validos), activation="softmax"),
    ])
    model.compile(optimizer="adam",
                  loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    model.summary()

    model.fit(ds_train, epochs=EPOCHS, validation_data=ds_test)
    loss, acc = model.evaluate(ds_test, verbose=0)
    print(f"Acurácia no teste: {acc:.3f}")

    # 3. Salvar (classes.json na MESMA ordem das classes que realmente treinaram)
    model.save(MODEL_PATH)
    with open(CLASSES_PATH, "w", encoding="utf-8") as f:
        json.dump(nomes_pt, f, ensure_ascii=False)
    print(f"Modelo salvo em {MODEL_PATH} e {len(nomes_pt)} classes em {CLASSES_PATH}")

    # 4. (opcional) exportar para o navegador
    if exportar_web:
        subprocess.run(["tensorflowjs_converter", "--input_format=keras",
                        "--quantize_uint8", MODEL_PATH, "web_model"], check=True)
        print("Exportado para web_model/. Rode: python -m http.server 8000")


# =====================================================================
# PARTE 2 - CAMERA
# =====================================================================
def carregar_modelo():
    model = keras.models.load_model(MODEL_PATH)
    with open(CLASSES_PATH, encoding="utf-8") as f:
        classes_texto = json.load(f)
    return model, classes_texto


def preprocess(roi):
    """Retorna (bitmap28 ou None, mascara_de_tinta, contornos)."""
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12)
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) >= MIN_CONTOUR_AREA]

    ys, xs = np.nonzero(ink)
    if len(xs) < MIN_INK_PIXELS:
        return None, ink, contours

    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    crop = ink[y0:y1 + 1, x0:x1 + 1]

    h, w = crop.shape
    side = max(h, w)
    square = np.zeros((side, side), np.uint8)
    square[(side - h) // 2:(side - h) // 2 + h,
           (side - w) // 2:(side - w) // 2 + w] = crop

    k = max(3, side // 12)
    square = cv2.dilate(square, np.ones((k, k), np.uint8))

    small = cv2.resize(square, (24, 24), interpolation=cv2.INTER_AREA)
    bitmap = np.zeros((28, 28), np.uint8)
    bitmap[2:26, 2:26] = small
    return bitmap, ink, contours


def predict(model, bitmap):
    x = bitmap.astype("float32") / 255.0
    return model.predict(x.reshape(1, 28, 28, 1), verbose=0)[0]


def draw_contours(target, contours, offset):
    ox, oy = offset
    if not contours:
        return
    shifted = [c + np.array([[ox, oy]]) for c in contours]
    cv2.drawContours(target, shifted, -1, (0, 255, 255), 2)
    for c in shifted:
        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(target, (x, y), (x + w, y + h), (255, 0, 255), 1)
    x, y, w, h = cv2.boundingRect(np.vstack(shifted))
    cv2.rectangle(target, (x, y), (x + w, y + h), (0, 0, 255), 2)


def camera(cam_index=0):
    if not (os.path.exists(MODEL_PATH) and os.path.exists(CLASSES_PATH)):
        raise SystemExit("model.h5/classes.json não encontrados. Rode: py -3.11 main.py --treinar")

    model, classes_texto = carregar_modelo()
    classes = [sem_acento(c) for c in classes_texto]
    DEBUG_WIN = "DEBUG (esq: tinta+contornos | dir: 28x28 da IA)"

    cap = cv2.VideoCapture(cam_index, cv2.CAP_DSHOW)  # CAP_DSHOW = mais rapido no Windows
    if not cap.isOpened():
        raise SystemExit("Nao consegui abrir a camera. Tente --cam 1")

    mirror = False
    show_debug = True
    show_contours = True
    box_frac = 0.6
    history = deque(maxlen=SMOOTH_FRAMES)

    last_label = None
    cand_label = None
    cand_count = 0
    fps_t = time.time()
    fps = 0.0

    print("Camera iniciada. Desenhe algo no quadrado verde. (q para sair)\n")

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

        bitmap, ink, contours = preprocess(roi)

        view = frame.copy()
        cv2.rectangle(view, (x0, y0), (x0 + side, y0 + side), (0, 255, 0), 2)
        if show_contours:
            draw_contours(view, contours, (x0, y0))

        label_now = None
        probs = None
        if bitmap is None:
            history.clear()
            cv2.putText(view, "Desenhe algo no quadrado", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
            model_view = np.zeros((280, 280), np.uint8)
        else:
            history.append(predict(model, bitmap))
            probs = np.mean(history, axis=0)
            order = np.argsort(probs)[::-1][:3]
            best = order[0]
            confident = probs[best] >= MIN_CONFIDENCE
            title = classes[best] if confident else "?"
            label_now = classes_texto[best] if confident else None

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

        # Saida em TEXTO no terminal (so quando muda e esta estavel)
        if label_now == cand_label:
            cand_count += 1
        else:
            cand_label, cand_count = label_now, 1
        if cand_count == STABLE_FRAMES and cand_label != last_label:
            last_label = cand_label
            hora = time.strftime("%H:%M:%S")
            if cand_label is None:
                print(f"[{hora}] Nada reconhecido (sem desenho ou confianca baixa)")
            else:
                conf = probs[classes_texto.index(cand_label)] * 100
                print(f"[{hora}] Estou vendo: {cand_label} ({conf:.0f}%) "
                      f"| contornos: {len(contours)}")

        # FPS
        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - fps_t, 1e-6))
        fps_t = now
        cv2.putText(view, f"FPS {fps:.0f}", (W - 100, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Camera", view)

        # Janela de DEBUG
        if show_debug:
            ink_color = cv2.cvtColor(ink, cv2.COLOR_GRAY2BGR)
            cv2.drawContours(ink_color, contours, -1, (0, 255, 255), 2)
            for c in contours:
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(ink_color, (x, y), (x + w, y + h), (255, 0, 255), 1)
            ink_view = cv2.resize(ink_color, (280, 280))
            model_color = cv2.cvtColor(model_view, cv2.COLOR_GRAY2BGR)
            panel = np.hstack([ink_view, model_color])

            info = np.zeros((90, panel.shape[1], 3), np.uint8)
            lines = [
                f"Contornos validos: {len(contours)}",
                f"Pixels de tinta: {int(np.count_nonzero(ink))} (min {MIN_INK_PIXELS})",
                f"Previsao: {last_label or '-'}",
            ]
            for i, t in enumerate(lines):
                cv2.putText(info, sem_acento(t), (8, 22 + i * 24),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
            cv2.imshow(DEBUG_WIN, np.vstack([panel, info]))

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("m"):
            mirror = not mirror
        elif key == ord("c"):
            show_contours = not show_contours
        elif key == ord("d"):
            show_debug = not show_debug
            if not show_debug:
                cv2.destroyWindow(DEBUG_WIN)
        elif key in (ord("+"), ord("=")):
            box_frac = min(0.95, box_frac + 0.05)
        elif key == ord("-"):
            box_frac = max(0.2, box_frac - 0.05)
        elif key == ord("s"):
            os.makedirs("capturas", exist_ok=True)
            nome = os.path.join("capturas", time.strftime("%Y%m%d_%H%M%S") + ".png")
            cv2.imwrite(nome, view)
            print(f"Print salvo em {nome}")

    cap.release()
    cv2.destroyAllWindows()


# =====================================================================
# MAIN
# =====================================================================
def main():
    parser = argparse.ArgumentParser(description="Reconhecimento de desenhos (treino + camera)")
    parser.add_argument("--treinar", action="store_true", help="força treinar o modelo")
    parser.add_argument("--camera", action="store_true", help="só abre a camera (sem treinar)")
    parser.add_argument("--sem-camera", action="store_true", help="não abre a camera depois do treino")
    parser.add_argument("--web", action="store_true", help="exporta também para TensorFlow.js")
    parser.add_argument("--cam", type=int, default=0, help="índice da camera (padrão 0)")
    parser.add_argument("--basico", action="store_true", help="treina só 9 classes (rápido)")
    parser.add_argument("--medio", action="store_true", help="treina ~70 classes")
    parser.add_argument("--amostras", type=int, help="imagens por classe (padrão 1500)")
    parser.add_argument("--epocas", type=int, help="número de épocas (padrão 10)")
    args = parser.parse_args()

    global CLASSES, SAMPLES_PER_CLASS, EPOCHS
    if args.basico:
        CLASSES = dict(CLASSES_BASICAS)
        SAMPLES_PER_CLASS = 5000
    elif args.medio:
        CLASSES = dict(CLASSES_MEDIAS)
        SAMPLES_PER_CLASS = 3000
    if args.amostras:
        SAMPLES_PER_CLASS = args.amostras
    if args.epocas:
        EPOCHS = args.epocas

    tem_modelo = os.path.exists(MODEL_PATH) and os.path.exists(CLASSES_PATH)

    if not args.camera and (args.treinar or not tem_modelo):
        print("=== TREINANDO O MODELO ===")
        treinar(exportar_web=args.web)
    else:
        print(f"Modelo encontrado ({MODEL_PATH}). Pulando o treino.")

    if not args.sem_camera:
        print("\n=== ABRINDO A CAMERA ===")
        camera(args.cam)


if __name__ == "__main__":
    main()