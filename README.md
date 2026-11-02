# AI Personalized Learning Path Generator

Adaptive mathematics practice. A model trained on Junyi Academy data predicts how likely a student is to solve each exercise,
and a rule-based engine turns that into a path: revise weak topics, continue topics in progress, unlock new ones.

```
frontend/            React + Vite app (login, onboarding, practice, learning path, progress)
adaptive_learning/   engine/ + models/ (ML), backend/ (FastAPI + SQLite + JWT), tests/
docs/                SCOPE_AND_EXTENSION.md
```

## Run it (two terminals)

**1. Backend** (from `adaptive_learning/`)
```
cd adaptive_learning
python -m venv .venv
.venv\Scripts\activate                 # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt -r backend/requirements.txt    # scikit-learn must be 1.6.1
uvicorn backend.app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

**2. Frontend** (from `frontend/`)
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. To point at another backend, set `VITE_API_URL` in `frontend/.env`.

## Tests
```
cd adaptive_learning
python -m pytest -q tests backend/tests     # 34 engine + 46 backend tests
```

## Important limits
The dataset has exercise IDs and topic labels but **no question text or answers**, so students solve each recommended
exercise themselves and report whether they got it right. See `docs/SCOPE_AND_EXTENSION.md`.
