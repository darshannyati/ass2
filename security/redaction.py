"""Best-effort credential redaction before persistence, tracing, or memory writes."""
import re
_PATTERNS = [
    re.compile(r"(?i)\b(password|passwd|passcode|otp|one[- ]time (?:password|code)|api[_ -]?key|secret)\s*(?:is|=|:)?\s*([^\s,;]+)"),
    re.compile(r"\b\d{6}\b"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,})\b"),
]
def redact_sensitive(text: str) -> tuple[str, bool]:
    original=text; text=_PATTERNS[0].sub(lambda m: f"{m.group(1)} [REDACTED]", text)
    text=_PATTERNS[1].sub("[REDACTED-CODE]", text)
    text=_PATTERNS[2].sub("[REDACTED-KEY]", text)
    return text, text != original
