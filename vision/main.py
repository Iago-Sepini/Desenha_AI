"""
MAIN - treino (QuickDraw, 100 classes) + camera em TELA CHEIA, em um unico programa.

Uso:
    py -3.11 main.py              -> treina se ainda nao existir model.h5, depois abre a camera
    py -3.11 main.py --treinar    -> forca re-treinar e depois abre a camera
    py -3.11 main.py --camera     -> so abre a camera (precisa do model.h5)
    py -3.11 main.py --treinar --sem-camera   -> so treina
    py -3.11 main.py --web        -> tambem exporta para TensorFlow.js
    py -3.11 main.py --cam 1      -> usa a camera de indice 1

Teclas na camera:
    q = sair | m = espelhar | + / - = sensibilidade da deteccao de tinta
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
import keras
from keras import layers

try:
    sys.stdout.reconfigure(encoding="utf-8")  # acentos no CMD
except Exception:
    pass

# =====================================================================
# CONFIGURACOES
# =====================================================================
# Classes: nome oficial do QuickDraw (ingles) -> nome mostrado na tela (100 classes)
CLASSES = {
    "soccer ball": "bola",
    "umbrella": "guarda-chuva",
    "dog": "cachorro",
    "cat": "gato",
    "house": "casa",
    "car": "carro",
    "sun": "sol",
    "apple": "maçã",
    "fish": "peixe",
    "airplane": "avião",
    "bicycle": "bicicleta",
    "banana": "banana",
    "bird": "pássaro",
    "book": "livro",
    "butterfly": "borboleta",
    "cake": "bolo",
    "camera": "câmera",
    "chair": "cadeira",
    "clock": "relógio",
    "cloud": "nuvem",
    "cup": "copo",
    "door": "porta",
    "eye": "olho",
    "flower": "flor",
    "guitar": "violão",
    "hat": "chapéu",
    "key": "chave",
    "lightning": "raio",
    "moon": "lua",
    "mushroom": "cogumelo",
    "pencil": "lápis",
    "scissors": "tesoura",
    "star": "estrela",
    "table": "mesa",
    "tree": "árvore",
    "truck": "caminhão",
    "train": "trem",
    "hand": "mão",
    "face": "rosto",
    "bed": "cama",
    "bear": "urso",
    "bee": "abelha",
    "bus": "ônibus",
    "cactus": "cacto",
    "candle": "vela",
    "carrot": "cenoura",
    "castle": "castelo",
    "cow": "vaca",
    "crab": "caranguejo",
    "crown": "coroa",
    "diamond": "diamante",
    "donut": "rosquinha",
    "duck": "pato",
    "elephant": "elefante",
    "envelope": "envelope",
    "feather": "pena",
    "frog": "sapo",
    "giraffe": "girafa",
    "hammer": "martelo",
    "headphones": "fone de ouvido",
    "helicopter": "helicóptero",
    "horse": "cavalo",
    "ice cream": "sorvete",
    "ladder": "escada",
    "lion": "leão",
    "monkey": "macaco",
    "mountain": "montanha",
    "octopus": "polvo",
    "owl": "coruja",
    "pizza": "pizza",
    "rabbit": "coelho",
    "rainbow": "arco-íris",
    "sailboat": "veleiro",
    "shark": "tubarão",
    "sheep": "ovelha",
    "shoe": "sapato",
    "skull": "caveira",
    "snake": "cobra",
    "snowman": "boneco de neve",
    "spider": "aranha",
    "strawberry": "morango",
    "sword": "espada",
    "tiger": "tigre",
    "toothbrush": "escova de dentes",
    "tractor": "trator",
    "trumpet": "trombeta",
    "violin": "violino",
    "watermelon": "melancia",
    "whale": "baleia",
    "windmill": "moinho de vento",
    "zebra": "zebra",
    "pig": "porco",
    "penguin": "pinguim",
    "piano": "piano",
    "pear": "pera",
    "pineapple": "abacaxi",
    "snowflake": "floco de neve",
    "tent": "barraca",
    "vase": "vaso",
    "hamburger": "hambúrguer",
}
SAMPLES_PER_CLASS = 5000
EPOCHS = 12
BASE_URL = "https://storage.googleapis.com/quickdraw_dataset/full/numpy_bitmap/"
MODEL_PATH = "model.h5"
CLASSES_PATH = "classes.json"

# Camera
MIN_CONFIDENCE = 0.40    # abaixo disso mostra "?" (100 classes => confianca menor)
MIN_INK_PIXELS = 150     # minimo de tinta no desenho escolhido
MIN_CONTOUR_AREA = 60    # ignora contornos pequenos (ruido)
MERGE_KERNEL = 25        # junta tracos proximos num mesmo desenho
MAX_BLOB_FRAC = 0.6      # ignora regioes maiores que isso do frame (bordas, sombras)
THRESH_C = 12            # sensibilidade inicial (maior = menos tinta detectada)
SMOOTH_FRAMES = 6        # media das ultimas N previsoes
STABLE_FRAMES = 8        # frames iguais seguidos para anunciar no terminal


def sem_acento(texto):
    """cv2.putText nao desenha acentos."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


