import sys
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
VOICE_DIR = BASE_DIR / "voice"

load_dotenv(BASE_DIR / ".env")

PIPER_EXE = VOICE_DIR / "piper" / ("piper.exe" if sys.platform == "win32" else "piper")
PIPER_MODEL = VOICE_DIR / "models" / "br.onnx"
PIPER_LENGTH_SCALE = 1.0 
PIPER_SENTENCE_SILENCE = 0.1

# --- IA (Groq) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_TIMEOUT = 15

# --- Dados ---
DATA_DIR = BASE_DIR / "data"
CACHE_FILE = DATA_DIR / "cache" / "respostas.json"