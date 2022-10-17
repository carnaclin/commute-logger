from dotenv import load_dotenv
import os, requests, time, datetime, csv
import urllib.parse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

SECONDS_DAY = 86400 # number of seconds in a day
SECONDS_MIN = 60    # number of seconds in a minute

load_dotenv() # take environment variables from .env.
api_key = os.getenv('API_KEY')

# Default distance maxtrix parameters
mode = "driving"
avoid = ''
traffic_model = ['optimistic', 'best_guess', 'pessimistic']

response = []   # list to store google api requests
data_main = []  # Stores averages for each day
data_std = []   # Stores all samples for all days for 'standard' model
data_opt = []   # Stores all samples for all days for 'optimistic' model
data_guess = [] # Stores all samples for all days for 'best_guess' model
data_pess = []  # Stores all samples for all days for 'pessimistic' model
time_stamp = []

# Builds request url and executes google maps request
def distance_matrix(origin, destination, api_key, mode, departure_time, traffic_model):
    base_url = "https://maps.googleapis.com/maps/api/distancematrix/json?" 
    params = {'origins': origin, 'destinations': destination, 'units': 'metric', \
        'key': api_key, 'mode': mode, 'departure_time': str(int(departure_time)), \
            'traffic_model': traffic_model, 'avoid': avoid}
    return requests.get(base_url + urllib.parse.urlencode(params))

# Populate reponse list with each traffic model request response
def get_response(origin, destination, api_key, mode, departure_time, traffic_model):
    for traffic_model in traffic_model:
        response.append(distance_matrix(origin, destination, api_key, mode, \
            departure_time, traffic_model))

# Takes request from google maps in json format and extract the data we want
def print_response(response, departure_datetime):
    origin = response[0].json()["origin_addresses"][0]
    destination = response[0].json()["destination_addresses"][0]
    travel_standard = response[0].json()["rows"][0]["elements"][0]["duration"]["value"]
    travel_optimistic = response[0].json()["rows"][0]["elements"][0]["duration_in_traffic"]["value"]
    travel_best_guess = response[1].json()["rows"][0]["elements"][0]["duration_in_traffic"]["value"] 
    travel_pessimistic = response[2].json()["rows"][0]["elements"][0]["duration_in_traffic"]["value"]

    print(f"- Origin: {origin}\n- Destination: {destination}")
    print(f"- Departure: {str(departure_datetime)}")
    print(f"- Travel Time Standard: {round(travel_standard/60,1)} min")
    print(f"- Travel Time Optmistic: {round(travel_optimistic/60,1)} min")
    print(f"- Travel Time Best guess: {round(travel_best_guess/60,1)} min")
    print(f"- Travel Time Pessimistic: {round(travel_pessimistic/60,1)} min")

# Take user input as dd mm yy and converts to epoch time
def convert_datetime(date_ui):
    date_ui = time.strptime(date_ui, "%d %m %y")
    return datetime.datetime(date_ui.tm_year, \
            date_ui.tm_mon, date_ui.tm_mday, date_ui.tm_hour, \
                date_ui.tm_min, date_ui.tm_sec).timestamp()

# Populates samples for 1 day. Lists are recycled after for each day
def collect_data(response, aux_std, aux_opt, aux_guess, aux_pess):
    aux_std.append(round(response[0].json()["rows"][0]["elements"][0]["duration"]["value"]/60,1))
    aux_opt.append(round(response[0].json()["rows"][0]["elements"][0]["duration_in_traffic"]["value"]/60,1))
    aux_guess.append(round(response[1].json()["rows"][0]["elements"][0]["duration_in_traffic"]["value"]/60,1))
    aux_pess.append(round(response[2].json()["rows"][0]["elements"][0]["duration_in_traffic"]["value"]/60,1))

# Display user options
print("Applications available:")
print("1. No user input (default settings)\n2. Single query\n3. Predictive query")
user_input = input("Select application (1-3): ")

# Case 1: Get a quick commute output for whatever you define as HOME and WORK
if user_input == '1':
    origin = os.getenv('HOME')
    destination = os.getenv('WORK')
    departure_time = time.time()
    departure_datetime = time.ctime(departure_time) # Datetime just for display
    get_response(origin, destination, api_key, mode, departure_time, traffic_model)
    print_response(response, departure_datetime)

