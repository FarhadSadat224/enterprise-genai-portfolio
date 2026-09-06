import re
import unicodedata
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str | None = None


SECRET = re.compile(
    r"sk-[a-zA-Z0-9_-]{12,}|-----BEGIN (?:RSA )?PRIVATE KEY-----|\b\d{3}-\d{2}-\d{4}\b"
)


def check_input(text: str) -> GuardrailResult:
    normalized = " ".join(unicodedata.normalize("NFKC", text).casefold().split())
    if any(
        p in normalized
        for p in ("ignore all previous instructions", "reveal system prompt", "dump secrets")
    ) or SECRET.search(text):
        return GuardrailResult(False, "Request blocked by safety checks.")
    return GuardrailResult(True)


def check_output(text: str) -> GuardrailResult:
    return GuardrailResult(not bool(SECRET.search(text)), "Potential sensitive data")
