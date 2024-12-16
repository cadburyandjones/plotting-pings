import asyncio
import aiohttp
import time
import csv
import os
import matplotlib.pyplot as plt
import toml  # for configuration files

# --- Configuration Management ---

def load_config(config_file="config.toml"):
    try:
        with open(config_file, "r") as f:
            config = toml.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_file}' not found. Using default values.")
        return {
            "urls": ["https://www.google.com", "https://www.bbc.co.uk", "https://www.yahoo.com"],
            "ping_interval": 60,
            "plot_window": 20,
            "csv_filename": "ping_data.csv"
        }

# --- Asynchronous Pinging ---

async def fetch_latency(session, url):
    start_time = time.time()
    try:
        async with session.get(url) as response:
            if response.status == 200: # or check for other successful codes as needed
                end_time = time.time()
                latency = end_time - start_time
                return url, latency # return both the url and latency for later use
            else:
                return url, None # return None if ping failed
    except aiohttp.ClientError: # catch errors
        return url, None

async def main(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_latency(session, url) for url in urls]
        latencies = await asyncio.gather(*tasks) # run all the ping calls simultaneously
        return latencies

# --- CSV Export ---

def save_to_csv(data, filename):
    file_exists = os.path.exists(filename)
    with open(filename, mode="a", newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Timestamp", "Website", "Latency"])
        writer.writerow(data)

# --- Plotting ---

def update_plot(time_data, latency_data, plot_window, ax, line, plt, config):
    # Ensure data lists are not longer than the plot window
    time_data = time_data[-plot_window:]
    latency_data = latency_data[-plot_window:]

    # Update the plot
    line.set_data(time_data, latency_data)
    ax.relim()  # recalculate the limits
    ax.autoscale_view()  # adjust the view to fit the new data
    ax.set_title(f'Ping Latency over time for: {config["urls"]}')
    ax.set_xlabel('Time')
    ax.set_ylabel('Latency (s)')
    plt.pause(0.01)  # pause to allow the GUI to update

# --- Main Loop ---

async def run_monitor():

    config = load_config() # load the config from the toml file

    urls = config["urls"] # use the list of urls from the config file
    ping_interval = config["ping_interval"] # use the ping interval from the config file
    plot_window = config["plot_window"]  # how many readings to show at any given time
    csv_filename = config["csv_filename"] # name of the csv file

    # Data storage
    time_data = []
    latency_data = []

    # Setup Plot
    fig, ax = plt.subplots()
    line, = ax.plot([], [])
    plt.ion()
    plt.show()

    while True:
        latencies = await asyncio.run(main(urls))
        current_time = time.time()

        for url, latency in latencies:
          if latency is not None:
            print(f"Latency for {url}: {latency*1000:.2f} ms")
            timestamp = time.time()
            csv_data = [timestamp, url, latency]
            save_to_csv(csv_data, csv_filename)

            time_data.append(current_time)
            latency_data.append(latency)

          else:
            print(f"Error pinging {url}")

        update_plot(time_data, latency_data, plot_window, ax, line, plt, config)

        await asyncio.sleep(ping_interval)


if __name__ == "__main__":
    asyncio.run(run_monitor())
