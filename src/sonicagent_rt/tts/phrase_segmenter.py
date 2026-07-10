"""Deterministic phrase segmentation baseline."""
import re

_BOUNDARY = re.compile(r"(?<=[.!?;:])\s+")

def segment_text(text: str, *, max_chars: int = 180) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    chunks: list[str] = []
    for sentence in _BOUNDARY.split(text):
        while len(sentence) > max_chars:
            cut = sentence.rfind(" ", 0, max_chars + 1)
            cut = cut if cut > 0 else max_chars
            chunks.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if sentence:
            chunks.append(sentence)
    return chunks
