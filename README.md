# Gator Gauge

Gator Gauge tracks and visualizes University of Florida gym occupancy data. The project currently has three working lanes:

- `injestion/`: scraper container for collecting gym count data and writing to S3.
- `dashboard/`: Streamlit dashboard for historical analysis and occupancy predictions.
- `scripts/`: early local data-prep, report, and model-training scripts.

The `.claude` worktree handoff included a Streamlit dashboard implementation. That work has been brought into the main workspace and tightened so the dashboard can be run from the root Makefile.

## Current Status

Working now:

- One-shot ingestion from the UF gym API to local CSV snapshots and S3.
- Historical dashboard reading from `s3://gator-gains-data/bronze/gym_counts/`.
- Ridge regression prediction model in `dashboard/model.py`.
- Prediction tab for a selected location, date, and hour.
- Best-time and avoid-time recommendations for a selected day.
- Date and location filters.
- Occupancy trend line chart.
- Hour-by-day heatmap.
- Average occupancy by facility chart.
- Peak hour/location table.
- AWS access smoke test.

Still incomplete:

- No prediction API exists yet.
- No deployment configuration for the dashboard exists yet.
- Local preprocessing scripts still expect local CSV files under `data/`, while the dashboard reads from S3.

## Repository Layout

```text
.
|-- dashboard/
|   |-- app.py
|   |-- charts.py
|   |-- data_access.py
|   |-- model.py
|   |-- transforms.py
|   |-- test_aws_access.py
|   `-- requirements.txt
|-- injestion/
|   |-- Dockerfile
|   |-- gym_scraper.py
|   `-- requirements.txt
|-- scripts/
|   |-- basic_preprocess.py
|   |-- generate_report.py
|   |-- train_model.py
|   `-- requirements.txt
|-- docker-compose.yml
|-- Makefile
`-- README.md
```

Note: the folder is currently named `injestion`. Keep that spelling unless you are ready to update all references together.

## Setup

Use Python 3.9+.

For the dashboard:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r dashboard/requirements.txt
```

Configure AWS credentials with read access to the `gator-gains-data` bucket. The Makefile defaults to the `gator-gauge` profile:

```bash
aws configure --profile gator-gauge
```

Or export a different profile before running commands:

```bash
export AWS_PROFILE=my-profile
```

## Ingest One Batch

From the repo root:

```bash
pip install -r injestion/requirements.txt
make ingest-once
```

`make ingest-once` fetches the current UF gym counts once, writes a timestamped local CSV under `data/raw/`, uploads location-partitioned CSVs to S3, and exits.

Useful direct variants:

```bash
python3 injestion/gym_scraper.py --no-s3
python3 injestion/gym_scraper.py --no-local
python3 injestion/gym_scraper.py --loop --interval 600
```

Docker Compose runs the same one-shot job and mounts your local AWS config read-only:

```bash
docker compose up --build
```

The one-shot command is the recommended production shape. Schedule it every 10 minutes with cron, GitHub Actions, EventBridge, or ECS instead of keeping a local process running forever.

## Run The Dashboard

From the repo root:

```bash
make test-dashboard
make dashboard
```

Then open `http://localhost:8501`.

The dashboard discovers the available S3 date range, then defaults to the most recent 7 days in that range.

The prediction tab trains a Ridge regression model from the S3 data. It uses cyclical hour, day-of-week, and month features, a weekend flag, and one-hot location encoding. The model also filters out closed facilities, impossible occupancy percentages, off-hours rows, and per-location statistical outliers before training.

## Data Contract

The dashboard expects CSV objects in S3 under:

```text
s3://gator-gains-data/bronze/gym_counts/location_name={location}/year={YYYY}/month={MM}/day={DD}/
```

Expected columns:

- `pulled_at_utc`
- `facility_name`
- `location_name`
- `last_count`
- `total_capacity`
- `percent_full`
- `last_updated_source_time`
- `is_closed`

## Where To Go From Here

1. Verify the S3 data window.
   Run `make test-dashboard`, then confirm whether current data exists beyond `2025-05-15`. If it does, update the dashboard default dates or make the app discover the latest available partition automatically.

2. Make ingestion repeatable.
   Schedule `make ingest-once` every 10 minutes with cron, GitHub Actions, EventBridge, or ECS. Keep AWS credentials out of source control; use an AWS profile locally and an IAM role in AWS.

3. Unify local scripts with S3.
   `scripts/basic_preprocess.py` expects `../data/raw/gym_raw_data.csv`, but the dashboard reads S3. Decide whether local modeling should pull from S3 directly or use an exported local snapshot.

4. Improve model accuracy.
   Add features that explain real demand swings: academic calendar, football/basketball game days, holidays, weather, exams, and recent lagged occupancy.

5. Persist a trained model artifact.
   The dashboard currently trains in-process from S3. For deployment, train on a schedule and save a versioned artifact to S3 so app startup is faster and reproducible.

6. Add tests around transforms.
   Start with `dashboard/transforms.py` and `dashboard/model.py`: timestamp parsing, Eastern time conversion, model filters, feature generation, and prediction bounds.

7. Plan deployment.
   For private usage, Streamlit Community Cloud with secrets or an internal AWS deployment is enough. For public usage, add scoped IAM credentials, request caching, and a cost-aware data access layer before publishing.

## Useful Commands

```bash
make ingest-once    # Fetch current counts and upload them to S3
make dashboard       # Run Streamlit dashboard
make test-dashboard  # Verify AWS/S3 access
make preprocess      # Run local preprocessing script
make report          # Generate local profiling report
make all             # preprocess, train, report
```

## Notes

- The dashboard uses Streamlit caching with a 10-minute TTL in `dashboard/data_access.py`.
- Streamlit reads credentials through `boto3`, so normal AWS CLI environment variables and profile configuration apply.
- `data/` and `reports/` are gitignored because they are generated or local artifacts.
