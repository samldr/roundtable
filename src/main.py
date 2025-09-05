import os
# import pdb
from redminelib import Redmine
from datetime import datetime, timedelta
from collections import defaultdict

REDMINE_URL = os.environ.get('REDMINE_URL') 
REDMINE_API_KEY = os.environ.get('REDMINE_API_KEY') 
PROJECT = 'dfgm'

redmine = Redmine(REDMINE_URL, key=REDMINE_API_KEY)
project = redmine.project.get(PROJECT)
issues = redmine.issue.filter(project_id=project.id, status_id='open')
    

def prompt(message):
    query = input(f"{message} [y/n]: ").strip().lower()
    while query not in ('y', 'n'):
        query = input("Please enter 'y' or 'n': ").strip().lower()
    return query


def tuesday():
    today = datetime.now()
    if today.weekday() == 1:
        return today
    day = 1 - today.weekday()
    return today + timedelta(day)


def update_issues():
    assigned_issues = defaultdict(list)
    for issue in issues:
        assigned_to = getattr(issue, 'assigned_to', None)
        assigned_name = assigned_to.name if assigned_to else 'Unassigned'
        assigned_issues[assigned_name].append(issue)

    for user in assigned_issues:
        if user == 'Unassigned':
            continue
        
        print(f"\nIssues assigned to {user}:")
        for issue in assigned_issues[user]:
            print(f"{issue.id}: {issue.subject}")
            query = prompt("Issue Completed?")
            if query == 'y':
                redmine.issue.update(
                    issue.id,
                    status_id=5,
                    done_ratio=100
                )
            elif query == 'n':
                percent = input(f"Progress (currently {issue.done_ratio}%) [0-100]: ").strip()
                while not percent.isdigit() or not (0 <= int(percent) <= 100):
                    percent = input("Please enter a valid percentage [0-100]: ").strip()
                redmine.issue.update(
                    issue.id,
                    done_ratio=int(percent)
                )
                print(f"Current due date: {issue.due_date}")
                delay = prompt("Move task to next week?")
                if delay == 'y':
                    redmine.issue.update(
                        issue.id,
                        due_date=issue.due_date + timedelta(7)
                    )


def main():
    update_issues()

if __name__ == "__main__":
    main()

