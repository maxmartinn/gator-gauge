# Gator Gains

## Overview
Gator Gains is a project designed to predict the number of people at specific gym locations based on historical data. The dataset includes information such as timestamps, facility names, location names, current counts, total capacity, and more. The goal is to build a predictive model that estimates the number of people at a given location based on the time and day of the week.

## Project Structure

```
├── api/                # API for serving predictions
├── dashboard/          # Dashboard for visualizing data and predictions
├── data/
│   ├── processed/      # Processed data for modeling
│   └── raw/            # Raw data (e.g., gym_capacity_log.csv)
├── ingestion/
│   └── gym_scraper.py  # Script for scraping gym data
├── model/              # Model training and storage
├── notebooks/          # Jupyter notebooks for exploratory data analysis
├── requirements.txt    # Python dependencies
├── docker-compose.yml  # Docker setup for the project
└── README.md           # Project documentation
```

## Dataset
The dataset contains the following columns:
- `pulled_at_utc`: Timestamp when the data was pulled.
- `facility_name`: Name of the facility.
- `location_name`: Specific location within the facility.
- `last_count`: Current count of people at the location.
- `total_capacity`: Maximum capacity of the location.
- `percent_full`: Percentage of the location's capacity that is currently occupied.
- `last_updated_source_time`: Last time the source updated the data.
- `is_closed`: Boolean indicating if the location is closed.

## Goals
1. Preprocess the data to extract useful features such as day of the week and hour of the day.
2. Build a predictive model to estimate the number of people at a location.
3. Deploy the model via an API for real-time predictions.
4. Create a dashboard to visualize historical data and predictions.

## Getting Started

### Prerequisites
- Python 3.8+
- Docker (optional for containerized setup)

### Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd gator_gains
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Project
1. **Data Ingestion**:
   - Use `gym_scraper.py` to scrape or update the dataset.
2. **Model Training**:
   - Train the predictive model using scripts in the `model/` directory.
3. **API**:
   - Start the API server to serve predictions.
4. **Dashboard**:
   - Launch the dashboard to visualize data and predictions.

### Docker Setup
To run the project using Docker:
1. Build and start the containers:
   ```bash
   docker-compose up --build
   ```
2. Access the API and dashboard via the provided URLs.

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

## License
This project is licensed under the MIT License.