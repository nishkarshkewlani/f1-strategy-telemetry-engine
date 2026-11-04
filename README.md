# F1 Strategy & Telemetry Engine

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/database-SQLite%20%7C%20PostgreSQL-green.svg)](https://www.sqlite.org/)
[![Status](https://img.shields.io/badge/status-M0--M8%20Complete-brightgreen.svg)]()

> **Notice:** This is an independent educational motorsport analytics and strategy simulation platform. It is not affiliated with, endorsed by, or sponsored by Formula 1, the FIA, or Formula 1 teams.

---

## 1. Project Overview & Differentiators

The **F1 Strategy & Telemetry Engine** is an end-to-end race-engineering decision-support application. It ingests historical Formula 1 session, lap, tyre stint, pit-stop, weather, telemetry, and race control data into a relational database, performs production SQL analytics, trains race-aware lap-time regressors, and simulates alternative pit-stop strategies under green-flag and safety-car scenarios.

### Key Differentiators
1. **Race-Based Model Validation**: Respects temporal and event boundaries; prevents data leakage by holding out entire sessions/races rather than randomly sampling neighbouring laps.
2. **Contextual Tyre-Age Analytics**: Models pace degradation while accounting for stint duration, fuel load progression, and track context.
3. **Prescriptive Strategy Simulator**: Evaluates multi-scenario candidate pit strategies (one-stop, two-stop) with explicit incremental pit loss accounting to avoid double-counting.
4. **Conditional Safety-Car Dynamics**: Recalculates candidate costs during safety-car windows dynamically rather than relying on naive heuristic rules.
5. **Auditable & Explainable Decision Support**: Discloses empirical uncertainty intervals, sensitivity indicators, and clear plain-language rationales for strategy rankings.

---

## 2. Architecture & Data Flow

```text
 PUBLIC F1 DATA SOURCES
 OpenF1 API / Jolpica API
         |
         v
 INGESTION / API CLIENT (requests, backoff, retries, schemas)
         |
         v
 RAW DATA SNAPSHOTS (JSON / data manifests)
         |
         v
 TRANSFORM / FEATURE LAYER (lap-to-stint mapping, tyre-age logic)
         |
         v
 RELATIONAL DATABASE (SQLite / PostgreSQL)
 meetings | sessions | drivers | laps | telemetry | stints | pit_stops | weather | race_events
         |
  +------+------+
  |             |
  v             v
SQL ANALYTICS  MODEL PIPELINE (scikit-learn Pipelines, race-aware split)
  |             |
  +------+------+
         |
         v
 STRATEGY SIMULATOR (candidate search, incremental pit loss, safety-car logic)
         |
         v
 STREAMLIT DASHBOARD (multipage interactive UI, Plotly charts)
```

---

## 3. Repository Structure

```text
f1-strategy-telemetry-engine/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── config/
│   ├── __init__.py
│   └── settings.py
├── data/
│   ├── raw/
│   ├── processed/
│   └── sample/
├── ingestion/
│   ├── __init__.py
│   ├── api_client.py
│   ├── fetch_sessions.py
│   ├── fetch_session_data.py
│   ├── normalize.py
│   └── validate.py
├── database/
│   ├── __init__.py
│   ├── schema.sql
│   ├── db.py
│   ├── repository.py
│   └── load_data.py
├── sql_queries/
│   ├── driver_pace.sql
│   ├── lap_delta.sql
│   ├── tyre_compound.sql
│   ├── stint_summary.sql
│   ├── pit_stops.sql
│   └── outlier_laps.sql
├── analysis/
│   ├── __init__.py
│   ├── lap_analysis.py
│   ├── telemetry_analysis.py
│   ├── tyre_analysis.py
│   └── data_quality.py
├── features/
│   ├── __init__.py
│   └── build_features.py
├── models/
│   ├── __init__.py
│   ├── train_lap_time.py
│   ├── train_tyre_model.py
│   ├── predict.py
│   └── evaluate.py
├── strategy/
│   ├── __init__.py
│   ├── cost_model.py
│   ├── candidate_generator.py
│   ├── pit_optimizer.py
│   └── scenario_simulator.py
├── dashboard/
│   ├── __init__.py
│   ├── components.py
│   └── pages/
│       ├── 1_Race_Explorer.py
│       ├── 2_Telemetry.py
│       ├── 3_Tyre_Analytics.py
│       ├── 4_Pit_Strategy.py
│       ├── 5_Scenario_Lab.py
│       └── 6_Model_Evaluation.py
├── tests/
│   ├── __init__.py
│   ├── test_api_client.py
│   ├── test_data_validation.py
│   ├── test_database.py
│   ├── test_features.py
│   ├── test_models.py
│   └── test_strategy.py
└── artifacts/
```

---

## 4. Setup & Installation

### Windows PowerShell
```powershell
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install project dependencies
python -m pip install -r requirements.txt

# Copy environment configuration
Copy-Item .env.example .env
```

### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

---

## 5. Quick Start

```powershell
# From project root
Set-Location "C:\path\to\f1-strategy-telemetry-engine"

# 1. Run all 25 tests
& ".venv\Scripts\python.exe" -m pytest -v

# 2. Ingest a new session (e.g. session 9157 = 2023 Monza Race)
$env:PYTHONPATH = "."
& ".venv\Scripts\python.exe" -m ingestion.fetch_session_data --session_key 9157 --telemetry_drivers 2
& ".venv\Scripts\python.exe" -m database.load_data --session_key 9157

# 3. Retrain lap-time & tyre models
& ".venv\Scripts\python.exe" -m models.train_lap_time
& ".venv\Scripts\python.exe" -m models.train_tyre_model

# 4. Launch dashboard (requires network access)
& ".venv\Scripts\python.exe" -m streamlit run app.py
# → open http://localhost:8501
```

---

## 6. Live Data & Model Results

### Ingested Sessions
| session_key | Circuit | Type | Laps | Stints | Pit Stops | Telemetry rows |
|-------------|---------|------|------|--------|-----------|----------------|
| 9126 | Silverstone | Race | 974 | 44 | 24 | 67,142 |
| 9157 | Monza | Race | 968 | 45 | 25 | 71,962 |

### Lap-Time Model Holdout (Monza – 902 test laps)
| Model | MAE (s) | RMSE (s) |
|-------|---------|----------|
| Dummy baseline | 6.012 | — |
| Ridge linear | 5.932 | — |
| **HistGBM (selected)** | **0.296** | **0.516** |
| Random Forest | 5.586 | — |

> *Train on Silverstone, test on Monza. Per-driver MAE range: 0.20s (ALO) – 0.39s (PIA).*

---

## 7. Development Milestones

- [x] **M0: Foundation & Setup**: Repository structure, configuration module, virtualenv setup, and dependencies.
- [x] **M1: API Discovery & Session Selection**: Dynamic discovery of 2023+ OpenF1 sessions and schema contracts.
- [x] **M2: Data Ingestion & Validation**: Robust data fetcher with retries, exponential backoff, raw storage, and validation.
- [x] **M3: Relational Database & Idempotent Loader**: Normalized SQLite/PostgreSQL schema, upsert logic, and integrity tests.
- [x] **M4: SQL Analytics & Python EDA**: 9 portfolio analytical SQL queries with CTEs, window functions, and timing statistics.
- [x] **M5: Feature Engineering & Machine Learning**: Lap-to-stint mapping, tyre degradation baseline vs regressor with race-grouped CV.
- [x] **M6: Pit-Stop Strategy Simulator**: Multi-stop candidate generation, incremental pit loss, and safety-car scenario engine.
- [x] **M7: Streamlit Multipage Dashboard**: Interactive visualization for race pace, telemetry traces, tyre degradation, and strategy simulator.
- [x] **M8: Test Suite, Audit & Release**: 25/25 pytest passing, reproducible pipeline, and final documentation.
