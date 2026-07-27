"""
Prompt injection protection for SelfSmart AI.
Blocks known jailbreak and injection patterns before they reach the LLM.
"""

import re
from fastapi import HTTPException

# Patterns that indicate prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"forget\s+everything\s+(you\s+know|above)",
    r"you\s+are\s+now\s+(a|an)\s+(?!assistant|helpful|smart)",  # "you are now a hacker"
    r"act\s+as\s+(if\s+you\s+are|a)\s+(?!an?\s+(helpful|smart|friendly))",
    r"do\s+not\s+(follow|obey)\s+(the\s+)?(rules?|instructions?|guidelines?)",
    r"system\s*:\s*.{0,50}(ignore|bypass|override)",
    r"<\s*system\s*>",  # XML-style system tag injection
    r"\[INST\].*override",  # Llama-style instruction injection
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _INJECTION_PATTERNS]


def sanitize_user_message(message: str) -> str:
    """
    Validate user message for prompt injection attempts.
    Raises HTTPException 400 if injection is detected.
    Returns the original message if safe.
    """
    for i, pattern in enumerate(_COMPILED):
        if pattern.search(message):
            raise HTTPException(
                status_code=400,
                detail=f"Message contains disallowed content (pattern {i+1}). Please rephrase.",
            )
    return message


__all__ = ["sanitize_user_message"]
