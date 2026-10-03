"""
TREINO — gera model.h5 e classes.json a partir do QuickDraw
(as classes vêm do classes_quickdraw.py).

Uso:
    py -3.10 vision/treinar.py                        todas as classes (342) — demora bastante
    py -3.10 vision/treinar.py --classes medio        ~71 classes (bom equilíbrio)
    py -3.10 vision/treinar.py --classes basico       9 classes (rápido)
    py -3.10 vision/treinar.py --escolher "cat,dog,house,sun"   só as que você escolher (nomes em inglês)
    py -3.10 vision/treinar.py --amostras 800 --epocas 6        treino mais leve
    py -3.10 vision/treinar.py --listar               mostra os nomes de todas as classes
    py -3.10 vision/treinar.py --web                  também exporta para TensorFlow.js (precisa do tensorflowjs)

Saída: model.h5 + classes.json (sempre juntos, da mesma execução). Os desenhos baixados
ficam em data/ e não são baixados de novo.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

from classes_quickdraw import CLASSES_BASICAS, CLASSES_MEDIAS, TODAS_AS_CLASSES

try:
    sys.stdout.reconfigure(encoding="utf-8")   # acentos no CMD
except Exception:
    pass

BASE_URL = "https://storage.googleapis.com/quickdraw_dataset/full/numpy_bitmap/"


def escolher_classes(args):
    if args.escolher:
        nomes = [n.strip() for n in args.escolher.split(",") if n.strip()]
        invalidos = [n for n in nomes if n not in TODAS_AS_CLASSES]
        if invalidos:
            raise SystemExit(f"Classes que não estão no classes_quickdraw.py: {invalidos}\n"
                             "Veja os nomes com: py -3.10 treinar.py --listar")
        return {n: TODAS_AS_CLASSES[n] for n in nomes}
    if args.classes == "basico":
        return dict(CLASSES_BASICAS)
    if args.classes == "medio":
        return dict(CLASSES_MEDIAS)
    return dict(TODAS_AS_CLASSES)


def carregar_dados(classes, pasta, amostras):
    """Baixa (se preciso) e monta X (uint8) e y. Pula classes que falharem."""
    pasta = Path(pasta)
    pasta.mkdir(exist_ok=True)
    X, y, validos = [], [], []
    total = len(classes)
    for n, nome in enumerate(classes, 1):
        caminho = pasta / f"{nome}.npy"
        if not caminho.exists():
            url = BASE_URL + urllib.parse.quote(nome) + ".npy"
            print(f"[{n}/{total}] Baixando {nome}...")
            try:
                urllib.request.urlretrieve(url, caminho)
            except Exception as e:
                print(f"   ! pulando '{nome}': {e}")
                caminho.unlink(missing_ok=True)
                continue
        try:
            arr = np.array(np.load(caminho, mmap_mode="r")[:amostras], dtype=np.uint8)
        except Exception as e:
            print(f"   ! '{nome}.npy' corrompido, apagando e pulando: {e}")
            caminho.unlink(missing_ok=True)
            continue
        X.append(arr)
        y.append(np.full(len(arr), len(validos)))
        validos.append(nome)

    if len(validos) < 2:
        raise SystemExit("Menos de 2 classes disponíveis. Verifique a internet.")
    return np.concatenate(X).reshape(-1, 28, 28, 1), np.concatenate(y), validos


def criar_modelo(n_classes):
    return keras.Sequential([
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
        layers.Dense(n_classes, activation="softmax"),
    ])


def main():
    p = argparse.ArgumentParser(description="Treino do reconhecedor de desenhos")
    p.add_argument("--classes", choices=["todas", "medio", "basico"], default="todas")
    p.add_argument("--escolher", help='nomes em inglês separados por vírgula, ex.: "cat,dog,house"')
    p.add_argument("--amostras", type=int, default=1500, help="imagens por classe (padrão 1500)")
    p.add_argument("--epocas", type=int, default=10, help="épocas de treino (padrão 10)")
    p.add_argument("--dados", default="data", help="pasta dos .npy baixados (padrão data)")
    p.add_argument("--modelo", default="model.h5", help="arquivo do modelo (padrão model.h5)")
    p.add_argument("--saida-classes", default="classes.json", help="arquivo dos nomes (padrão classes.json)")
    p.add_argument("--web", action="store_true", help="exporta também para TensorFlow.js")
    p.add_argument("--listar", action="store_true", help="lista as classes disponíveis e sai")
    args = p.parse_args()

    if args.listar:
        for en, pt in TODAS_AS_CLASSES.items():
            print(f"{en:22s} -> {pt}")
        print(f"\nTotal: {len(TODAS_AS_CLASSES)} (medio: {len(CLASSES_MEDIAS)}, basico: {len(CLASSES_BASICAS)})")
        return

    classes = escolher_classes(args)
    print(f"Treinando com até {len(classes)} classes, {args.amostras} imagens cada, {args.epocas} épocas.\n")

    X, y, validos = carregar_dados(classes, args.dados, args.amostras)
    nomes_pt = [classes[v] for v in validos]
    print(f"\n{len(validos)} classes prontas. {len(X)} imagens no total.")

    perm = np.random.permutation(len(X))
    X, y = X[perm], y[perm]
    corte = int(0.9 * len(X))

    # converte para float32 /255 lote a lote (não estoura a memória)
    def normalizar(x, rotulo):
        return tf.cast(x, tf.float32) / 255.0, rotulo

    ds_treino = (tf.data.Dataset.from_tensor_slices((X[:corte], y[:corte]))
                 .shuffle(20000).batch(128).map(normalizar).prefetch(tf.data.AUTOTUNE))
    ds_teste = (tf.data.Dataset.from_tensor_slices((X[corte:], y[corte:]))
                .batch(256).map(normalizar).prefetch(tf.data.AUTOTUNE))

    modelo = criar_modelo(len(validos))
    modelo.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    modelo.summary()

    # classes.json ANTES de treinar + modelo salvo a cada época que melhora:
    # se o treino for interrompido, o que já foi salvo continua utilizável
    with open(args.saida_classes, "w", encoding="utf-8") as f:
        json.dump(nomes_pt, f, ensure_ascii=False)
    checkpoint = keras.callbacks.ModelCheckpoint(
        args.modelo, monitor="val_accuracy", save_best_only=True, verbose=1)

    modelo.fit(ds_treino, epochs=args.epocas, validation_data=ds_teste, callbacks=[checkpoint])

    modelo = keras.models.load_model(args.modelo)   # volta ao melhor modelo salvo
    _, acc = modelo.evaluate(ds_teste, verbose=0)
    print(f"\nAcurácia no teste: {acc:.3f}")
    print(f"Pronto: {args.modelo} + {args.saida_classes} ({len(nomes_pt)} classes).")

    if args.web:
        subprocess.run(["tensorflowjs_converter", "--input_format=keras",
                        "--quantize_uint8", args.modelo, "web_model"], check=True)
        print("Exportado para web_model/.")


if __name__ == "__main__":
    main()