import json
import os
import csv
import sys
import requests

# Function to fetch JSON data from a URL
def fetch_json_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

# Function to write selected parameter to CSV
def write_json_to_csv(json_data, parameter, outpath):
    time_data = json_data["hourly"]["time"]
    param_data = json_data["hourly"].get(parameter, [])

    if not param_data:
        print(f"Parameter '{parameter}' not found in the JSON data.")
        return
    
    # Get the unit for the parameter (if available)
    param_unit = json_data["hourly_units"].get(parameter, "")

    # CSV file output path
    csv_file_path = os.path.join(outpath, f"{parameter}_data.csv")

    # Writing the JSON data to CSV
    with open(csv_file_path, mode='w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)

        # Writing the header
        csv_writer.writerow(["Time", f"{parameter} ({param_unit})"])

        # Writing the rows
        for time, value in zip(time_data, param_data):
            csv_writer.writerow([time, value])

    print(f"Data for '{parameter}' has been written to {csv_file_path}")

# Function to write all parameters to CSV
def write_all_parameters_to_csv(json_data, outpath, outfile, locationID):
    time_data = json_data["hourly"]["time"]
    
    # Prepare the CSV file path
    csv_file_path = os.path.join(outpath, outfile)

    # Gather all parameter names dynamically
    parameters = {key: json_data["hourly"][key] for key in json_data["hourly"] if key != "time"}

    # Extract location info (assumed to be in the main JSON structure)
    #latitude = json_data.get("latitude", "Unknown")
    #longitude = json_data.get("longitude", "Unknown")
    location = locationID

    # Writing the JSON data to CSV
    with open(csv_file_path, mode='w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)

        # Writing the header
        header = ["Time", "Location"] + list(parameters.keys())
        csv_writer.writerow(header)

        # Writing the rows
        for i in range(len(time_data)):
            row = [time_data[i], location] + [parameters[key][i] for key in parameters]
            csv_writer.writerow(row)

    print(f"Data for all parameters has been written to {csv_file_path}")


# Main function
def main():
    # URL of the API or file containing the JSON data
    #url = input("Enter the URL of the JSON data: ")
    url = sys.argv[1]
    outpath = sys.argv[2]
    outfile = sys.argv[4]+'_' + sys.argv[3]

    # Fetch JSON data from the provided URL
    json_data = fetch_json_data(url)

    if json_data:
        # List available parameters for user selection
        available_parameters = list(json_data["hourly"].keys())
        print("Available parameters:")
        for param in available_parameters:
            print(f"- {param}")

        # User selects a parameter to export
        #selected_param = input("\nPlease enter the parameter you'd like to export: ")
        locationID = sys.argv[4]

        # Call the function to write the selected parameter to CSV
    if json_data:
        # Write all parameters to CSV
        write_all_parameters_to_csv(json_data, outpath, outfile, locationID)

if __name__ == "__main__":
    main()

#"args": ["https://archive-api.open-meteo.com/v1/archive?latitude=51.0222&longitude=71.4669&start_date=2020-09-29&end_date=2024-10-13&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&models=era5_seamless", "d:/FEWS/FEWS_Accelerator/FEWS_Accelerator/Astana_SA/Modules/download_openMeteo/", "testLOC"]
# #"args:" ["https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&past_days=3&forecast_days=16","d:/FEWS/FEWS_Accelerator/FEWS_Accelerator/Astana_SA/Modules/download_openMeteo/", "testLOC"],

"""
            "args": ["https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&past_days=3&forecast_days=16",
                     "d:/FEWS/FEWS_Accelerator/FEWS_Accelerator/Astana_SA/Modules/download_openMeteo/", 
                     "forecast_openmeteo.csv"
                     "testLOC"]

            "args": ["https://archive-api.open-meteo.com/v1/archive?latitude=51.0222&longitude=71.4669&start_date=2020-09-29&end_date=2024-10-13&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m&models=era5_seamless",
                     "d:/FEWS/FEWS_Accelerator/FEWS_Accelerator/Astana_SA/Modules/download_openMeteo/", 
                     "historic_openmeteo.csv"
                     "testLOC"]

"""