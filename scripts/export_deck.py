import argparse
from pathlib import Path
from dateutil import parser as dtparser

from processing.run_tagging import tag_unprocessed_posts_text
from analytics.kpis import week_range, compute_sov, top_posts
from analytics.alerts import compute_under_delivery_alerts
from analytics.benchmarks import compute_content_benchmarks
from analytics.recommendations import compute_next_week_recommendations
from reporting.pptx_deck import build_client_deck_pptx

def safe_filename(s: str) -> str:
    return "".join([c if c.isalnum() or c in "-_." else "_" for c in s]).strip("_")

def main(client: str, week_ending: str):
    week_end_dt = dtparser.parse(week_ending)
    start, end = week_range(week_end_dt)

    tag_unprocessed_posts_text(client_name=client, limit=8000)
    sov = compute_sov(client, start, end)
    tops = top_posts(client, start, end, limit=15)
    alerts = compute_under_delivery_alerts(client, week_end_dt, lookback_weeks=4, threshold_pct=0.20)
    benchmarks = compute_content_benchmarks(client, week_end_dt, lookback_weeks=8)
    recs = compute_next_week_recommendations(client, week_end_dt, lookback_weeks=8)

    deck = build_client_deck_pptx(client, start, end, sov, tops, alerts, benchmarks, recs, brand_name="ImpactLens")
    Path("reports").mkdir(exist_ok=True)
    out = f"reports/{safe_filename(client)}_weekly_{end.date()}.pptx"
    with open(out, "wb") as f:
        f.write(deck)
    print(f"Exported deck: {out}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--client", required=True)
    ap.add_argument("--week_ending", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()
    main(args.client, args.week_ending)