# =====================================================================
# PARTE 1 - TREINO
# =====================================================================
def baixar_amostras(name, destino):
    """Baixa so os primeiros SAMPLES_PER_CLASS desenhos do .npy (~4 MB em vez de ~100 MB)."""
    url = BASE_URL + urllib.parse.quote(name) + ".npy"
    n_bytes = 256 + SAMPLES_PER_CLASS * 784   # folga para o cabecalho do .npy
    req = urllib.request.Request(url, headers={"Range": f"bytes=0-{n_bytes - 1}"})
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read(n_bytes)          # le so o necessario, mesmo se o servidor ignorar o Range
    except urllib.error.HTTPError:
        raise SystemExit(
            f"Classe '{name}' não existe no QuickDraw. "
            "Confira o nome na lista oficial e troque em CLASSES."
        )
    hlen = int.from_bytes(raw[8:10], "little")   # .npy v1.0: tamanho do cabecalho
    off = 10 + hlen
    dados = raw[off:off + SAMPLES_PER_CLASS * 784]
    dados = dados[:len(dados) // 784 * 784]
    with open(destino, "wb") as f:
        f.write(dados)


def treinar(exportar_web=False):
    names = list(CLASSES.keys())
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    # 1. Baixar e montar o dataset (uint8 para economizar memoria)
    X, y = [], []
    for idx, name in enumerate(names):
        npy_path = data_dir / f"{name}.npy"   # arquivo completo (se ja existir de antes)
        bin_path = data_dir / f"{name}.bin"   # so as N primeiras amostras (bem menor)
        if npy_path.exists():
            arr = np.array(np.load(npy_path, mmap_mode="r")[:SAMPLES_PER_CLASS])
        else:
            if not bin_path.exists():
                print(f"Baixando {name} ({idx + 1}/{len(names)})...")
                baixar_amostras(name, bin_path)
            arr = np.fromfile(bin_path, dtype=np.uint8).reshape(-1, 784)
        X.append(arr)
        y.append(np.full(len(arr), idx))

    X = np.concatenate(X).reshape(-1, 28, 28, 1)  # uint8 0..255
    y = np.concatenate(y)

    perm = np.random.permutation(len(X))
    X, y = X[perm], y[perm]
    split = int(0.9 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # 2. Modelo (normalizacao 0..255 -> 0..1 esta DENTRO do modelo)
    model = keras.Sequential([
        layers.Input(shape=(28, 28, 1)),
        layers.Rescaling(1.0 / 255),
        layers.Conv2D(32, 3, activation="relu"),
        layers.MaxPooling2D(),
        layers.Conv2D(64, 3, activation="relu"),
        layers.MaxPooling2D(),
        layers.Conv2D(128, 3, activation="relu"),
        layers.Flatten(),
        layers.Dense(512, activation="relu"),
        layers.Dropout(0.4),
        layers.Dense(len(names), activation="softmax"),
    ])
    model.compile(optimizer="adam",
                  loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    model.summary()

    model.fit(X_train, y_train, epochs=EPOCHS, batch_size=128,
              validation_data=(X_test, y_test))
    loss, acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"Acurácia no teste: {acc:.3f}")

    # 3. Salvar
    model.save(MODEL_PATH)
    with open(CLASSES_PATH, "w", encoding="utf-8") as f:
        json.dump(list(CLASSES.values()), f, ensure_ascii=False)
    print(f"Modelo salvo em {MODEL_PATH} e classes em {CLASSES_PATH}")

    # 4. (opcional) exportar para o navegador
    if exportar_web:
        subprocess.run(["tensorflowjs_converter", "--input_format=keras",
                        "--quantize_uint8", MODEL_PATH, "web_model"], check=True)
        print("Exportado para web_model/. Rode: python -m http.server 8000")


# =====================================================================
# PARTE 2 - CAMERA (tela cheia)
# =====================================================================
def carregar_modelo():
    model = keras.models.load_model(MODEL_PATH)
    with open(CLASSES_PATH, encoding="utf-8") as f:
        classes_texto = json.load(f)
    return model, classes_texto


def preprocess(frame, thresh_c):
    """
    Analisa o FRAME INTEIRO.
    Retorna (bitmap28 ou None, mascara_de_tinta, contornos, caixa_do_desenho ou None).
    """
    H, W = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, thresh_c)
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))

    contours, _ = cv2.findContours(ink, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) >= MIN_CONTOUR_AREA]

    # Junta tracos proximos em "blobs" e escolhe o com mais tinta
    merged = cv2.dilate(ink, np.ones((MERGE_KERNEL, MERGE_KERNEL), np.uint8))
    blobs, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_box, best_score = None, 0
    for b in blobs:
        x, y, w, h = cv2.boundingRect(b)
        if w * h > MAX_BLOB_FRAC * H * W:
            continue
        score = cv2.countNonZero(ink[y:y + h, x:x + w])
        if score > best_score:
            best_score, best_box = score, (x, y, w, h)

    if best_box is None or best_score < MIN_INK_PIXELS:
        return None, ink, contours, None

    bx, by, bw, bh = best_box
    crop = ink[by:by + bh, bx:bx + bw]

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
    return bitmap, ink, contours, best_box


