from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
from datetime import datetime

MOODLE_URL = 'https://moodle.bgu.ac.il/moodle'
CALENDAR_URL = 'https://moodle.bgu.ac.il/moodle/calendar/view.php?view=month'


def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def login_to_moodle(driver, username, password):
    print("נכנס למודל...")
    driver.get(f"{MOODLE_URL}/login/index.php")
    wait = WebDriverWait(driver, 10)
    username_field = wait.until(EC.presence_of_element_located((By.ID, 'username')))
    username_field.send_keys(username)
    password_field = driver.find_element(By.ID, 'password')
    password_field.send_keys(password)
    driver.find_element(By.ID, 'loginbtn').click()
    time.sleep(2)
    if 'login' in driver.current_url:
        raise Exception("התחברות נכשלה")
    print("התחברות הצליחה!")


def get_current_month_year(driver):
    """שולף את החודש והשנה הנוכחיים מהדף"""
    try:
        # מנסה למצוא את כותרת החודש בדף
        header = driver.find_element(By.CSS_SELECTOR, '.current .dimmed_text, h2.accesshide, .calendarwrapper h2')
        return header.text
    except:
        now = datetime.now()
        return f"{now.month}/{now.year}"


def get_assignments_from_calendar(driver):
    print("פותח מערכת שעות...")
    driver.get(CALENDAR_URL)
    time.sleep(3)

    assignments = []
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    # שולף את כל התאים בלוח
    cells = driver.find_elements(By.CSS_SELECTOR, 'td.day')

    for cell in cells:
        try:
            # מוצא את מספר היום
            day_link = cell.find_elements(By.CSS_SELECTOR, 'a')
            if not day_link:
                continue

            day_num = None
            events_in_day = []

            for link in day_link:
                text = link.text.strip()
                if not text:
                    continue

                # אם זה מספר — זה התאריך
                if text.isdigit():
                    day_num = int(text)
                # אחרת זו מטלה
                elif any(kw in text for kw in ['יש להגיש', 'is due', 'due', 'הגשה', 'Assignment', 'מטלה', 'Homework']):
                    events_in_day.append(text)

            # מחבר תאריך + מטלות
            if day_num and events_in_day:
                for event_text in events_in_day:
                    # ניקוי הטקסט
                    clean_title = event_text
                    clean_title = re.sub(r"יש להגיש את '(.+)'", r'\1', clean_title)
                    clean_title = re.sub(r"(.+) is due", r'\1', clean_title)

                    deadline = datetime(current_year, current_month, day_num, 23, 59)

                    assignment = {
                        'title': clean_title.strip(),
                        'deadline': deadline,
                        'deadline_str': deadline.strftime('%d/%m/%Y'),
                        'source': 'moodle_calendar'
                    }
                    assignments.append(assignment)
                    print(f"📌 {assignment['deadline_str']} | {assignment['title']}")

        except Exception as e:
            continue

    print(f"\nנמצאו {len(assignments)} מטלות במודל")
    return assignments


def scrape_moodle(username, password):
    driver = create_driver()
    try:
        login_to_moodle(driver, username, password)
        assignments = get_assignments_from_calendar(driver)
        return assignments
    finally:
        driver.quit()


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()

    USERNAME = os.getenv('MOODLE_USERNAME')
    PASSWORD = os.getenv('MOODLE_PASSWORD')

    if not USERNAME or not PASSWORD:
        print("שגיאה: חסרים פרטים בקובץ .env")
    else:
        scrape_moodle(USERNAME, PASSWORD)