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

# --- Microfone ---
# Vazio = usa o padrão do sistema. Aceita o índice (ex.: 14) ou parte do nome
# do aparelho (ex.: QCY), que é mais estável porque o índice muda quando se
# liga ou desliga um dispositivo. Use /mics no programa para ver a lista.
MIC_DEVICE = os.getenv("MIC_DEVICE", "")

# --- IA (Groq) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_TIMEOUT = 15

# --- Dados ---
DATA_DIR = BASE_DIR / "data"
CACHE_FILE = DATA_DIR / "cache" / "respostas.json"