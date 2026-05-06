# Study Bot 🤖

An automated daily bot that syncs Moodle LMS assignments to Google Calendar.

## What it does
- Scrapes BGU's Moodle calendar daily at 8:00 AM
- Extracts assignment deadlines automatically
- Adds, updates, and deletes events in Google Calendar
- Reads Gmail for deadline notifications and postponements
- Runs autonomously via Windows Task Scheduler

## Tech Stack
- Python, Selenium, Google Calendar API, Gmail API, OAuth2

## Features
- Prevents duplicate calendar events
- Detects postponed deadlines and updates calendar automatically
- Removes assignments that no longer exist in Moodle
- Reminders 3 days and 1 hour before each deadline
