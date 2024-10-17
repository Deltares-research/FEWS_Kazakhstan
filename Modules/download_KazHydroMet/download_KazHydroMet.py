import logging
from datetime import datetime, timedelta
import json
import csv
import os
import sys

# Setup logging configuration
log_file = sys.argv[5]
logging.basicConfig(
    filename=log_file,  # Log file name
    level=logging.INFO,     # Log level
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Example JSON data (as a list of dictionaries)
json_data = [
    {
        "post_id": 11002,
        "date": "2024-01-01",
        "Q_08": "null",
        "Q_mean": "null",
        "Q": "null",
        "level_mean": 265.0,
        "level_20": 265.0,
        "level_08": 265.0,
        "water_code_status_1": 600,
        "water_code_status_2": "null"
    },
    {
        "post_id": 11025,
        "date": "2024-01-01",
        "Q_08": "null",
        "Q_mean": "null",
        "Q": "null",
        "level_mean": 109.0,
        "level_20": 109.0,
        "level_08": 109.0,
        "water_code_status_1": 51301,
        "water_code_status_2": 51901.0
    }
]

def round_to_nearest_3_hours(dt):
    # Calculate how many hours to add or subtract to get to the nearest 3-hour mark
    hours_to_nearest_3 = round(dt.hour / 3) * 3
    rounded_dt = dt.replace(hour=hours_to_nearest_3 % 24, minute=0, second=0, microsecond=0)

    # Adjust the day if the rounding pushed us to the next or previous day
    if hours_to_nearest_3 >= 24:
        rounded_dt += timedelta(days=1)
    elif hours_to_nearest_3 < 0:
        rounded_dt -= timedelta(days=1)

    return rounded_dt

# Function to convert JSON to CSV
def json_to_csv(json_data, csv_file_path):
    try:
        # Extract keys from the first dictionary as the CSV header
        keys = json_data[0].keys()
        
        # Write to CSV file
        with open(csv_file_path, 'w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=keys)
            
            # Write header
            writer.writeheader()
            
            # Write data rows
            writer.writerows(json_data)
        
        logging.info(f"Data successfully written to {csv_file_path}")
    except Exception as e:
        logging.error(f"Failed to write data to {csv_file_path}: {str(e)}")

def create_url(base_url, startdate):
    """
    Create a URL based on the base_url and start date.
    """
    try:
        if "meteo_3h" in base_url:
            startdate_round = round_to_nearest_3_hours(startdate)
            startdate_formatted = startdate_round.strftime("%Y%m%d")
            starthour_formatted = startdate_round.strftime("%H")
            url = f"{base_url}?sdate={startdate_formatted}&shour={starthour_formatted}"
        elif "hydro1d" in base_url or "wrf_48h" in base_url:
            startdate_formatted = startdate.strftime("%Y%m%d")
            url = f"{base_url}?sdate={startdate_formatted}"
        else:
            url = base_url
        
        logging.info(f"URL created: {url}")
        return url
    except Exception as e:
        logging.error(f"Error creating URL: {str(e)}")
        raise

def main():
    try:
        # Argument parsing
        base_url = sys.argv[1]
        outpath = sys.argv[2]
        outfile = sys.argv[3]
        startdate = sys.argv[4]
        

        logging.info("Script started with arguments: %s", sys.argv)

        if base_url == "-":
            url = json_data  # Use the provided JSON data instead of a URL
            date_file = startdate
        else:
            date_format = "%Y%m%d%H%M%S"
            datetime_start = datetime.strptime(startdate, date_format)
            url = create_url(base_url, datetime_start)
            date_file = startdate
        
        # Specify CSV output file path
        csv_file_path = os.path.join(outpath, f"{date_file}_{outfile}")
        
        # Call the function to convert and save JSON data to a CSV file
        json_to_csv(url, csv_file_path)

        logging.info(f"Process completed successfully. Data saved to {csv_file_path}")
        print(f"Data successfully written to {csv_file_path}")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
