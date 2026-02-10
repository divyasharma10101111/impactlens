import argparse
from datetime import datetime, timedelta
from pathlib import Path
import random
import pandas as pd

SPONSORS = ["Dream11", "Tata", "Jio", "Paytm", "CRED"]
PLATFORMS = ["instagram", "youtube"]
MEDIA_BY_PLATFORM = {
    "instagram": ["reel", "post"],
    "youtube": ["short", "video"],
}
LANGS = ["Hindi", "English"]

def gen_caption(sponsor: str, lang: str) -> str:
    if lang == "Hindi":
        return f"{sponsor} ke saath matchday vibes! #Win #Cricket @{sponsor.lower()} #reel"
    return f"Matchday moments presented by {sponsor}. #Cricket #{sponsor}"

def main(out_csv: str, weeks: int, seed: int):
    random.seed(seed)
    end = datetime(2026, 2, 8, 21, 0, 0)
    start = end - timedelta(days=7 * weeks - 1)

    clients = [
        ("Mumbai Falcons (Demo)", "mumbai_falcons"),
        ("Delhi Strikers (Demo)", "delhi_strikers"),
    ]

    rows = []
    dt = start
    post_counter = 1

    while dt <= end:
        for client_name, slug in clients:
            for platform in PLATFORMS:
                for _ in range(random.randint(0, 2)):
                    sponsor = random.choice(SPONSORS)
                    media_type = random.choice(MEDIA_BY_PLATFORM[platform])
                    lang = random.choices(LANGS, weights=[0.6, 0.4])[0]

                    base_views = random.randint(80_000, 400_000)
                    if platform == "instagram" and media_type == "reel" and lang == "Hindi":
                        base_views *= random.randint(3, 7)

                    # Force under-delivery for Paytm in last week
                    if sponsor == "Paytm" and dt.date() >= datetime(2026, 2, 2).date():
                        base_views = int(base_views * 0.55)

                    likes = int(base_views * random.uniform(0.015, 0.045))
                    comments = int(base_views * random.uniform(0.001, 0.004))
                    shares = int(base_views * random.uniform(0.001, 0.006))

                    account = f"{slug}_{platform}"
                    post_id = f"{slug}_{platform}_{post_counter}"
                    url = f"https://example.com/{post_id}"

                    rows.append({
                        "client": client_name,
                        "account": account,
                        "platform": platform,
                        "post_id": post_id,
                        "url": url,
                        "posted_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "caption": gen_caption(sponsor, lang),
                        "media_type": media_type,
                        "language": lang,
                        "views": int(base_views),
                        "likes": likes,
                        "comments": comments,
                        "shares": shares,
                    })
                    post_counter += 1

        dt += timedelta(days=random.randint(1, 2))

    df = pd.DataFrame(rows).sort_values("posted_at")
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"Wrote demo CSV: {out_csv} ({len(df)} rows)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/demo_posts_synthetic.csv")
    ap.add_argument("--weeks", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    main(args.out, args.weeks, args.seed)
