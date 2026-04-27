# Gator Gauge Dashboard

A Streamlit dashboard for visualizing UF gym occupancy trends and patterns.

## Quick Start

### Prerequisites
- AWS CLI configured with `gator-gauge` profile and S3 read access
- Python 3.8+
- Dependencies: `pip install -r requirements.txt`

### Running Locally

1. **Test AWS access:**
   ```bash
   AWS_PROFILE=gator-gauge python3 test_aws_access.py
   ```
   Should output: "✅ All checks passed! You're ready to run the dashboard."

2. **Run the dashboard:**
   ```bash
   AWS_PROFILE=gator-gauge streamlit run app.py
   ```
   Or use the Makefile from the project root:
   ```bash
   make dashboard
   ```

3. **Open in browser:**
   Navigate to `http://localhost:8501`

## Deploying to Streamlit Community Cloud

Streamlit Community Cloud is the cheapest working deployment option for this app.
GitHub Pages cannot run this dashboard because it is a live Python/Streamlit app.

1. Push the repo to GitHub.
2. In Streamlit Community Cloud, create a new app from the GitHub repo.
3. Use this app entry point:
   ```text
   dashboard/app.py
   ```
4. Keep `requirements.txt` at the repo root. It points to `dashboard/requirements.txt`.
5. Add AWS credentials in Streamlit app secrets:
   ```toml
   [aws]
   region_name = "us-east-1"
   aws_access_key_id = "YOUR_READ_ONLY_ACCESS_KEY_ID"
   aws_secret_access_key = "YOUR_READ_ONLY_SECRET_ACCESS_KEY"
   ```

Use an IAM user or access key with read-only access to the dashboard bucket. A minimal policy looks like:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::gator-gains-data"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::gator-gains-data/*"
    }
  ]
}
```

Do not commit `.streamlit/secrets.toml` or `dashboard/.streamlit/secrets.toml`.
Use `.streamlit/secrets.toml.example` for root-level Streamlit runs and
`dashboard/.streamlit/secrets.toml.example` when running from inside `dashboard/`.

## Features

- **Occupancy Trends**: Line chart showing % full over time for selected locations
- **Heatmap**: Hour × Day-of-Week view showing when gyms are busiest
- **Facility Comparison**: Bar chart comparing average occupancy across facilities
- **Peak Hours Table**: Top 10 busiest hour-location combinations
- **Key Metrics**: Average occupancy, peak occupancy, number of locations, data points
- **Classes**: UF RecSports class schedule with per-class calendar downloads
- **Cameras & Counts**: RecSports camera feeds paired with latest S3 count data

## File Structure

```
dashboard/
├── app.py                      # Main Streamlit app
├── data_access.py              # S3 data retrieval + caching
├── transforms.py               # Data preprocessing + feature engineering
├── charts.py                   # Plotly chart builders
├── test_aws_access.py          # AWS connectivity test
├── requirements.txt            # Python dependencies
├── .streamlit/config.toml      # Streamlit configuration
└── README.md                   # This file
```

## Configuration

- **AWS Profile**: Set `AWS_PROFILE=gator-gauge` environment variable before running
- **Streamlit Cloud**: Add `[aws]` credentials through app secrets
- **Cache TTL**: Data is cached for 10 minutes (see `data_access.py`)
- **Theme**: Configured in `.streamlit/config.toml`

## Troubleshooting

### "Unable to read S3 object"
- Verify AWS credentials: `aws s3 ls s3://gator-gains-data/ --profile gator-gauge`
- Check IAM user has `S3ReadOnlyAccess` or equivalent permissions

### "No data available"
- Default date range starts at the first actual SWRC Fitness Total data day
- S3 data currently spans 2025-05-10 to 2026-04-27 for SWRC Fitness Total
- Adjust date range in sidebar filters

### Port 8501 already in use
- Kill existing Streamlit process: `pkill streamlit`
- Or use different port: `streamlit run app.py --server.port 8502`

## Development

### Adding new charts
1. Add function to `charts.py` (uses `plotly`)
2. Call function from `app.py` and display with `st.plotly_chart()`

### Adding new data transforms
1. Add function to `transforms.py`
2. Call from `app.py` after loading + preprocessing

### Updating dependencies
```bash
pip install -r requirements.txt --upgrade
```

## Future Enhancements

- Real-time data refresh with WebSocket
- Predictions from trained model (when available)
- Current occupancy tiles (live snapshot)
- Multi-facility comparison with filters
- Export data as CSV/PDF reports
- Public hosting (Streamlit Cloud / AWS Amplify)
