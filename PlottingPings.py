import tkinter as tk
from tkinter import ttk
import subprocess
import platform
import threading
import time
from datetime import datetime
import queue
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import collections
from matplotlib.dates import DateFormatter
import numpy as np
from PIL import Image, ImageTk
import os  # Added for logo path handling

class PlottingPings:
    def __init__(self, root):
        self.root = root
        self.root.title("Plotting Pings")
        
        # Set window size and center it
        window_width = 800
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        # Default destinations in alphabetical order
        self.destinations = [
            "amazon.com",
            "bbc.co.uk",
            "cloudflare.com",
            "google.com",
            "microsoft.com"
        ]
        
        # Dictionary to store checkbox variables - all set to True by default
        self.service_vars = {dest: tk.BooleanVar(value=True) for dest in self.destinations}
        
        # Data storage
        self.ping_data = {dest: [] for dest in self.destinations}
        self.time_data = {dest: [] for dest in self.destinations}
        self.max_points = 50
        
        # Control variables
        self.ping_interval = tk.IntVar(value=5)
        self.running = False
        self.queue = queue.Queue()
        
        # Color scheme
        self.colors = {
            "amazon.com": {'main': '#9b59b6', 'alpha': 0.8},      # Purple
            "bbc.co.uk": {'main': '#f1c40f', 'alpha': 0.8},       # Yellow
            "cloudflare.com": {'main': '#3498db', 'alpha': 0.8},  # Blue
            "google.com": {'main': '#2ecc71', 'alpha': 0.8},      # Green
            "microsoft.com": {'main': '#e67e22', 'alpha': 0.8}    # Orange
        }
        
        # Failure colors (different shades of red)
        self.failure_colors = {
            "amazon.com": '#FF9999',      # Light red
            "bbc.co.uk": '#FF8080',       # Slightly darker red
            "cloudflare.com": '#FF6666',  # Medium red
            "google.com": '#FF4D4D',      # Darker red
            "microsoft.com": '#FF3333'     # Darkest red
        }
        
        self._create_gui()
        self._setup_plot()
        self._setup_legend_checkboxes()

    def _create_gui(self):
        # Main container
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky="nsew")
        
        # Title Label
        title_label = ttk.Label(main_container, text="Plotting Pings", 
                              font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, pady=10)
        
        # Control Frame
        control_frame = ttk.Frame(main_container, padding="5")
        control_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        # Interval frame
        interval_frame = ttk.Frame(control_frame, padding="5")
        interval_frame.pack(side=tk.LEFT, padx=20)
        
        # Interval setting with label
        ttk.Label(interval_frame, text="Ping Interval (seconds):", 
                 font=('Arial', 10)).pack(side=tk.LEFT)
        
        # Spinbox for interval
        interval_spinbox = ttk.Spinbox(interval_frame, 
                                     from_=1, 
                                     to=60,
                                     width=5,
                                     textvariable=self.ping_interval,
                                     wrap=True,
                                     increment=1)
        interval_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Start/Stop button
        self.start_button = ttk.Button(interval_frame, text="Start", 
                                     command=self.toggle_polling)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Plot frame
        self.plot_frame = ttk.Frame(main_container, padding="5")
        self.plot_frame.grid(row=2, column=0, sticky="nsew")
        
        # Right side container for logo and legend
        right_container = ttk.Frame(self.plot_frame, padding="5")
        right_container.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Logo frame
        logo_frame = ttk.Frame(right_container, padding="5")
        logo_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Load and display logo
        try:
            # Get the directory where the script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, "CandJ_Logo.jpg")
            logo_image = Image.open(logo_path)
            # Resize logo (adjust size as needed)
            logo_image = logo_image.resize((80, 80), Image.Resampling.LANCZOS)
            self.logo_photo = ImageTk.PhotoImage(logo_image)
            logo_label = ttk.Label(logo_frame, image=self.logo_photo)
            logo_label.pack(pady=(0, 10))
        except Exception as e:
            print(f"Error loading logo: {e}")
        
        # Legend frame
        self.legend_frame = ttk.Frame(right_container, padding="5")
        self.legend_frame.pack(side=tk.TOP, fill=tk.Y)
        
        # Configure grid weights
        main_container.grid_rowconfigure(2, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

    def _setup_plot(self):
        self.fig = Figure(figsize=(10, 6), facecolor='#f8f9fa')
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Set up the plot
        self.ax.set_title("Network Latency Monitor", fontsize=14, pad=15)
        self.ax.set_xlabel("Time", fontsize=10)
        self.ax.set_ylabel("Ping (ms)", fontsize=10)
        self.ax.grid(True, alpha=0.3, linestyle='--')
        self.ax.set_facecolor('#ffffff')
        
        # Initialize filled areas only (no lines)
        self.fills = {}
        
        # Initialize with default ranges
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 100)
        
        # Create empty fills for each destination
        for dest in self.destinations:
            color = self.colors[dest]['main']
            fill = self.ax.fill_between([], [], alpha=self.colors[dest]['alpha'], 
                                      color=color, label=dest)
            self.fills[dest] = fill

    def _setup_legend_checkboxes(self):
        # Create legend title
        title = ttk.Label(self.legend_frame, text="Services", font=('Arial', 10, 'bold'))
        title.pack(pady=(0, 5))
        
        # Create frame for each legend item
        for dest in self.destinations:
            frame = ttk.Frame(self.legend_frame)
            frame.pack(fill=tk.X, padx=5, pady=2)
            
            # Color box
            color_box = tk.Canvas(frame, width=15, height=15, bg=self.colors[dest]['main'])
            color_box.pack(side=tk.LEFT, padx=(0, 5))
            
            # Checkbox
            cb = ttk.Checkbutton(frame, 
                               text=dest,
                               variable=self.service_vars[dest],
                               command=self.handle_service_toggle)
            cb.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def handle_service_toggle(self):
        """Handle checkbox toggle events"""
        # Clear data for deselected services
        for dest in self.destinations:
            if not self.service_vars[dest].get():
                self.ping_data[dest] = []
                self.time_data[dest] = []
        
        # Trigger plot update
        if self.running:
            self.update_plot()

    def get_active_destinations(self):
        """Returns list of currently selected destinations"""
        return [dest for dest in self.destinations if self.service_vars[dest].get()]

    def ping(self, host):
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, '1', host]
        try:
            # Create startupinfo object to hide console window
            startupinfo = None
            if platform.system().lower() == 'windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            # Run ping command with hidden window
            output = subprocess.check_output(
                command,
                startupinfo=startupinfo,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )

            if platform.system().lower() == 'windows':
                if 'Reply from' in output:
                    ms = int(output.split('time=')[-1].split('ms')[0].strip())
                    return ms
            else:
                if 'time=' in output:
                    ms = float(output.split('time=')[-1].split('ms')[0].strip())
                    return ms
        except:
            return None
        return None

    def poll_destinations(self):
        while self.running:
            current_time = datetime.now()
            active_destinations = self.get_active_destinations()
            for dest in active_destinations:
                ping_time = self.ping(dest)
                if ping_time is not None:
                    self.queue.put((dest, current_time, ping_time))
                else:
                    # Explicitly queue failed pings
                    self.queue.put((dest, current_time, None))
            time.sleep(self.ping_interval.get())

    def toggle_polling(self):
        if not self.running:
            # Check if at least one service is selected
            if not self.get_active_destinations():
                print("Please select at least one service to monitor")
                return
                
            self.running = True
            self.start_button.config(text="Stop")
            self.polling_thread = threading.Thread(target=self.poll_destinations)
            self.polling_thread.daemon = True
            self.polling_thread.start()
            self.update_plot()
        else:
            self.running = False
            self.start_button.config(text="Start")    

    def update_plot(self):
        try:
            while not self.queue.empty():
                dest, timestamp, ping_time = self.queue.get()
                
                # Only update if service is still selected
                if self.service_vars[dest].get():
                    self.time_data[dest].append(timestamp)
                    # Store None for failed pings
                    self.ping_data[dest].append(ping_time)
                    
                    # Trim data to max_points
                    if len(self.time_data[dest]) > self.max_points:
                        self.time_data[dest] = self.time_data[dest][-self.max_points:]
                        self.ping_data[dest] = self.ping_data[dest][-self.max_points:]
            
            # Get active destinations and their current ping times
            active_destinations = self.get_active_destinations()
            
            if active_destinations:
                # Find common time points across all active destinations
                all_times = set()
                for dest in active_destinations:
                    if self.time_data[dest]:
                        all_times.update(self.time_data[dest])
                all_times = sorted(list(all_times))

                if all_times:
                    # Create arrays for plotting with consistent time points
                    plot_data = {}
                    failure_masks = {}
                    for dest in active_destinations:
                        plot_data[dest] = []
                        failure_masks[dest] = []
                        for t in all_times:
                            if t in self.time_data[dest]:
                                idx = self.time_data[dest].index(t)
                                value = self.ping_data[dest][idx]
                                if value is None:
                                    plot_data[dest].append(100)  # Default height for failed pings
                                    failure_masks[dest].append(True)
                                else:
                                    plot_data[dest].append(value)
                                    failure_masks[dest].append(False)
                            else:
                                if self.ping_data[dest]:
                                    last_value = self.ping_data[dest][-1]
                                    plot_data[dest].append(100 if last_value is None else last_value)
                                    failure_masks[dest].append(last_value is None)
                                else:
                                    plot_data[dest].append(0)
                                    failure_masks[dest].append(False)

                    # Convert times to strings for plotting
                    time_strings = [t.strftime('%H:%M:%S') for t in all_times]

                    # Sort destinations by current ping time (fastest first)
                    current_pings = {dest: plot_data[dest][-1] for dest in active_destinations if plot_data[dest]}
                    sorted_destinations = sorted(current_pings.keys(), key=lambda x: current_pings[x])

                    # Clear all fills
                    for dest in self.destinations:
                        if hasattr(self.fills[dest], 'remove'):
                            self.fills[dest].remove()
                        self.fills[dest] = self.ax.fill_between([], [], alpha=0.4)

                    # Plot stacked areas
                    base = np.zeros(len(all_times))
                    for dest in sorted_destinations:
                        values = np.array(plot_data[dest])
                        failure_mask = np.array(failure_masks[dest])
                        
                        # Update fill for successful pings
                        if hasattr(self.fills[dest], 'remove'):
                            self.fills[dest].remove()
                        
                        # Create fill for successful pings
                        self.fills[dest] = self.ax.fill_between(time_strings, 
                                                              base, 
                                                              base + values,
                                                              where=~failure_mask,
                                                              alpha=self.colors[dest]['alpha'],
                                                              color=self.colors[dest]['main'],
                                                              label=dest)
                        
                        # Create fill for failed pings
                        if np.any(failure_mask):
                            self.ax.fill_between(time_strings, 
                                               base, 
                                               base + values,
                                               where=failure_mask,
                                               alpha=0.6,
                                               color=self.failure_colors[dest])
                        
                        base += values

                    # Update axis and tick handling
                    if len(set(time_strings)) > 1:
                        self.ax.set_xlim(time_strings[0], time_strings[-1])
                        
                        # Calculate number of ticks based on figure width
                        fig_width = self.fig.get_figwidth()
                        min_spacing_inches = 0.393701  # 1 cm = 0.393701 inches
                        max_ticks = int(fig_width / min_spacing_inches)
                        
                        # Select evenly spaced tick positions
                        n_times = len(time_strings)
                        if n_times > max_ticks:
                            tick_indices = np.linspace(0, n_times-1, max_ticks, dtype=int)
                            self.ax.set_xticks([time_strings[i] for i in tick_indices])
                        else:
                            self.ax.set_xticks(time_strings)
                    
                    self.ax.set_ylim(0, max(max(base) * 1.2, 100))
                    
                    # Rotate x-axis labels
                    plt.setp(self.ax.get_xticklabels(), rotation=45, ha='right')
                    
                    self.fig.tight_layout()
                    self.canvas.draw()
            
        except Exception as e:
            print(f"Error updating plot: {e}")
            
        if self.running:
            self.root.after(1000, self.update_plot)


if __name__ == "__main__":
    root = tk.Tk()
    app = PlottingPings(root)
    root.mainloop()