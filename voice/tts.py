import atexit
import json
import queue
import shutil
import subprocess
import tempfile
import threading
import wave
from collections import deque
from pathlib import Path

import numpy as np


def trim_silence(audio, sample_rate, threshold=300, keep_ms=60):
    """Corta o silêncio do começo e do fim do áudio (int16)."""
    idx = np.where(np.abs(audio) > threshold)[0]
    if idx.size == 0:
        return audio
    keep = int(sample_rate * keep_ms / 1000)
    start = max(idx[0] - keep, 0)
    end = min(idx[-1] + keep, len(audio))
    return audio[start:end]


def shorten_pauses(audio, sample_rate, threshold=300, max_pause_ms=180, frame_ms=10):
    """Encolhe silêncios longos no meio do áudio para no máximo max_pause_ms."""
    frame = int(sample_rate * frame_ms / 1000)
    n = len(audio) // frame
    if n == 0:
        return audio
    frames = audio[: n * frame].reshape(n, frame)
    silent = np.abs(frames).max(axis=1) < threshold
    max_frames = max_pause_ms // frame_ms

    keep = np.ones(n, dtype=bool)
    i = 0
    while i < n:
        if silent[i]:
            j = i
            while j < n and silent[j]:
                j += 1
            if j - i > max_frames:
                keep[i + max_frames : j] = False
            i = j
        else:
            i += 1

    out = frames[keep].reshape(-1)
    return np.concatenate([out, audio[n * frame :]])


