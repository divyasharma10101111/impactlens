import re
from typing import Dict, List, Tuple

def normalize_text(text: str) -> str:
    return (text or "").lower()

def tag_sponsors_text(text: str, sponsor_patterns: Dict[str, List[str]]) -> List[Tuple[str, float, str]]:
    """
    Returns list of (sponsor_name, confidence, reason)
    """
    t = normalize_text(text)
    hits: List[Tuple[str, float, str]] = []
    for sponsor, patterns in sponsor_patterns.items():
        for pat in patterns:
            if re.search(pat, t, flags=re.IGNORECASE):
                hits.append((sponsor, 0.85, f"matched:{pat}"))
                break
    return hits
