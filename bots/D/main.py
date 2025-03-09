import time
import logging
import configparser

# Configure logging for the bot
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='bot_a.log')  # Different log file

# Load configuration
config = configparser.ConfigParser()
config.read('config.ini')

# Example variables from config
api_key = config['API']['key']
setting1 = config['SETTINGS']['setting1']


def main():
    logging.info("Bot A started.")

    try:
        while True:
            logging.info(f"Bot A is running. API Key: {api_key}, Setting1: {setting1}")
            time.sleep(10) # Simulate bot doing something
    except KeyboardInterrupt:
        logging.info("Bot A stopped.")


if __name__ == "__main__":
    main()