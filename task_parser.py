import os
import json
from google import genai
from dotenv import load_dotenv
from gmail_reader import get_emails

load_dotenv()

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

IGNORE_KEYWORDS = [
    'you have submitted',
    'your submission',
    'submission received',
    'you submitted',
]


def analyze_email_with_gemini(subject, body):
    prompt = f"""
You are analyzing a university email. Extract assignment information.

Subject: {subject}
Body: {body[:500]}

Reply with ONLY a JSON object in this exact format, nothing else:
{{
    "is_assignment": true or false,
    "is_postponement": true or false,
    "deadline_date": "DD.MM.YYYY or null",
    "assignment_name": "name or null"
}}

Rules:
- is_assignment: true if this email is about an assignment deadline
- is_postponement: true if a deadline was moved to a new date
- deadline_date: the submission date in DD.MM.YYYY format, null if not found
- assignment_name: the assignment name, null if not found
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        text = response.text.strip()
        text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"  Gemini error: {e}")
        return None


def extract_tasks_from_email(subject, body=''):
    tasks = []
    text = f"{subject} {body}".lower()

    is_confirmation = any(kw.lower() in text for kw in IGNORE_KEYWORDS)
    if is_confirmation:
        return tasks

    print(f"  Gemini analyzing: {subject[:50]}...")
    result = analyze_email_with_gemini(subject, body)

    if not result or not result.get('is_assignment'):
        return tasks

    deadline = result.get('deadline_date')

    task = {
        'title': subject,
        'course': subject.split(':')[0].strip() if ':' in subject else subject,
        'body': body,
        'dates_found': [deadline] if deadline else [],
        'has_deadline': deadline is not None,
        'is_postponement': result.get('is_postponement', False)
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
                tag = "Postponement" if task['is_postponement'] else "Assignment"
                print(f"  [{tag}] {task['title'][:60]}")
                if task['dates_found']:
                    print(f"    Deadline: {task['dates_found']}")
                else:
                    print(f"    No date found")
            all_tasks.extend(tasks)

    print(f"\nTotal: {len(all_tasks)} tasks found")
    return all_tasks


if __name__ == '__main__':
    print("Fetching emails...")
    emails = get_emails()
    print("\nAnalyzing with Gemini AI...\n")
    tasks = parse_all_emails(emails)