import argparse
from dateutil import parser as dtparser

from processing.run_tagging import tag_unprocessed_posts_text
from analytics.kpis import week_range, compute_sov, top_posts
from analytics.alerts import compute_under_delivery_alerts
from analytics.benchmarks import compute_content_benchmarks
from analytics.recommendations import compute_next_week_recommendations
from reporting.premium_pdf import generate_premium_weekly_pdf

def safe_filename(s: str) -> str:
    return "".join([c if c.isalnum() or c in "-_." else "_" for c in s]).strip("_")

def main(client: str, week_ending: str):
    week_end_dt = dtparser.parse(week_ending)
    start, end = week_range(week_end_dt)

    created = tag_unprocessed_posts_text(client_name=client, limit=8000)
    print(f"Created {created} sponsor tags from text.")

    sov = compute_sov(client, start, end)
    tops = top_posts(client, start, end, limit=15)
    alerts = compute_under_delivery_alerts(client, week_end_dt, lookback_weeks=4, threshold_pct=0.20)
    benchmarks = compute_content_benchmarks(client, week_end_dt, lookback_weeks=8)
    recs = compute_next_week_recommendations(client, week_end_dt, lookback_weeks=8)

    out = f"reports/{safe_filename(client)}_weekly_{end.date()}.pdf"
    generate_premium_weekly_pdf(out, client, start, end, sov, tops, alerts, benchmarks, recs, brand_name="ImpactLens")
    print(f"Generated report: {out}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--client", required=True)
    ap.add_argument("--week_ending", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()
    main(args.client, args.week_ending)