def predict(model, bitmap):
    x = bitmap.astype("float32")  # o /255 e feito dentro do modelo
    return model.predict(x.reshape(1, 28, 28, 1), verbose=0)[0]


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
    thresh_c = THRESH_C
    history = deque(maxlen=SMOOTH_FRAMES)

    last_label = None
    cand_label = None
    cand_count = 0
    fps_t = time.time()
    fps = 0.0

    print("Camera iniciada. Desenhe em qualquer lugar da imagem. (q para sair)\n")

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if mirror:
            frame = cv2.flip(frame, 1)

        H, W = frame.shape[:2]
        bitmap, ink, contours, box = preprocess(frame, thresh_c)

        view = frame.copy()
        if show_contours:
            cv2.drawContours(view, contours, -1, (0, 255, 255), 1)
        if box is not None:
            bx, by, bw, bh = box
            cv2.rectangle(view, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)

        label_now = None
        probs = None
        if bitmap is None:
            history.clear()
            cv2.putText(view, "Desenhe algo (em qualquer lugar)", (10, 30),
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
            cv2.drawContours(ink_color, contours, -1, (0, 255, 255), 1)
            if box is not None:
                bx, by, bw, bh = box
                cv2.rectangle(ink_color, (bx, by), (bx + bw, by + bh), (0, 0, 255), 3)
            ink_view = cv2.resize(ink_color, (int(280 * W / H), 280))
            model_color = cv2.cvtColor(model_view, cv2.COLOR_GRAY2BGR)
            panel = np.hstack([ink_view, model_color])

            info = np.zeros((90, panel.shape[1], 3), np.uint8)
            lines = [
                f"Contornos validos: {len(contours)}",
                f"Sensibilidade (C): {thresh_c}  (+/-)",
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
            thresh_c = max(2, thresh_c - 2)    # mais sensivel (detecta mais tinta)
        elif key == ord("-"):
            thresh_c = min(40, thresh_c + 2)   # menos sensivel (menos ruido)
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
    args = parser.parse_args()

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