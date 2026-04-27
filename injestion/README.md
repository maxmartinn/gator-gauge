# Ingestion

This folder contains the UF gym count ingestion job.

## One-Shot Run

From the project root:

```bash
pip install -r injestion/requirements.txt
make ingest-once
```

The command:

1. Fetches current counts from the UF GoBoard API.
2. Formats rows with UTC timestamps and occupancy percentages.
3. Writes one timestamped local CSV to `data/raw/`.
4. Uploads one CSV per location to S3.
5. Exits.

S3 objects are written to:

```text
s3://gator-gains-data/bronze/gym_counts/location_name={location}/year={YYYY}/month={MM}/day={DD}/gym_data_{timestamp}.csv
```

## Options

Run without uploading to S3:

```bash
python3 injestion/gym_scraper.py --no-s3
```

Run without saving a local CSV:

```bash
python3 injestion/gym_scraper.py --no-local
```

Run continuously every 10 minutes for local development:

```bash
python3 injestion/gym_scraper.py --loop --interval 600
```

For production, prefer scheduling the one-shot command every 10 minutes instead of using `--loop`.

## Docker

From the project root:

```bash
docker compose up --build
```

The compose file runs one ingestion batch, mounts `./data/raw` for local snapshots, and mounts `~/.aws` read-only so `boto3` can use your local AWS profile.

## Configuration

Environment variables:

- `AWS_PROFILE`: AWS profile used by `boto3` locally. The Makefile defaults this to `gator-gauge`.
- `GATOR_GAUGE_S3_BUCKET`: defaults to `gator-gains-data`.
- `GATOR_GAUGE_S3_PREFIX`: defaults to `bronze/gym_counts`.
- `GATOR_GAUGE_LOCAL_DIR`: defaults to `data/raw`.
- `GATOR_GAUGE_ACCOUNT_API_KEY`: GoBoard account API key used to build the count URL.
- `GATOR_GAUGE_API_URL`: full GoBoard API URL. Use this instead of `GATOR_GAUGE_ACCOUNT_API_KEY` only when you need to override the entire endpoint.
