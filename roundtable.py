import typer
import os
# import pdb
from redminelib import Redmine
from datetime import datetime, timedelta
from collections import defaultdict
from rich import print
from rich.table import Table
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt

app = typer.Typer()
console = Console()

def tuesday():
    today = datetime.now()
    if today.weekday() == 1:
        return today
    day = 1 - today.weekday()
    return (today + timedelta(day)).date()


@app.callback()
def main():
    """
    CLI for managing Redmine issues
    """
    global REDMINE_URL, REDMINE_API_KEY, PROJECT
    REDMINE_URL = os.environ.get('REDMINE_URL') 
    REDMINE_API_KEY = os.environ.get('REDMINE_API_KEY') 
    PROJECT = 'dfgm'

    global redmine, project, issues
    redmine = Redmine(REDMINE_URL, key=REDMINE_API_KEY)
    project = redmine.project.get(PROJECT)
    issues = redmine.issue.filter(project_id=project.id, status_id='open')

    title_splash = 'Roundtable CLI'
    user_splash = f'Current User: {redmine.user.get("current").login}'
    url_splash = f'Current Project: {REDMINE_URL}/projects/{project.name.lower()} '


    # print splash
    print(f"╭─{'─' * len(url_splash)}─╮")
    print(f"│ [bold]{title_splash}[/bold]{" " * (len(url_splash) - len(title_splash))} │")
    print(f"│ {user_splash}{" " * (len(url_splash) - len(user_splash))} │")
    print(f"│ {url_splash} │")
    print(f"╰─{'─' * len(url_splash)}─╯\n")


@app.command()
def update():
    """
    Update assigned Redmine issues
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

        console.print(table)

        for issue in assigned_issues[user]:
            print(f"\n[bold white]{issue.id}: {issue.subject}")
            query = Confirm.ask("Issue completed?")
            if query:
                redmine.issue.update(
                    issue.id,
                    status_id=5,
                    done_ratio=100
                )
            else:
                percent = Prompt.ask(f"Progress (currently {issue.done_ratio}%) [0-100]")
                while not percent.isdigit() or not (0 <= int(percent) <= 100):
                    if percent.lower() == 'n':
                        percent = issue.done_ratio
                        break
                    percent = Prompt.ask("Please enter a valid percentage [0-100]")
                redmine.issue.update(
                    issue.id,
                    done_ratio=int(percent)
                )
                print(f"Current due date: [bold white]{issue.due_date}")
                delay = Confirm.ask("Move task to next week?")
                if delay:
                    redmine.issue.update(
                        issue.id,
                        due_date=issue.due_date + timedelta(7)
                    )
            print(f'Link to issue: {REDMINE_URL}/issues/{issue.id}')    


@app.command()
def new():
    """
    Create new Redmine issues
    """
    while True:
        new_issue = {}
        print("[bold italic]Create New Issue")

        # title and description
        new_issue['subject'] = Prompt.ask("Issue Subject")
        
        what = Prompt.ask("What is the task?")
        why = Prompt.ask("Why are we doing this task?")

        # dates
        start = tuesday()
        deadline = IntPrompt.ask(f'Start date: [bold white]{start}[/], in how many weeks is this due?', default='1')

        new_issue['due_date'] = timedelta(deadline * 7 - 1) + start
        new_issue['start_date'] = start

        # parent task (topic)
        topics = redmine.issue.filter(project_id=project.id, tracker_id=8)

        table = Table(show_footer=False, title_justify="left")
        table.add_column("Index")
        table.add_column("Topic")
        for index, issue in enumerate(topics):
            table.add_row(str(index), issue.subject)
        console.print(table)
        topic_index = Prompt.ask("Select Parent Task", choices=[str(i) for i in range(len(topics))])

        new_issue['parent_issue_id'] = topics[int(topic_index)].id

        # assignee
        members = project.memberships
        table = Table(show_footer=False, title_justify="left")
        table.add_column("Index")
        table.add_column("Name")
        for index, user in enumerate(members):
            table.add_row(str(index), user.user.name)
        console.print(table)
        member_index = Prompt.ask("Select Assignee", choices=[str(i) for i in range(len(members))])

        new_issue['assigned_to_id'] = members[int(member_index)].user.id

        # category
        categories = project.issue_categories
        table = Table(show_footer=False, title_justify="left")
        table.add_column("Index")
        table.add_column("Category")
        for index, category in enumerate(categories):
            table.add_row(str(index), category.name)
        console.print(table)
        category_index = Prompt.ask("Select Category", choices=[str(i) for i in range(len(categories))])

        new_issue['category_id'] = categories[int(category_index)].id

        # misc
        new_issue['description'] = f"Who: {members[int(member_index)].user.name}\nWhat: {what}\nWhy: {why}"        
        new_issue['project_id'] = project.id
        new_issue['tracker_id'] = 7  # Task
        new_issue['status_id'] = 2  # In Progress
        new_issue['priority_id'] = 2  # Normal
        new_issue['done_ratio'] = 0  # 0%

        # confirmation
        print("[bold]Issue Summary:", new_issue)
        confirm = Confirm.ask("Create this issue?")
        if confirm:
            try:
                issue = redmine.issue.create(**new_issue)
                print(f"Issue created: {REDMINE_URL}/issues/{issue.id}\n")
            except Exception as e:
                print(f"[red]Error creating issue: {e}")
        loop = Confirm.ask("Add another issue?")
        if not loop:
            break  
        

if __name__ == "__main__":
    app()