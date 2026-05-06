import re
from gmail_reader import get_emails

DEADLINE_KEYWORDS = [
    'deadline', 'due', 'הגשה', 'מועד אחרון',
    'יש להגיש', 'תאריך הגשה', 'מטלה', 'assignment'
]

IGNORE_KEYWORDS = [
    'you have submitted',
    'your submission',
    'הגשתך התקבלה',
    'submission received',
    'you submitted',
]

# מילות מפתח לזיהוי דחייה
POSTPONE_KEYWORDS = [
    'דחייה', 'נדחה', 'נדחית', 'תאריך חדש', 'מועד חדש',
    'extended', 'postponed', 'new deadline', 'new due date',
    'הוארך', 'דחינו', 'דוחים'
]

DATE_PATTERNS = [
    r'\d{1,2}\.\d{1,2}(?:\.\d{2,4})?',
    r'\d{1,2}/\d{1,2}(?:/\d{2,4})?',
    r'\d{4}-\d{2}-\d{2}',
    r'\d{1,2} (?:ינואר|פברואר|מרץ|אפריל|מאי|יוני|יולי|אוגוסט|ספטמבר|אוקטובר|נובמבר|דצמבר)',
    r'\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*',
]

DEADLINE_SENTENCE_PATTERNS = [
    r'תאריך ההגשה[^\n.]*?(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
    r'יש להגיש[^\n.]*?(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
    r'מועד אחרון[^\n.]*?(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
    r'due[^\n.]*?(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
    r'deadline[^\n.]*?(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
    r'נדח[^\n.]*?(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
    r'תאריך חדש[^\n.]*?(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
    r'מועד חדש[^\n.]*?(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
    r'extended[^\n.]*?(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)',
]


def extract_deadline_dates(body):
    deadlines = []
    for pattern in DEADLINE_SENTENCE_PATTERNS:
        matches = re.findall(pattern, body, re.IGNORECASE)
        deadlines.extend(matches)
    return list(set(deadlines))


def is_postponement(subject, body):
    """בודק אם המייל הוא הודעת דחייה"""
    text = f"{subject} {body}".lower()
    return any(kw.lower() in text for kw in POSTPONE_KEYWORDS)


def extract_course_name(subject):
    """מחלץ שם קורס מנושא המייל"""
    # נושא BGU בפורמט: "שם קורס: נושא הודעה"
    if ':' in subject:
        return subject.split(':')[0].strip()
    return subject.strip()


def extract_tasks_from_email(subject, body=''):
    tasks = []
    text = f"{subject} {body}".lower()

    is_confirmation = any(kw.lower() in text for kw in IGNORE_KEYWORDS)
    if is_confirmation:
        return tasks

    has_keyword = any(kw.lower() in text for kw in DEADLINE_KEYWORDS)
    if not has_keyword:
        return tasks

    deadline_dates = extract_deadline_dates(body)

    if not deadline_dates:
        for pattern in DATE_PATTERNS:
            matches = re.findall(pattern, subject, re.IGNORECASE)
            deadline_dates.extend(matches)

    task = {
        'title': subject,
        'course': extract_course_name(subject),
        'body': body,
        'dates_found': deadline_dates,
        'has_deadline': len(deadline_dates) > 0,
        'is_postponement': is_postponement(subject, body)
    }
    tasks.append(task)
    return tasks


def parse_all_emails(emails):
    all_tasks = []

    for email in emails:
        tasks = extract_tasks_from_email(
            subject=email['subject'],
            body=email.get('body', '')
        )
        if tasks:
            for task in tasks:
                tag = "🔄 דחייה" if task['is_postponement'] else "✅ משימה"
                print(f"{tag}: {task['title'][:60]}...")
                if task['dates_found']:
                    print(f"   📅 תאריך: {task['dates_found']}")
                else:
                    print(f"   ⚠️  לא נמצא תאריך")
            all_tasks.extend(tasks)

    print(f"\nסה\"כ {len(all_tasks)} משימות זוהו")
    return all_tasks


if __name__ == '__main__':
    print("שולף מיילים...")
    emails = get_emails()
    print("\nמנתח משימות...\n")
    tasks = parse_all_emails(emails)