# Case 2: Allows user input for addresses
elif user_input == '2':
    if input("Avoid tolls? (y/n): ") == 'y':
        avoid = "tolls"
    else:
        avoid = ''
    origin = input("Enter origin: ")
    destination = input("Enter destination: ")
    departure_ui = input("Enter departure time ('dd mm yy hh mm' or 'now'): ")
    if departure_ui == 'now':
        departure_epoch = time.time()
        departure_datetime = time.ctime(departure_epoch)
    else:
        d = time.strptime(departure_ui, "%d %m %y %H %M")
        departure_time = datetime.datetime(d.tm_year, d.tm_mon, d.tm_mday, \
            d.tm_hour, d.tm_min, d.tm_sec).timestamp()
        departure_datetime = time.ctime(departure_time)
    get_response(origin, destination, api_key, mode, departure_time, traffic_model)
    print_response(response, departure_datetime)

# Case 3: Allows user to input time period and frequency to get traffic trends
elif user_input == '3':
    if input("Avoid tolls? (y/n): ") == 'y':
        avoid = "tolls"
    else:
        avoid = ''
    origin = input("Enter origin: ")
    destination = input("Enter destination: ")
    start_time = convert_datetime(input("Enter start date ('dd mm yy'): "))
    sample_days = int(input("Enter number of days: "))
    sample_size = float(sample_days) * SECONDS_DAY
    samples_per_day = int(input("Enter samples per day: "))
    frequency = SECONDS_DAY / samples_per_day   # Time intervale between each request
    end_time = start_time + sample_size
    departure_time = start_time

     # Create list of responses for each day
    for i in range(sample_days):
        aux_std = []
        aux_opt = []
        aux_guess = []
        aux_pess = []
        for j in range(samples_per_day):
            response = []
            departure_datetime = time.ctime(departure_time)
            get_response(origin, destination, api_key, mode, departure_time, traffic_model)
            collect_data(response, aux_std, aux_opt, aux_guess, aux_pess)
            departure_time += frequency
            print(f"Progress: {round((departure_time - start_time) / sample_size * 100,1)}%", end="\r")
        data_std.append(aux_std)
        data_opt.append(aux_opt)
        data_guess.append(aux_guess)
        data_pess.append(aux_pess)

    # Create list for the time for each sample (used only for chart display)
    t = 0 # time in hours
    for i in range(samples_per_day):
        time_stamp.append(t)
        t += (frequency/3600)

    # Calculate averages for each traffic model for each day
    for sample in range(samples_per_day):
        avg_std = 0.0
        avg_opt = 0.0
        avg_guess = 0.0
        avg_pess = 0.0
        for day in range(sample_days):
            avg_std += data_std[day][sample]
            avg_opt += data_opt[day][sample]
            avg_guess += data_guess[day][sample]
            avg_pess += data_pess[day][sample]
        avg_std = round(avg_std / sample_days,1)   
        avg_opt = round(avg_opt / sample_days,1) 
        avg_guess = round(avg_guess / sample_days,1) 
        avg_pess = round(avg_pess / sample_days,1)  
        data_main.append([sample, time_stamp[sample], avg_std,\
            avg_opt, avg_guess, avg_pess])
    #print(data_main)

    # Write to csv file
    with open('samples.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['SAMPLE','TIME(HRS)','AVG_STANDARD',\
            'AVG_OPTIMISTIC','AVG_BEST_GUESS','AVG_PESSIMISTIC'])
        writer.writerows(data_main)

    # Display results
    data = pd.read_csv('samples.csv')
    df = pd.DataFrame(data)
    
    hour = list(df.iloc[:,1])
    std = list(df.iloc[:,2])
    opt = list(df.iloc[:,3])
    gue = list(df.iloc[:,4])
    pes = list(df.iloc[:,5])

    plt.figure(figsize=(8,6))

    plt.plot(hour, std, label="Standard",linestyle='dashed')
    plt.plot(hour, opt, label="Optimistic")
    plt.plot(hour, gue, label="Best Guess")
    plt.plot(hour, pes, label="Pessimistic")
    plt.xlabel("Hour of the day")
    plt.ylabel("Commute [min]")
    plt.title(f"From {origin} to {destination}\n[sample Days: {sample_days}] \
        [samples p/day: {samples_per_day}] [start date: {time.ctime(start_time)}]")
    plt.xticks(np.arange(0,24,1))
    plt.yticks(np.arange(20,60,5))
    plt.legend()
    plt.grid(linestyle = '--')
    plt.show()

else:
    print("Wrong input")
    exit()



