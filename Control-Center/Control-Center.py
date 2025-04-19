import tkinter as tk
from tkinter import ttk, Toplevel
import requests
import json

#plot
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ESP32_AP_IP = "192.168.4.1"
ctrl_endpoint = f"http://{ESP32_AP_IP}/ctrl"
data_endpoint = f"http://{ESP32_AP_IP}/data"
piddata_endpoint = f"http://{ESP32_AP_IP}/piddata"

def center_window(window):
    window.update_idletasks()
    window_width = window.winfo_width()
    window_height = window.winfo_height()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    window.geometry(f"+{x}+{y}")

class FloatControlCenter:
    def __init__(self, root):
        self.field_vars = {}
        self.root = root
        self.root.title("Float Control Center")
        self.root.geometry("800x600")
        
        # Create notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(padx=10, pady=10, expand=True, fill="both")
        
        # Create tabs
        self.config_tab = ttk.Frame(self.notebook)
        self.profiling_tab = ttk.Frame(self.notebook)
        self.manual_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.config_tab, text="Config")
        self.notebook.add(self.profiling_tab, text="Profiling")
        self.notebook.add(self.manual_tab, text="Manual Control")
        
        field_name = "app_status"
        self.field_vars[field_name] = tk.StringVar()
        app_status = ttk.Label(root, textvariable=self.field_vars[field_name])
        app_status.configure(foreground="blue")
        app_status.pack(side="left")

        self.setup_config_tab()
        self.setup_profiling_tab()
        self.setup_manual_tab()

        center_window(self.root)
        
    def setup_config_tab(self):
        # Create and grid a frame for better organization
        config_frame = ttk.Frame(self.config_tab)
        config_frame.pack(padx=10, pady=10, fill="both")
        # Config fields
        ttk.Button(config_frame, text="Retrieve Float Config", command=self.get_config_vars).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(config_frame, text="Update Float Config", command=self.set_config_vars).grid(row=0, column=2, padx=5, pady=5)
        
        field_name = "Company Name"
        self.field_vars[field_name] = tk.StringVar()
        ttk.Label(config_frame, text=f"{field_name}:").grid(row=2, column=1, padx=5, pady=5, sticky="e")
        ttk.Entry(config_frame, textvariable=self.field_vars[field_name], width=20).grid(row=2, column=2, padx=5, pady=5, sticky="w")
        field_name = "Max Profiling Time"
        self.field_vars[field_name] = tk.StringVar()
        ttk.Label(config_frame, text=f"{field_name} (s):").grid(row=3, column=1, padx=5, pady=5, sticky="e")
        ttk.Entry(config_frame, textvariable=self.field_vars[field_name], width=10).grid(row=3, column=2, padx=5, pady=5, sticky="w")
        field_name = "Target Depth Tolerance"
        self.field_vars[field_name] = tk.StringVar()
        ttk.Label(config_frame, text=f"{field_name} (m):").grid(row=4, column=1, padx=5, pady=5, sticky="e")
        ttk.Entry(config_frame, textvariable=self.field_vars[field_name], width=5).grid(row=4, column=2, padx=5, pady=5, sticky="w")
        field_name = "Current Depth"
        self.field_vars[field_name] = tk.StringVar()
        ttk.Label(config_frame, text=f"{field_name} (m):").grid(row=5, column=1, padx=5, pady=5, sticky="e")
        ttk.Entry(config_frame, state="readonly", textvariable=self.field_vars[field_name], width=10).grid(row=5, column=2, padx=5, pady=5, sticky="w")
        field_name = "Float ESP32 IP"
        self.field_vars[field_name] = tk.StringVar()
        ttk.Label(config_frame, text=f"{field_name}:", ).grid(row=6, column=1, padx=5, pady=5, sticky="e")
        ttk.Entry(config_frame, state="readonly", textvariable=self.field_vars[field_name], width=20).grid(row=6, column=2, padx=5, pady=5, sticky="w")
            
    def get_config_vars(self):
    # Set default values for all fields
        params = {"command":"GETCONFIG"}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            config_setting = json.loads(resp.text)
            for field, value in config_setting.items():
                self.field_vars[field].set(value)
            self.field_vars["app_status"].set("Get config settings successfully.")
        else:
            self.field_vars["app_status"].set(f"Get config settings failed. Error {resp.text}")

    def set_config_vars(self):    
        msg="command=config&";    
        for field, var in self.field_vars.items():
            msg+=f"{field}={var.get()}&"
        print(msg)
        params = {"command": "SETCONFIG",
                  "Company Name": self.field_vars["Company Name"].get(),
                  "Max Profiling Time": self.field_vars["Max Profiling Time"].get(),
                  "Target Depth Tolerance": self.field_vars["Target Depth Tolerance"].get()
                  }
        print(params)
        resp=requests.get(ctrl_endpoint, params, timeout=30)
        if (resp.status_code == 200):
            print("config setting updated")
            self.field_vars["app_status"].set("Set config settings successfully.")
        else:
            self.field_vars["app_status"].set(f"Set config settings failed. Error {resp.text}")

    def setup_profiling_tab(self):
        # Top frame for buttons and inputs
        top_frame = ttk.Frame(self.profiling_tab)
        top_frame.pack(side="top", padx=10, pady=10, fill="y")
        
        # Bottom frame for text output
        bottom_frame = ttk.Frame(self.profiling_tab)
        bottom_frame.pack(side="bottom", padx=10, pady=10, fill="both", expand=True)
        
        # Status section
        ttk.Button(top_frame, text="Status", width=15, command=self.get_status).grid(row=1, column=1, padx=5, pady=5, sticky="e")
        self.field_vars["Status"] = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.field_vars["Status"], width=50).grid(row=1, column=2, columnspan=6, padx=5, pady=5, sticky="ew")
        
        # PID section
        ttk.Button(top_frame, text="Start Profiling", command=self.send_start_profiling, width=15).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(top_frame, text="p:").grid(row=2, column=2, padx=0, pady=5, sticky="w")
        self.field_vars["p"] = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.field_vars["p"], width=5).grid(row=2, column=3, padx=0, pady=5, sticky="w")  
        ttk.Label(top_frame, text="i:").grid(row=2, column=4, padx=0, pady=5, sticky="w")
        self.field_vars["i"] = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.field_vars["i"], width=5).grid(row=2, column=5, padx=0, pady=5, sticky="w")
        ttk.Label(top_frame, text="d:").grid(row=2, column=6, padx=0, pady=5, sticky="w")
        self.field_vars["d"] = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.field_vars["d"], width=5).grid(row=2, column=7, padx=0, pady=5, sticky="w")
        # Data buttons
        ttk.Button(top_frame, text="Retrieve Data", command=self.retrieve_data, width=15).grid(row=3, column=1, columnspan=1, padx=5, pady=5, sticky="e")
        ttk.Button(top_frame, text="Retrieve PID Data", command=self.retrieve_pid_data, width=15).grid(row=3, column=3, columnspan=1, padx=5, pady=5, sticky="e")
        ttk.Button(top_frame, text="Plot Data", command=self.plot_data, width=15).grid(row=3, column=5, columnspan=1, padx=5, pady=5, sticky="e")
        
        # Text output with scrollbar
        text_frame = ttk.Frame(bottom_frame)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.data_text = tk.Text(text_frame, height=15, width=40, yscrollcommand=scrollbar.set)
        self.data_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.data_text.yview)

    def get_status(self):
        params = {"command":"STATUS"}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.field_vars["Status"].set(resp.text)
            tokens = resp.text.split(" ")
            self.field_vars["p"].set(tokens[8])
            self.field_vars["i"].set(tokens[10])
            self.field_vars["d"].set(tokens[12])
            self.field_vars["app_status"].set("Get status successfully.")
        else:
            self.field_vars["app_status"].set(f"Get status failed. Error {resp.text}")

    def retrieve_data(self):        
        resp = requests.get(data_endpoint, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.data_text.delete("1.0", tk.END)
            self.data_text.insert("1.0", resp.text)
            data_file = open("float_profile.csv", "w")
            data_file.write(resp.text)
            data_file.close()
            self.field_vars["app_status"].set("Retrieve data successfully.")
        else:
            self.field_vars["app_status"].set(f"Retrieve data failed. Error {resp.text}")

    def retrieve_pid_data(self):
    # Set default values for all fields        
        resp = requests.get(piddata_endpoint, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.data_text.delete("1.0", tk.END)
            self.data_text.insert("1.0", resp.text)
            self.field_vars["app_status"].set("Get PID data successfully.")
        else:
            self.field_vars["app_status"].set(f"Get PID data failed. Error {resp.text}")

    def plot_data(self):
        popup = Toplevel(self.root)
        popup.title("Depth Plot")
        popup.geometry("800x400")  # Set the size of the popup window

        # Sample data creation
        data = pd.read_csv(f'float_profile8.csv', sep=' ')

        df = pd.DataFrame(data)
        df['Time'] = df['Time'] - df['Time'].iloc[0]        
        df.set_index('Time', inplace=True)

        # Create a new index for 5-second intervals within an hour
        new_index = pd.Index(np.arange(0, 85, 5), name='Time_5s')

        # Reindex the DataFrame to include the new index
        df_reindexed = df.reindex(new_index)
        df_reindexed.head()
        df_reindexed.ffill() #forward filling missing value with the last non-missing value
        # Interpolate the data
        df_interpolated = df_reindexed.interpolate(method='linear', limit_direction='both')
        df_interpolated.head()

        # Plot the interpolated data
        fig, ax = plt.subplots()
        #fig= plt.figure(figsize=(10, 5))
        plt.plot(df_interpolated.index, df_interpolated['Depth'], marker='o')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Depth (meters)')
        plt.title('Depth Data at 5-Second Intervals')
        ax.invert_yaxis()
        plt.grid(True)

        # Embed the matplotlib figure in the Tkinter popup window
        canvas = FigureCanvasTkAgg(fig, master=popup)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        center_window(popup)

    def send_start_profiling(self):
        params = {"command":"START",
                  "p": self.field_vars["p"].get(),
                  "i": self.field_vars["i"].get(),
                  "d": self.field_vars["d"].get()}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.field_vars["app_status"].set("Start profiling successfully.")
        else:
            self.field_vars["app_status"].set(f"Start profiling failed. Error {resp.text}")


    def setup_manual_tab(self):
        manual_frame = ttk.Frame(self.manual_tab)
        manual_frame.pack(padx=10, pady=10, fill="both")
        
        # Up control
        ttk.Button(manual_frame, text="Up", command=self.go_up, width=15).grid(row=1, column=1, padx=5, pady=5, sticky="e")
        self.field_vars["Up Seconds"] = tk.StringVar()
        ttk.Entry(manual_frame, textvariable=self.field_vars["Up Seconds"], width=10).grid(row=1, column=2, padx=5, pady=5, sticky="w")
        ttk.Label(manual_frame, text="Seconds").grid(row=1, column=3, padx=5, pady=5, sticky="w")
        
        # Down control
        ttk.Button(manual_frame, text="Down", command=self.go_down, width=15).grid(row=2, column=1, padx=5, pady=5, sticky="e")
        self.field_vars["Down Seconds"] = tk.StringVar()
        ttk.Entry(manual_frame, textvariable=self.field_vars["Down Seconds"], width=10).grid(row=2, column=2, padx=5, pady=5, sticky="w")
        ttk.Label(manual_frame, text="Seconds").grid(row=2, column=3, padx=5, pady=5, sticky="w")

        # Control buttons
        ttk.Button(manual_frame, text="Stop Pump", command=self.stop_pump, width=15).grid(row=3, column=1, padx=5, pady=5, sticky="")
        ttk.Button(manual_frame, text="Reset ESP32", command=self.reset_ESP32, width=15).grid(row=3, column=2, padx=5, pady=5, sticky="")

    def go_down(self):
        params = {"command":"DOWN", "seconds":self.field_vars["Down Seconds"].get()}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.field_vars["app_status"].set("Go down successfully.")
        else:
            self.field_vars["app_status"].set(f"Go down failed. Error {resp.text}")

    def go_up(self):
        params = {"command":"UP", "seconds":self.field_vars["Up Seconds"].get()}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.field_vars["app_status"].set("Go up successfully.")
        else:
            self.field_vars["app_status"].set(f"Go up failed. Error {resp.text}")

    def stop_pump(self):
        params = {"command":"STOP"}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.field_vars["app_status"].set("Stop pump successfully.")
        else:
            self.field_vars["app_status"].set(f"Stop pump failed. Error {resp.text}")

    def reset_ESP32(self):
        params = {"command":"RESET"}
        resp = requests.get(ctrl_endpoint, params=params, timeout=30)
        if (resp.status_code == 200):
            print(resp.text)
            self.field_vars["app_status"].set("Reset ESP32 successfully.")
        else:
            self.field_vars["app_status"].set(f"Reset EPS32 failed. Error {resp.text}")

def main():
    root = tk.Tk()
    app = FloatControlCenter(root)
    root.mainloop()

if __name__ == "__main__":
    main()