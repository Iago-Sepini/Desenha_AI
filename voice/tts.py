import json
import subprocess
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


class PiperTTS:
    """Chama o executável do Piper e devolve o áudio como array int16 (mono)."""

    def __init__(self, exe, model, length_scale=1.0, sentence_silence=0.1):
        self.exe = Path(exe)
        self.model = Path(model)
        config = Path(str(self.model) + ".json")

        for p in (self.exe, self.model, config):
            if not p.exists():
                raise FileNotFoundError(f"Arquivo do Piper não encontrado: {p}")

        self.sample_rate = json.loads(config.read_text(encoding="utf-8"))["audio"]["sample_rate"]
        self.length_scale = length_scale
        self.sentence_silence = sentence_silence

    def synthesize(self, text: str) -> np.ndarray:
        cmd = [
            str(self.exe),
            "--model", str(self.model),
            "--output_raw",
            "--length_scale", str(self.length_scale),
            "--sentence_silence", str(self.sentence_silence),
        ]
        proc = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            capture_output=True,
            cwd=self.exe.parent,  # o Piper acha o espeak-ng-data aqui
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore"))

        audio = np.frombuffer(proc.stdout, dtype=np.int16)
        audio = shorten_pauses(audio, self.sample_rate)
        return trim_silence(audio, self.sample_rate)