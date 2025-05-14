from flask import Flask, jsonify, request
from flask_cors import CORS
import psutil
import os
import signal
import time
from collections import deque

app = Flask(__name__)
CORS(app)  # Allow frontend to access API

# Round Robin Scheduling Setup
process_queue = deque()
time_quantum = 2  # Each process gets 2 seconds

# Function to collect system metrics
@app.route('/metrics', methods=['GET'])
def get_metrics():
    return jsonify({
        "CPU Usage (%)": psutil.cpu_percent(interval=1),
        "Memory Usage (%)": psutil.virtual_memory().percent,
        "Disk Usage (%)": psutil.disk_usage('/').percent,
        "Running Processes": [{"pid": p.pid, "name": p.name()} for p in psutil.process_iter(['pid', 'name'])]
    })

# Function to add processes to the scheduling queue
def add_to_queue():
    process_queue.clear()
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        if proc.info['cpu_percent'] > 0:
            process_queue.append(proc.info)

# Round Robin Scheduler
def round_robin_schedule():
    if not process_queue:
        add_to_queue()

    if process_queue:
        current_process = process_queue.popleft()
        pid = current_process['pid']
        
        try:
            process = psutil.Process(pid)
            process.cpu_affinity([0])  # Restrict process to one CPU core
            time.sleep(time_quantum)  # Simulate execution time
            process_queue.append(current_process)  # Add back to queue
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

# API Route to trigger scheduling
@app.route('/schedule', methods=['POST'])
def schedule():
    round_robin_schedule()
    return jsonify({"message": "Round Robin Scheduling executed successfully"})

@app.route('/')
def index():
    return "System Monitor Backend is Live!"

# API to kill a specific process
@app.route('/kill_process', methods=['POST'])
def kill_process():
    try:
        pid = request.json.get("pid")
        if pid is None:
            return jsonify({"error": "Missing PID"}), 400
        
        os.kill(pid, signal.SIGTERM)  # Kill process
        return jsonify({"message": f"Process {pid} terminated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port, debug=True)
