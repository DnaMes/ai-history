import re
from typing import Iterable, List
from ..core.models import UnifiedSession, Role


def extract_rules(sessions: Iterable[UnifiedSession], max_rules: int = 30) -> List[str]:
    """Extract rule-like sentences from assistant messages."""
    candidates = []
    keywords = [
        "must",
        "should",
        "avoid",
        "do not",
        "never",
        "always",
        "best practice",
        "recommend",
        "prefer",
    ]

    def score_sentence(sentence: str) -> int:
        s = sentence.lower()
        score = 0
        for kw in keywords:
            if kw in s:
                score += 1
        return score

    for session in sessions:
        for msg in session.messages:
            if msg.role != Role.ASSISTANT:
                continue
            content = msg.content or ""
            for sentence in re.split(r'(?<=[.!?])\s+', content):
                sentence = sentence.strip()
                if len(sentence) < 20 or len(sentence) > 180:
                    continue
                if score_sentence(sentence) > 0:
                    candidates.append(sentence)

    ranked = sorted(set(candidates), key=score_sentence, reverse=True)
    return ranked[:max_rules]
