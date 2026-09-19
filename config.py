import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VOICE_DIR = BASE_DIR / "voice"

PIPER_EXE = VOICE_DIR / "piper" / ("piper.exe" if sys.platform == "win32" else "piper")
PIPER_MODEL = VOICE_DIR / "models" / "br.onnx"
PIPER_LENGTH_SCALE = 1.0 
PIPER_SENTENCE_SILENCE = 0.1