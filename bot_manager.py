import os
import subprocess
import threading
import time
import logging
from datetime import datetime
import configparser
import psutil  # For checking process status
from flask import Flask, render_template, request, redirect, url_for
import schedule

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='bot_manager.log')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this!

BOT_DIR = 'bots'
LOG_DIR = 'logs'
# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)


def get_bot_names():
    """Returns a list of bot names (A, B, C...) by listing subdirectories."""
    return sorted([d for d in os.listdir(BOT_DIR) if os.path.isdir(os.path.join(BOT_DIR, d))])


def get_bot_status(bot_name):
    """Checks if a bot process is running."""
    bot_process_name = f"python {os.path.join(BOT_DIR, bot_name, 'main.py')}"
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if bot_process_name in ' '.join(proc.cmdline()): # Check if it's part of the command line
                return True, proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False, None


def start_bot(bot_name):
    """Starts a bot in a separate process."""
    bot_path = os.path.join(BOT_DIR, bot_name, 'main.py')
    log_file_path = os.path.join(LOG_DIR, f"{bot_name}.log")

    # Use subprocess.Popen to start the bot in the background
    with open(log_file_path, 'a') as log_file:  # 'a' for append mode
        process = subprocess.Popen(['python', bot_path],
                                   stdout=log_file,
                                   stderr=subprocess.STDOUT,
                                   cwd=os.path.join(BOT_DIR, bot_name))  # Important: set cwd

    logging.info(f"Started bot {bot_name} (PID: {process.pid})")
    return process.pid


def stop_bot(bot_name, pid):
    """Stops a bot process, given its PID."""
    try:
        process = psutil.Process(pid)
        process.terminate()  # Or .kill() for a more forceful termination
        process.wait(timeout=10) # Wait for termination (optional timeout)
        logging.info(f"Stopped bot {bot_name} (PID: {pid})")
    except psutil.NoSuchProcess:
        logging.warning(f"Bot {bot_name} (PID: {pid}) not found.")
    except Exception as e:
        logging.error(f"Error stopping bot {bot_name} (PID: {pid}): {e}")


def get_bot_log(bot_name, num_lines=10):
    """Reads the last `num_lines` from the bot's log file."""
    log_file_path = os.path.join(LOG_DIR, f"{bot_name}.log")
    try:
        with open(log_file_path, 'r') as f:
            lines = f.readlines()
            return lines[-num_lines:]
    except FileNotFoundError:
        return [f"Log file not found for bot {bot_name}"]
    except Exception as e:
        return [f"Error reading log for bot {bot_name}: {e}"]


def get_bot_config(bot_name):
    """Reads the configuration file for a bot."""
    config_file_path = os.path.join(BOT_DIR, bot_name, 'config.ini')
    config = configparser.ConfigParser()
    try:
        config.read(config_file_path)
        return config
    except Exception as e:
        return str(e)  # Return error message if config can't be read.


def run_scheduled_bots():
    """Runs the schedule in a separate thread."""
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


# Flask Routes
@app.route("/")
def index():
    """Main dashboard."""
    bots = get_bot_names()
    bot_statuses = {}
    for bot in bots:
        is_running, pid = get_bot_status(bot)
        bot_statuses[bot] = {'running': is_running, 'pid': pid}

    return render_template("index.html", bots=bots, bot_statuses=bot_statuses)


@app.route("/bot/<bot_name>")
def bot_details(bot_name):
    """Details page for a specific bot."""
    is_running, pid = get_bot_status(bot_name)
    log_lines = get_bot_log(bot_name)
    config = get_bot_config(bot_name)
    return render_template("bot_details.html", bot_name=bot_name, running=is_running, pid=pid, log_lines=log_lines, config=config)


@app.route("/start_bot", methods=["POST"])
def start_bot_route():
    """Starts a bot via a POST request."""
    bot_name = request.form["bot_name"]
    start_bot(bot_name)
    return redirect(url_for("index"))


@app.route("/stop_bot", methods=["POST"])
def stop_bot_route():
    """Stops a bot via a POST request."""
    bot_name = request.form["bot_name"]
    pid = int(request.form["pid"]) # Get PID from the form
    stop_bot(bot_name, pid)
    return redirect(url_for("index"))


@app.route("/schedule_bot", methods=["POST"])
def schedule_bot():
    """Schedules a bot to run at a specific time."""
    bot_name = request.form["bot_name"]
    schedule_time = request.form["schedule_time"]  # e.g., "10:30"

    # Schedule the bot to run at the specified time
    schedule.every().day.at(schedule_time).do(start_bot, bot_name)
    logging.info(f"Scheduled bot {bot_name} to run at {schedule_time}")
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduled_bots)
    scheduler_thread.daemon = True  # Allow the main program to exit even if the thread is running
    scheduler_thread.start()

    app.run(debug=True)  # Don't use debug=True in production!