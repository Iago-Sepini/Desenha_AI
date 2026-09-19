import re

_URL = re.compile(r"https?://\S+")
_MARKDOWN = re.compile(r"[*_#`>~]+")
_EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]+")
_SPACES = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Remove o que o TTS não deve ler (links, markdown, emojis)."""
    text = _URL.sub("", text)
    text = _MARKDOWN.sub("", text)
    text = _EMOJI.sub("", text)
    return _SPACES.sub(" ", text).strip()


def split_sentences(text: str, max_len: int = 220, min_len: int = 70) -> list[str]:
    """Divide em frases. Frases curtas são juntadas à seguinte (menos pausas,
    mais contexto para a entonação); frases muito longas são cortadas."""
    text = clean_text(text)
    out = []
    for part in re.split(r"(?<=[.!?…])\s+", text):
        while len(part) > max_len:
            cut = part.rfind(",", 0, max_len)
            if cut == -1:
                cut = part.rfind(" ", 0, max_len)
            if cut == -1:
                cut = max_len
            out.append(part[: cut + 1].strip())
            part = part[cut + 1 :].strip()
        if part:
            out.append(part)

    merged = []
    for s in out:
        if merged and len(merged[-1]) < min_len:
            merged[-1] += " " + s
        else:
            merged.append(s)
    return merged