_SEM_JANELA = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class PiperTTS:
    """Chama o executável do Piper e devolve o áudio como array int16 (mono).

    MODO PERSISTENTE (padrão): o piper.exe é aberto UMA vez, na criação do objeto, e fica
    esperando as frases. Antes, cada frase abria um piper.exe novo e recarregava a voz
    inteira do disco (o que atrasava toda fala). Se algo der errado, cai sozinho para o
    modo antigo (um processo por frase), então não deixa o Max mudo.

    Mesma interface de antes: PiperTTS(exe, model, length_scale, sentence_silence),
    .synthesize(texto) e .sample_rate.
    """

    def __init__(self, exe, model, length_scale=1.0, sentence_silence=0.1,
                 persistente=True, timeout=30.0):
        self.exe = Path(exe)
        self.model = Path(model)
        config = Path(str(self.model) + ".json")

        for p in (self.exe, self.model, config):
            if not p.exists():
                raise FileNotFoundError(f"Arquivo do Piper não encontrado: {p}")

        self.sample_rate = json.loads(config.read_text(encoding="utf-8"))["audio"]["sample_rate"]
        self.length_scale = length_scale
        self.sentence_silence = sentence_silence
        self.timeout = timeout

        self._lock = threading.Lock()
        self._proc = None
        self._saidas = None
        self._erros = deque(maxlen=20)
        self._falhas = 0
        self._pasta_wav = None
        self._persistente = bool(persistente)
        atexit.register(self.close)

        if self._persistente:
            try:
                self._pasta_wav = Path(tempfile.mkdtemp(prefix="piper_tts_"))
                # aquece: carrega a voz agora (na abertura do programa), não na 1ª fala
                self._synth_persistente("Oi.")
                print("[PiperTTS] modo persistente ativo (voz carregada uma vez só)")
            except Exception as e:
                print(f"[PiperTTS] modo persistente indisponível ({e}); usando o modo antigo.")
                self._persistente = False
                self._matar()

    # ---------- API pública ----------
    def synthesize(self, text: str) -> np.ndarray:
        audio = None
        if self._persistente:
            try:
                audio = self._synth_persistente(text)
                self._falhas = 0
            except Exception as e:
                self._falhas += 1
                print(f"[PiperTTS] modo persistente falhou ({e}).")
                if self._falhas >= 2:
                    self._persistente = False
                    self._matar()
                    print("[PiperTTS] desativado; daqui para frente usa o modo antigo.")
        if audio is None:
            audio = self._synth_por_chamada(text)   # esta frase sai pelo modo antigo

        audio = shorten_pauses(audio, self.sample_rate)
        return trim_silence(audio, self.sample_rate)

    def close(self):
        self._matar()
        if self._pasta_wav:
            shutil.rmtree(self._pasta_wav, ignore_errors=True)

    # ---------- modo persistente ----------
    def _args_voz(self):
        return ["--model", str(self.model),
                "--length_scale", str(self.length_scale),
                "--sentence_silence", str(self.sentence_silence)]

    def _iniciar(self):
        cmd = [str(self.exe), *self._args_voz(), "--output_dir", str(self._pasta_wav)]
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=self.exe.parent,                 # o Piper acha o espeak-ng-data aqui
            creationflags=_SEM_JANELA,
        )
        fila = queue.Queue()
        self._proc, self._saidas = proc, fila
        threading.Thread(target=self._ler_stdout, args=(proc, fila), daemon=True).start()
        threading.Thread(target=self._ler_stderr, args=(proc,), daemon=True).start()

    @staticmethod
    def _ler_stdout(proc, fila):
        # o Piper imprime uma linha (o caminho do .wav) a cada frase pronta
        try:
            for linha in iter(proc.stdout.readline, b""):
                fila.put(linha)
        except (ValueError, OSError):
            pass
        fila.put(None)                           # None = o processo terminou

    def _ler_stderr(self, proc):
        # precisa esvaziar o stderr, senão o Piper trava quando o buffer enche
        try:
            for linha in iter(proc.stderr.readline, b""):
                self._erros.append(linha.decode("utf-8", errors="replace").strip())
        except (ValueError, OSError):
            pass

    def _matar(self):
        proc, self._proc = self._proc, None
        if proc is None:
            return
        for acao in (proc.stdin.close, proc.terminate):
            try:
                acao()
            except Exception:
                pass
        try:
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _synth_persistente(self, text: str) -> np.ndarray:
        linha = " ".join(text.split())           # o Piper lê UMA frase por linha
        if not linha:
            return np.zeros(0, dtype=np.int16)

        with self._lock:                          # um pedido por vez no mesmo processo
            if self._proc is None or self._proc.poll() is not None:
                self._iniciar()
            proc, fila = self._proc, self._saidas
            proc.stdin.write((linha + "\n").encode("utf-8"))
            proc.stdin.flush()
            try:
                saida = fila.get(timeout=self.timeout)
            except queue.Empty:
                self._matar()
                raise TimeoutError(f"o Piper não respondeu em {self.timeout:.0f}s")
            if saida is None:
                erro = " | ".join(list(self._erros)[-3:])
                self._matar()
                raise RuntimeError(f"o Piper encerrou sozinho. {erro}")

        return self._ler_wav(saida.decode("utf-8", errors="replace").strip())

    def _ler_wav(self, caminho: str) -> np.ndarray:
        p = Path(caminho)
        if not p.exists():
            raise FileNotFoundError(f"o Piper não gerou o arquivo: {caminho}")
        try:
            with wave.open(str(p), "rb") as w:
                if w.getsampwidth() != 2 or w.getnchannels() != 1:
                    raise ValueError("formato de áudio inesperado (esperava mono 16 bits)")
                if w.getframerate() != self.sample_rate:
                    raise ValueError(f"taxa {w.getframerate()} Hz, esperava {self.sample_rate} Hz")
                dados = w.readframes(w.getnframes())
        finally:
            try:
                p.unlink()
            except OSError:
                pass
        return np.frombuffer(dados, dtype=np.int16)

    # ---------- modo antigo (um processo por frase) ----------
    def _synth_por_chamada(self, text: str) -> np.ndarray:
        cmd = [str(self.exe), *self._args_voz(), "--output_raw"]
        proc = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            capture_output=True,
            cwd=self.exe.parent,
            creationflags=_SEM_JANELA,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore"))
        return np.frombuffer(proc.stdout, dtype=np.int16)