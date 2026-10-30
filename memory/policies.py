"""Long-term memory allow-list and exclusion rules."""
import re

SENSITIVE = re.compile(r"password|passwd|passcode|\botp\b|one[- ]time (?:password|code)|api[_ -]?key|pin\b|cvv|card number|bank account|payment credential|secret|ssn|medical diagnosis|\b\d{6}\b|\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,})\b", re.I)
TEMPORARY = re.compile(r"today|tomorrow|this week|for now|temporary|one-time|just this once", re.I)

def classify_memory(text: str) -> tuple[bool, str]:
    if SENSITIVE.search(text): return False, "Sensitive credentials or personal data are never saved."
    if TEMPORARY.search(text): return False, "Temporary information is not useful as long-term memory."
    stable_markers = ("prefer", "my programme", "my program", "i study", "i am in semester", "i'm in semester", "please explain", "learning preference")
    if not any(marker in text.lower() for marker in stable_markers):
        return False, "Only stable preferences or study context are saved."
    if len(text) > 240: return False, "Memory entries must be concise."
    return True, "Stable study context or communication preference."
