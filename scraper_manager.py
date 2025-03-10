import threading
import time
import datetime
import importlib  # For dynamically importing scraper modules
import os

# Configuration
NUM_CONCURRENT_SCRAPERS = 5
NUM_SCRAPERS = 50  # Total number of scrapers
SCRAPER_MODULE_PREFIX = "scraper_bot_"
SCRAPER_DIR = "scrapers"

# Bot Status Tracking
bot_statuses = {}

def initialize_bot_statuses():
    """Initializes the status for all bots."""
    folder_names = [folder for folder in os.listdir(SCRAPER_DIR) if os.path.isdir(os.path.join(SCRAPER_DIR, folder))]
    for i in folder_names:
        bot_name = f"{i}"
        bot_statuses[bot_name] = {
            "status": "pending",
            "start_time": None,
            "end_time": None,
            "next_cycle": None, # Will be set after completion
            "last_run_status": None  # "success" or "failed"
        }

def update_bot_status(bot_name, status, **kwargs):
    """Updates the status of a bot."""
    bot_statuses[bot_name]["status"] = status
    for key, value in kwargs.items():
        bot_statuses[bot_name][key] = value

def run_scraper_bot(bot_name):
    """Runs a single scraper bot and manages status updates."""
    try:
        update_bot_status(bot_name, status="running", start_time=datetime.datetime.now())

        # Dynamically import and run the scraper function
        module_name = f"{SCRAPER_DIR}.{bot_name}.main"
        module = importlib.import_module(module_name, package=".") # package="." for relative import
        MyClass = getattr(module, 'LicenseCrawler')
        instance = MyClass()
        scraper_function = instance.run

        result = scraper_function() # Execute the scraper logic

        update_bot_status(
            bot_name,
            status="completed",
            end_time=datetime.datetime.now(),
            last_run_status="success"
        )
        return result

    except Exception as e:
        update_bot_status(
            bot_name,
            status="failed",
            end_time=datetime.datetime.now(),
            last_run_status="failed",
            error_message=str(e)
        )
        print(f"Error running {bot_name}: {e}")
        return "failed"

def manage_scraper_cycle():
    """Manages the execution of all scrapers in batches."""
    print("Starting scraper cycle...")
    initialize_bot_statuses() # Reset statuses for a new cycle
    folder_names = [folder for folder in os.listdir(SCRAPER_DIR) if os.path.isdir(os.path.join(SCRAPER_DIR, folder))]
    scraper_names = [f"{i}" for i in folder_names]
    semaphore = threading.Semaphore(NUM_CONCURRENT_SCRAPERS)
    threads = []

    for bot_name in scraper_names:
        semaphore.acquire()  # Wait if max concurrent scrapers are running
        update_bot_status(bot_name, status="pending") # Mark as pending before thread starts

        thread = threading.Thread(target=run_scraper_with_semaphore, args=(bot_name, semaphore))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    print("Scraper cycle completed.")
    set_next_cycle_times() # Calculate and set next run times

def run_scraper_with_semaphore(bot_name, semaphore):
    """Wraps run_scraper_bot to release the semaphore after execution."""
    try:
        run_scraper_bot(bot_name)
    finally:
        semaphore.release() # Ensure semaphore is released even if errors occur

def get_all_bot_statuses():
    """Returns the current status of all bots."""
    return bot_statuses

def set_next_cycle_times():
    """Sets the 'next_cycle' time for all bots (2 weeks from end time)."""
    two_weeks = datetime.timedelta(weeks=2)
    for bot_name, status_data in bot_statuses.items():
        if status_data["end_time"]: # Only set next cycle if it has run
            bot_statuses[bot_name]["next_cycle"] = status_data["end_time"] + two_weeks
        else:
            bot_statuses[bot_name]["next_cycle"] = "Not yet run" # Or a default initial next run time

def trigger_scraping_cycle(): # Function to manually start from web app or scheduler
    manage_scraper_cycle()


if __name__ == "__main__":
    # Example of running a scraper cycle manually
    trigger_scraping_cycle()
    print("\nBot Statuses:")
    for bot_name, status in get_all_bot_statuses().items():
        print(f"{bot_name}: {status}")