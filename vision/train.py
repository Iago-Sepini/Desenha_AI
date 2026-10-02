"""
Treina uma CNN LEVE com o QuickDraw (bitmaps 28x28) e exporta para TensorFlow.js.

Uso (Google Colab ou venv com Python 3.10/3.11):
    pip install tensorflow==2.15.0 tensorflowjs==4.17.0 numpy
    python train.py

Saída: pasta web_model/ (model.json + pesos quantizados) e classes.json
"""
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import keras
from keras import layers

# ---- Classes: nome oficial do QuickDraw (inglês) -> nome mostrado na tela ----
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
}
SAMPLES_PER_CLASS = 5000
EPOCHS = 6
BASE_URL = "https://storage.googleapis.com/quickdraw_dataset/full/numpy_bitmap/"

names = list(CLASSES.keys())
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# ---- 1. Baixar e montar o dataset ----
X, y = [], []
for idx, name in enumerate(names):
    path = data_dir / f"{name}.npy"
    if not path.exists():
        url = BASE_URL + urllib.parse.quote(name) + ".npy"
        print(f"Baixando {name}...")
        try:
            urllib.request.urlretrieve(url, path)
        except urllib.error.HTTPError:
            raise SystemExit(
                f"Classe '{name}' não existe no QuickDraw. "
                "Confira o nome na lista oficial de categorias e troque no CLASSES."
            )
    arr = np.load(path)[:SAMPLES_PER_CLASS]
    X.append(arr)
    y.append(np.full(len(arr), idx))

X = np.concatenate(X).astype("float32") / 255.0
X = X.reshape(-1, 28, 28, 1)
y = np.concatenate(y)

perm = np.random.permutation(len(X))
X, y = X[perm], y[perm]
split = int(0.9 * len(X))
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

# ---- 2. Modelo pequeno (~30 mil parâmetros) ----
model = keras.Sequential([
    layers.Input(shape=(28, 28, 1)),
    layers.Conv2D(16, 3, activation="relu"),
    layers.MaxPooling2D(),
    layers.Conv2D(32, 3, activation="relu"),
    layers.MaxPooling2D(),
    layers.Flatten(),
    layers.Dense(64, activation="relu"),
    layers.Dropout(0.3),
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

# ---- 3. Exportar para o navegador (pesos em uint8 = arquivo bem menor) ----
model.save("model.h5")
with open("classes.json", "w", encoding="utf-8") as f:
    json.dump(list(CLASSES.values()), f, ensure_ascii=False)

subprocess.run(["tensorflowjs_converter", "--input_format=keras",
                "--quantize_uint8", "model.h5", "web_model"], check=True)
print("Pronto! Agora rode: python -m http.server 8000")
