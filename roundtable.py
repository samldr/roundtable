import typer
import os
# import pdb
from redminelib import Redmine
from datetime import datetime, timedelta
from collections import defaultdict
from rich import print
from rich.table import Table
from rich.console import Console

app = typer.Typer()
console = Console()

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


@app.command()
def update():
    """
    Updates assigned Redmine issues
    """
    assigned_issues = defaultdict(list)
    for issue in issues:
        assigned_to = getattr(issue, 'assigned_to', None)
        assigned_name = assigned_to.name if assigned_to else 'Unassigned'
        assigned_issues[assigned_name].append(issue)

    for user in assigned_issues:
        if user == 'Unassigned':
            continue
        
        table = Table(show_footer=False, title=f"[bold]Issues assigned to {user}", title_justify="left")
        table.add_column("ID")
        table.add_column("Subject")
        table.add_column("Progress")
        table.add_column("Due Date")

        for issue in assigned_issues[user]:
            due_date = issue.due_date if hasattr(issue, 'due_date') else 'N/A'
            table.add_row(str(issue.id), issue.subject, f"{issue.done_ratio}%", str(due_date))

        console.print("\n")
        console.print(table)


        for issue in assigned_issues[user]:
            print(f"\n[bold white]{issue.id}: {issue.subject}")
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
                    if percent.lower() == 'n':
                        percent = issue.done_ratio
                        break
                    percent = input("Please enter a valid percentage [0-100]: ").strip()
                redmine.issue.update(
                    issue.id,
                    done_ratio=int(percent)
                )
                print(f"Current due date: [bold white]{issue.due_date}")
                delay = prompt("Move task to next week?")
                if delay == 'y':
                    redmine.issue.update(
                        issue.id,
                        due_date=issue.due_date + timedelta(7)
                    )
            print(f'Link to issue: {REDMINE_URL}/issues/{issue.id}')    


if __name__ == "__main__":
    app()