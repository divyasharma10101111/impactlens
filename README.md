# Cricket Sponsor & Content Intelligence — MVP (Python)

This repo is a **sellable MVP** for:
- **Sponsor detection** (text tagging first; vision optional)
- **Sponsor ROI analytics** (Share-of-Voice, top creatives, weekly deltas)
- **Weekly PDF report** (ReportLab) + **Dashboard** (Streamlit)

## 1) Quickstart (local with Docker)
### Prereqs
- Docker + Docker Compose installed

### Run
```bash
cp .env.example .env
docker compose up --build
```

This starts:
- Postgres (db)
- Redis (queue)
- Worker (Celery)
- Streamlit dashboard

### Load sample data
In a new terminal:
```bash
docker compose exec worker python scripts/init_db.py
docker compose exec worker python scripts/import_posts_csv.py data/sample_posts.csv
docker compose exec worker python scripts/run_weekly.py --client "Demo Client" --week_ending 2026-02-08
```

Open dashboard:
- http://localhost:8501

Generated report PDF:
- `reports/Demo_Client_weekly_2026-02-08.pdf` (inside the worker container volume; also mirrored to ./reports on your machine)

## 2) Your MVP workflow for real clients
1. Get a CSV export (or API) of posts + metrics weekly/daily.
2. Import to DB.
3. Run tagging + KPI calc.
4. Generate PDF + share dashboard link.

## 3) Data format (CSV)
See `data/sample_posts.csv`. Required columns:
- client, account, platform, post_id, url, posted_at, caption, media_type, language
- views, likes, comments, shares

## 4) Vision / logo detection (optional)
The MVP ships with text tagging. Vision is a plug-in:
- Add `ultralytics` to requirements
- Add logo classes + a model
- Run `processing/logo_detect.py` (template provided)

## 5) Notes
- For pilots, keep a **human QA** step (dashboard page) to correct sponsor tags.
- Never scrape private content without permission; prefer client-owned exports.



## Quickstart (no client data)
From the project root (the folder that contains `app/`), run:

```bash
python scripts/init_db.py
python scripts/import_posts_csv.py data/demo_posts_synthetic.csv
streamlit run dashboard/streamlit_app.py
```

If you see `ModuleNotFoundError: No module named 'app'`, it means you are NOT running from project root.
Fix by `cd` into the folder that contains `app/` and run Streamlit again.

### One-command demo
macOS/Linux:
```bash
bash run_demo.sh
```

Windows:
```bat
run_demo.bat
```
