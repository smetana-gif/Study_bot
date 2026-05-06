from datetime import datetime, timedelta
from gmail_reader import get_google_service
import os
from dotenv import load_dotenv

load_dotenv()


def parse_israeli_date(date_str):
    date_str = date_str.strip()
    current_year = datetime.now().year

    if '.' in date_str:
        parts = date_str.split('.')
        try:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2]) if len(parts) > 2 and parts[2] else current_year
            if year < 100:
                year += 2000
            return datetime(year, month, day, 23, 59)
        except:
            return None

    if '/' in date_str:
        parts = date_str.split('/')
        try:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2]) if len(parts) > 2 and parts[2] else current_year
            if year < 100:
                year += 2000
            return datetime(year, month, day, 23, 59)
        except:
            return None

    return None


def get_all_bot_events(service):
    now = datetime.now()
    time_min = now.strftime('%Y-%m-%dT00:00:00+03:00')
    time_max = (now + timedelta(days=365)).strftime('%Y-%m-%dT00:00:00+03:00')

    results = service.events().list(
        calendarId='primary',
        q='📚 הגשה:',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return results.get('items', [])


def find_existing_event(service, course_name):
    now = datetime.now()
    time_min = now.strftime('%Y-%m-%dT00:00:00+03:00')
    time_max = (now + timedelta(days=365)).strftime('%Y-%m-%dT00:00:00+03:00')

    results = service.events().list(
        calendarId='primary',
        q=course_name[:30],
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = results.get('items', [])
    for event in events:
        summary = event.get('summary', '')
        if course_name[:20].lower() in summary.lower():
            return event

    return None


def get_reminders():
    return {
        'useDefault': False,
        'overrides': [
            {'method': 'email', 'minutes': 3 * 24 * 60},
            {'method': 'popup', 'minutes': 3 * 24 * 60},
            {'method': 'popup', 'minutes': 60},
        ],
    }


def update_event_date(service, event, new_date_str, reason=''):
    new_dt = parse_israeli_date(new_date_str)
    if not new_dt:
        return None

    event['start'] = {
        'dateTime': new_dt.strftime('%Y-%m-%dT23:59:00+03:00'),
        'timeZone': 'Asia/Jerusalem',
    }
    event['end'] = {
        'dateTime': (new_dt + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S+03:00'),
        'timeZone': 'Asia/Jerusalem',
    }
    old_desc = event.get('description', '')
    event['description'] = f"עודכן לתאריך {new_date_str}\n{reason[:100]}\n\n{old_desc}"
    event['reminders'] = get_reminders()

    updated = service.events().update(
        calendarId='primary',
        eventId=event['id'],
        body=event
    ).execute()

    print(f"עודכן תאריך: {event['summary'][:40]} → {new_dt.strftime('%d/%m/%Y')}")
    return updated


def add_event_to_calendar(title, deadline_str, description=''):
    service = get_google_service('calendar', 'v3')

    deadline_dt = parse_israeli_date(deadline_str)
    if not deadline_dt:
        print(f"לא הצלחתי לפענח תאריך: {deadline_str}")
        return None

    existing = service.events().list(
        calendarId='primary',
        q=title[:30],
        timeMin=deadline_dt.strftime('%Y-%m-%dT00:00:00+03:00'),
        timeMax=(deadline_dt + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00+03:00')
    ).execute()

    if existing.get('items'):
        print(f"קיים: {title[:40]}")
        return None

    event = {
        'summary': f"📚 הגשה: {title[:60]}",
        'description': description[:200] if description else '',
        'start': {
            'dateTime': deadline_dt.strftime('%Y-%m-%dT23:59:00+03:00'),
            'timeZone': 'Asia/Jerusalem',
        },
        'end': {
            'dateTime': (deadline_dt + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S+03:00'),
            'timeZone': 'Asia/Jerusalem',
        },
        'reminders': get_reminders(),
    }

    created = service.events().insert(calendarId='primary', body=event).execute()
    print(f"נוסף: {title[:40]} — {deadline_dt.strftime('%d/%m/%Y')}")
    return created


def add_tasks_to_calendar(tasks):
    service = get_google_service('calendar', 'v3')
    added = 0
    updated = 0
    skipped = 0

    for task in tasks:
        if not task['has_deadline']:
            skipped += 1
            continue

        for date in task['dates_found']:
            if task.get('is_postponement'):
                existing = find_existing_event(service, task['course'])
                if existing:
                    result = update_event_date(
                        service,
                        existing,
                        date,
                        reason=task['body'][:100]
                    )
                    if result:
                        updated += 1
                    continue
                else:
                    print(f"לא נמצא אירוע קיים לדחייה: {task['course'][:40]}")

            result = add_event_to_calendar(
                title=task['title'],
                deadline_str=date,
                description=task['body'][:200]
            )
            if result:
                added += 1
            else:
                skipped += 1

    print(f"\nסיכום מיילים: {added} נוספו, {updated} עודכנו, {skipped} דולגו")


def sync_moodle_assignments(assignments):
    service = get_google_service('calendar', 'v3')
    added = 0
    updated = 0
    deleted = 0
    skipped = 0

    existing_events = get_all_bot_events(service)
    print(f"נמצאו {len(existing_events)} אירועים קיימים ביומן")

    moodle_titles = {a['title'].strip().lower(): a for a in assignments}

    for event in existing_events:
        summary = event.get('summary', '')
        clean_title = summary.replace('📚 הגשה: ', '').strip().lower()

        matched_assignment = None
        for moodle_title, assignment in moodle_titles.items():
            if moodle_title in clean_title or clean_title in moodle_title:
                matched_assignment = assignment
                break

        if matched_assignment is None:
            service.events().delete(
                calendarId='primary',
                eventId=event['id']
            ).execute()
            print(f"🗑️  נמחק: {summary[:40]} (לא קיים יותר במודל)")
            deleted += 1
        else:
            event_date_str = event['start'].get('dateTime', '')
            if event_date_str:
                event_date = datetime.fromisoformat(event_date_str[:10])
                moodle_date = matched_assignment['deadline']

                if event_date.date() != moodle_date.date():
                    event['start'] = {
                        'dateTime': moodle_date.strftime('%Y-%m-%dT23:59:00+03:00'),
                        'timeZone': 'Asia/Jerusalem',
                    }
                    event['end'] = {
                        'dateTime': (moodle_date + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S+03:00'),
                        'timeZone': 'Asia/Jerusalem',
                    }
                    old_desc = event.get('description', '')
                    event['description'] = f"תאריך עודכן אוטומטית ל־{matched_assignment['deadline_str']}\n\n{old_desc}"
                    event['reminders'] = get_reminders()

                    service.events().update(
                        calendarId='primary',
                        eventId=event['id'],
                        body=event
                    ).execute()
                    print(f"🔄 עודכן תאריך: {summary[:40]} → {matched_assignment['deadline_str']}")
                    updated += 1
                else:
                    skipped += 1

    existing_titles = [
        e.get('summary', '').replace('📚 הגשה: ', '').strip().lower()
        for e in existing_events
    ]

    for assignment in assignments:
        title_lower = assignment['title'].strip().lower()
        already_exists = any(
            title_lower in et or et in title_lower
            for et in existing_titles
        )

        if not already_exists:
            end_time = assignment['deadline'] + timedelta(hours=1)
            event = {
                'summary': f"📚 הגשה: {assignment['title']}",
                'start': {
                    'dateTime': assignment['deadline'].strftime('%Y-%m-%dT23:59:00+03:00'),
                    'timeZone': 'Asia/Jerusalem',
                },
                'end': {
                    'dateTime': end_time.strftime('%Y-%m-%dT%H:%M:%S+03:00'),
                    'timeZone': 'Asia/Jerusalem',
                },
                'reminders': get_reminders(),
            }
            service.events().insert(calendarId='primary', body=event).execute()
            print(f"✅ נוסף: {assignment['title'][:40]} — {assignment['deadline_str']}")
            added += 1

    print(f"\nסיכום מודל: {added} נוספו, {updated} עודכנו, {deleted} נמחקו, {skipped} ללא שינוי")


if __name__ == '__main__':
    from moodle_scraper import scrape_moodle
    from task_parser import parse_all_emails
    from gmail_reader import get_emails

    USERNAME = os.getenv('MOODLE_USERNAME')
    PASSWORD = os.getenv('MOODLE_PASSWORD')

    print("=== סנכרון מודל ===")
    assignments = scrape_moodle(USERNAME, PASSWORD)
    sync_moodle_assignments(assignments)

    print("\n=== מיילים ===")
    emails = get_emails()
    tasks = parse_all_emails(emails)
    add_tasks_to_calendar(tasks)