import os
from dotenv import load_dotenv
from gmail_reader import get_emails
from task_parser import parse_all_emails
from calendar_writer import add_tasks_to_calendar, sync_moodle_assignments
from moodle_scraper import scrape_moodle
import logging
from datetime import datetime

load_dotenv()

logging.basicConfig(
    filename='logs/bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    encoding='utf-8'
)

def run_bot():
    print(f"\n{'='*40}")
    print(f"בוט רץ: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*40}")
    logging.info("בוט התחיל")

    USERNAME = os.getenv('MOODLE_USERNAME')
    PASSWORD = os.getenv('MOODLE_PASSWORD')

    try:
        print("\n--- מודל ---")
        assignments = scrape_moodle(USERNAME, PASSWORD)
        sync_moodle_assignments(assignments)
        logging.info(f"מודל: {len(assignments)} מטלות")
    except Exception as e:
        print(f"שגיאה במודל: {e}")
        logging.error(f"שגיאה במודל: {e}")

    try:
        print("\n--- מיילים ---")
        emails = get_emails()
        tasks = parse_all_emails(emails)
        add_tasks_to_calendar(tasks)
        logging.info(f"מיילים: {len(tasks)} משימות")
    except Exception as e:
        print(f"שגיאה במיילים: {e}")
        logging.error(f"שגיאה במיילים: {e}")

    print("\nהבוט סיים!")
    logging.info("הבוט סיים בהצלחה")


if __name__ == '__main__':
    run_bot()