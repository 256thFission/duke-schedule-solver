# Duke Schedule Solver

Optimal course schedule generator for Duke University.
Uses Binary Integer Programming (OR-Tools) to maximize a weighted combination
of course quality metrics (from evaluations) subject to time/requirement constraints.

## Architecture

- **Pipeline** (`scripts/`): Ingests catalog + evaluations, applies Bayesian-shrunk quality metrics
- **Solver** (`scripts/solver/`): BIP optimizer with configurable constraints
- **Backend** (`backend/`): FastAPI API serving the solver
- **Frontend** (`frontend/`): React + Zustand wizard UI

## Quick Start (Local Dev)

### Prerequisites

- Python 3.10+, Node.js 18+
- conda (recommended) or pip

### Backend

```bash
conda env create -f environment.yml && conda activate solver
pip install -e .  # install project packages for imports
cd backend && python -m uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173

## Data Pipeline

```bash
python scripts/run_pipeline.py --config config/pipeline_config.json
```

Pipeline stages:
1. **Ingest** — Load raw JSON/CSV files
2. **Normalize** — Parse times, days, course codes
3. **Merge** — Match evaluations to catalog sections
4. **Aggregate** — Bayesian shrinkage + z-scores
5. **Export** — Generate solver-ready JSON

## Deployment

See [DEPLOY.md](DEPLOY.md) for EC2/Docker deployment instructions.

## License

MIT — see [LICENSE](LICENSE).
