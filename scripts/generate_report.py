import pandas as pd
from ydata_profiling import ProfileReport
from pathlib import Path
import argparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def generate_report(input_path: Path, output_path: Path, title: str = "Data Profile"):
    # Load data
    logging.info(f"Loading data from {input_path}")
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        logging.error(f"Failed to read CSV: {e}")
        return

    # Generate report
    logging.info("Generating profile report...")
    profile = ProfileReport(df, title=title, explorative=True)

    # Ensure output folder exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save report
    profile.to_file(output_path)
    logging.info(f"Report saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a profiling report from a CSV file.")
    parser.add_argument("--input", type=str, default="../data/processed/gym_processed_data.csv", help="Path to input CSV")
    parser.add_argument("--output", type=str, default="../reports/data_profile.html", help="Path to output HTML report")
    parser.add_argument("--title", type=str, default="GatorGauge Data Profile", help="Report title")

    args = parser.parse_args()
    generate_report(Path(args.input), Path(args.output), args.title)
