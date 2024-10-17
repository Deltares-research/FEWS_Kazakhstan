import json
import os
import csv
import sys
import requests
import pandas as pd
import logging
from datetime import datetime, timedelta

# Set up logging to write to a file
logging.basicConfig(
    filename='download_openmeteo.log',          # Log file path
    level=logging.INFO,          # Set logging level (INFO captures normal operations)
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    datefmt='%Y-%m-%d %H:%M:%S'  # Date format in log entries
)

# Function to fetch JSON data from a URL
def fetch_json_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
        logging.info(f"Successfully fetched data from URL: {url}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from {url}: {e}")
        return None

# Function to write selected parameter to CSV
def write_json_to_csv(json_data, parameter, outpath):
    time_data = json_data["hourly"]["time"]
    param_data = json_data["hourly"].get(parameter, [])

    if not param_data:
        logging.warning(f"Parameter '{parameter}' not found in the JSON data.")
        return
    
    # Get the unit for the parameter (if available)
    param_unit = json_data["hourly_units"].get(parameter, "")

    # CSV file output path
    csv_file_path = os.path.join(outpath, f"{parameter}_data.csv")

    # Writing the JSON data to CSV
    try:
        with open(csv_file_path, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)

            # Writing the header
            csv_writer.writerow(["Time", f"{parameter} ({param_unit})"])

            # Writing the rows
            for time, value in zip(time_data, param_data):
                csv_writer.writerow([time, value])

        logging.info(f"Data for '{parameter}' written to {csv_file_path}")
    except Exception as e:
        logging.error(f"Error writing data for '{parameter}' to CSV: {e}")

# Function to write all parameters to CSV
def write_all_parameters_to_csv(json_data, outpath, outfile, locationID):
    time_data = json_data["hourly"]["time"]
    
    # Prepare the CSV file path
    csv_file_path = os.path.join(outpath, outfile)

    # Gather all parameter names dynamically
    parameters = {key: json_data["hourly"][key] for key in json_data["hourly"] if key != "time"}

    # Extract location info (assumed to be in the main JSON structure)
    location = locationID

    # Writing the JSON data to CSV
    try:
        with open(csv_file_path, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)

            # Writing the header
            header = ["Time", "Location"] + list(parameters.keys())
            csv_writer.writerow(header)

            # Writing the rows
            for i in range(len(time_data)):
                time_formatted = time_data[i].replace("T", " ")
                row = [time_formatted, location] + [parameters[key][i] for key in parameters]
                csv_writer.writerow(row)

        logging.info(f"Data for all parameters written to {csv_file_path}")
    except Exception as e:
        logging.error(f"Error writing all parameters to CSV: {e}")


# Main function
def main():
    ini_file = sys.argv[1]
    outpath = sys.argv[2]
    enddate = sys.argv[3]
    date_object = datetime.strptime(enddate, "%Y-%m-%d")
    startdate = date_object - timedelta(days=35)
    startdate = startdate.strftime("%Y-%m-%d")
    ini = pd.read_csv(ini_file)

    for index, row in ini.iterrows():
        if sys.argv[4] == "historic":
            url = (f"https://archive-api.open-meteo.com/v1/archive?latitude={row.Lat}&longitude={row.Lon}"
                   f"&start_date={startdate}&end_date={enddate}&hourly={row.parameters}&models=era5_seamless")
            outfilename = f"{row.Location}_historic_openmeteo.csv"
            outfile = os.path.join(outpath, outfilename)
            locationID = row.Location

            # Fetch JSON data from the provided URL
            json_data = fetch_json_data(url)
            
            # Call the function to write the selected parameter to CSV
            if json_data:
                write_all_parameters_to_csv(json_data, outpath, outfile, locationID)

        elif sys.argv[4] == "forecast":
            url = (f"https://api.open-meteo.com/v1/forecast?latitude={row.Lat}&longitude={row.Lon}"
                   f"&hourly={row.parameters}&past_days=7&forecast_days=16")
            outfilename = f"{row.Location}_forecast_openmeteo.csv"
            outfile = os.path.join(outpath, outfilename)
            locationID = row.Location

            # Fetch JSON data from the provided URL
            json_data = fetch_json_data(url)

            # Call the function to write the selected parameter to CSV
            if json_data:
                write_all_parameters_to_csv(json_data, outpath, outfile, locationID)


if __name__ == "__main__":
    main()
