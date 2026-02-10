# Keep this file client-specific in production (one dict per client or per league).
# Start with 20-50 sponsor names + variants. Iterate weekly.

SPONSOR_PATTERNS = {
    "Dream11": [r"\bdream\s*11\b", r"@dream11", r"#dream11", r"\bd11\b"],
    "Tata": [r"\btata\b", r"#tataipl", r"@tata"],
    "Jio": [r"\bjio\b", r"@reliancejio", r"#jio"],
    "Paytm": [r"\bpaytm\b", r"@paytm", r"#paytm"],
    "CRED": [r"\bcred\b", r"@cred_club", r"#cred"],
}
