"""
max_pinyin.py
==============
Chatbot de voz: ouve em PORTUGUÊS, manda para a LLM responder em CHINÊS,
converte o chinês para PINYIN (alfabeto a-z) e fala usando o `piper.exe`.
"""

import os
import sys
import subprocess
import tempfile
import threading
import time
import traceback
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
from groq import Groq

# Biblioteca leve para converter caracteres chineses para Pinyin (apenas letras a-z)
# Instale com: pip install pypinyin
from pypinyin import lazy_pinyin, Style

RAIZ_PROJETO = Path(__file__).resolve().parent.parent
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from config import (
    VOICE_DIR,
    MIC_DEVICE,
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TIMEOUT,
)
from voice.listener import Listener

# =========================================================================
# CONFIG
# =========================================================================
PIPER_EXE = str(RAIZ_PROJETO / "voice" / "piper" / "piper.exe")
# Usaremos uma voz em inglês ou espanhol do Piper que saiba ler fonemas latinos fluidamente,
# ou uma voz multilíngue se houver. Exemplo com uma voz padrão do Piper em inglês (en_US-lessac-medium):
PIPER_MODEL_PINYIN = os.getenv("PIPER_MODEL_PINYIN", str(VOICE_DIR / "models" / "br.onnx"))

MUSICA_INTRO = "tests/oogway.mp3"
ATRASO_MUSICA_SEGUNDOS = float(os.getenv("ATRASO_MUSICA_SEGUNDOS", "1.5"))
VOLUME_MUSICA_FUNDO = float(os.getenv("VOLUME_MUSICA_FUNDO", "0.3"))
SEGUNDOS_MUSICA_APOS_FALAR = float(os.getenv("SEGUNDOS_MUSICA_APOS_FALAR", "2.0"))

PALAVRAS_SAIR = ("sair", "tchau", "encerrar", "até mais")

SYSTEM_PROMPT = (
    "You are Max, a friendly and concise voice assistant. "
    "Always reply in big Chinese sentences (Simplified Chinese)."
)

DESPEDIDA = "Zai jian, zaihui!"

if not GROQ_API_KEY:
    print("[Max-Pinyin] AVISO: GROQ_API_KEY não encontrada no .env.")

groq_client = Groq(api_key=GROQ_API_KEY, timeout=GROQ_TIMEOUT) if GROQ_API_KEY else None
historico = [{"role": "system", "content": SYSTEM_PROMPT}]
encerrar_evento = threading.Event()
_audio_intro_cache = None


def perguntar_llm(texto_pt: str) -> str:
    historico.append({"role": "user", "content": texto_pt})
    resposta = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=historico,
        temperature=0.7,
        max_tokens=300,
    )
    texto_zh = resposta.choices[0].message.content.strip()
    historico.append({"role": "assistant", "content": texto_zh})
    if len(historico) > 21:
        del historico[1:3]
    return texto_zh


def _carregar_audio(caminho):
    caminho = str(caminho)
    if not os.path.isfile(caminho):
        return None
    try:
        audio, taxa = sf.read(caminho, dtype="float32", always_2d=True)
    except Exception:
        return None
    return audio, taxa


def _tocar_array(audio, taxa):
    stream = sd.OutputStream(samplerate=taxa, channels=audio.shape[1], dtype="float32")
    stream.start()
    try:
        stream.write(audio)
    finally:
        stream.stop()
        stream.close()


def tocar_wav(caminho, bloqueante: bool = True):
    carregado = _carregar_audio(caminho)
    if carregado is None:
        return
    audio, taxa = carregado
    if bloqueante:
        _tocar_array(audio, taxa)
    else:
        threading.Thread(target=_tocar_array, args=(audio, taxa), daemon=True).start()


def _gerenciar_musica(evento_parar: threading.Event):
    global _audio_intro_cache
    if _audio_intro_cache is None:
        return
    audio, taxa = _audio_intro_cache
    total = len(audio)
    if total == 0:
        return
    pos = 0

    def callback(outdata, frames, time_info, status):
        nonlocal pos
        if evento_parar.is_set():
            outdata[:] = 0
            raise sd.CallbackStop()
        n = min(frames, total - pos)
        outdata[:n] = audio[pos:pos + n]
        if n < frames:
            falta = frames - n
            outdata[n:n + falta] = audio[:falta]
            pos = falta
        else:
            pos += n

    try:
        with sd.OutputStream(samplerate=taxa, channels=audio.shape[1], dtype="float32", callback=callback):
            while not evento_parar.is_set():
                time.sleep(0.05)
    except sd.CallbackStop:
        pass


def carregar_cache_musica():
    global _audio_intro_cache
    carregado = _carregar_audio(MUSICA_INTRO)
    if carregado:
        audio, taxa = carregado
        _audio_intro_cache = (audio * VOLUME_MUSICA_FUNDO, taxa)


def falar_pinyin(texto_zh: str):
    if not texto_zh:
        return

    # Converte o texto em chinês para Pinyin puro (sem tons ou com tons sem acentos)
    # Exemplo: "你好" vira "ni hao" usando apenas o alfabeto a-z
    lista_pinyin = lazy_pinyin(texto_zh, style=Style.NORMAL)
    texto_pinyin = " ".join(lista_pinyin)
    print(f"[Max-Pinyin] (Pinyin): {texto_pinyin}")

    if not os.path.isfile(PIPER_EXE) or not os.path.isfile(PIPER_MODEL_PINYIN):
        print("[Max-Pinyin] Erro: piper.exe ou modelo não encontrados.")
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        caminho_wav = tmp.name

    try:
        inicio = time.monotonic()
        cmd = [PIPER_EXE, "--model", PIPER_MODEL_PINYIN, "--output_file", caminho_wav]
        processo = subprocess.run(
            cmd,
            input=texto_pinyin.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15
        )
        if processo.returncode != 0:
            print(f"[Max-Pinyin] Erro no piper: {processo.stderr.decode('utf-8', errors='ignore')}")
            return

        tocar_wav(caminho_wav, bloqueante=True)
    except Exception:
        traceback.print_exc()
    finally:
        try:
            os.remove(caminho_wav)
        except OSError:
            pass


def falar_com_introducao(texto_zh: str):
    evento_parar_musica = threading.Event()
    thread_musica = threading.Thread(target=_gerenciar_musica, args=(evento_parar_musica,), daemon=True)
    thread_musica.start()

    time.sleep(ATRASO_MUSICA_SEGUNDOS)
    falar_pinyin(texto_zh)

    time.sleep(SEGUNDOS_MUSICA_APOS_FALAR)
    evento_parar_musica.set()
    thread_musica.join(timeout=1)


def responder(texto_pt: str):
    print(f"[Você] {texto_pt}")
    if any(palavra in texto_pt for palavra in PALAVRAS_SAIR):
        falar_com_introducao(DESPEDIDA)
        encerrar_evento.set()
        return
    try:
        resposta_zh = perguntar_llm(texto_pt)
    except Exception as e:
        print(f"Erro LLM: {e}")
        return
    falar_com_introducao(resposta_zh)


def main():
    carregar_cache_musica()
    listener = Listener(on_text=responder, lang="pt", device=MIC_DEVICE)
    listener.start()
    print("[Max-Pinyin] Pronto! O bot traduz para chinês, converte para Pinyin (a-z) e fala com o piper.exe.")
    try:
        encerrar_evento.wait()
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()


if __name__ == "__main__":
    main()