# GreenNexa Backend

AI-powered sustainable facility intelligence — backend service.

## Stack
- **Framework:** FastAPI
- **Database:** PostgreSQL (SQLite for testing)
- **ORM:** SQLAlchemy 2.0
- **AI/ML:** Pandas, NumPy, scikit-learn

## Quick Start

```bash
cd backend

# 1. Create virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env — set DATABASE_URL

# 4. Run server
uvicorn app.main:app --reload

# 5. Run tests (SQLite, no PostgreSQL needed)
pytest tests/ -v
```

## API Docs

After starting the server: http://localhost:8000/docs

## Module Overview

| Module | Path | Purpose |
|--------|------|---------|
| Database models | `app/db/models.py` | SQLAlchemy ORM tables |
| Anomaly Detector | `app/ai/anomaly_detector.py` | Statistical anomaly detection |
| Recommendation Engine | `app/ai/recommender.py` | AI recommendation generation |
| Anomaly API | `app/api/v1/anomalies.py` | Anomaly CRUD endpoints |
| Recommendation API | `app/api/v1/recommendations.py` | Recommendation endpoints |

## Important Notes

- Recommendations are **decision-support suggestions**, not verified diagnoses.
- No recommendation is generated for NORMAL severity readings.
- If fewer than 5 historical readings exist, an "Insufficient data" response is returned instead of an invented recommendation.
- All data is scoped to `organisation_id` — cross-organisation access is rejected.
