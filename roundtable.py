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
from typing_extensions import Annotated

app = typer.Typer()
console = Console()

def tuesday():
    today = datetime.now()
    if today.weekday() == 1:
        return today.date()
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
def update(notes: Annotated[bool, typer.Option("-n","--note", help="Add notes while updating issues")] = False):
    """
    Update assigned Redmine issues
    """
    assigned_issues = defaultdict(list)
    for issue in issues:
        assigned_to = getattr(issue, 'assigned_to', None)
        assigned_name = assigned_to.name if assigned_to else 'Unassigned'
        assigned_issues[assigned_name].append(issue)
    
    order = [
        "Sam Leader",
        "Matthew Foran",
        "Deven Thaleshvar",
        "Sandro Nevesinjac",
        "Matthew Schweiger",
        "Abel Gonzalez",
        "Toryn Rice",
        "Marie Metz",
        "Adam Hillaby",
        "Harris Oldring",
        "Bibek Kahlon",
        "Carson Mellow",
        "Joey Zhao",
        "Francesca Mison",
    ]
    sorted_users = sorted(assigned_issues.keys(), key=lambda x: order.index(x) if x in order else len(order))

    for user in sorted_users:
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
                    done_ratio=100,
                    due_date=tuesday() - timedelta(1),
                )
                print(f'Completion Date: [bold white]{tuesday() - timedelta(1)}')
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
                        due_date= tuesday() + timedelta(6)
                    )
                    print(f'New due date: [bold white]{tuesday() + timedelta(6)}')

            if notes:
                note = Prompt.ask("Note")
                if note.strip():
                    try:
                        redmine.issue.update(issue.id, notes=note)
                        print(f'Note added: [bold white]{note}')
                    except Exception as e:
                        print(f'[red]Error adding note: {e}')
            print(f'Link to issue: {REDMINE_URL}/issues/{issue.id}\n')    


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

@app.command()
def populate():
    """
    Add tasks to the backlog
    """
    while True:
        new_issue = {}
        print("[bold italic]Create New Backlog Issue")

        # title and description
        new_issue['subject'] = Prompt.ask("Issue Subject")
        
        what = Prompt.ask("What is the task?")
        why = Prompt.ask("Why are we doing this task?")

        # dates
        while True:
            try:
                start = datetime.strptime(Prompt.ask("Start date ([bold]YYYY-MM-DD[/bold])"), '%Y-%m-%d').date()
                deadline = datetime.strptime(Prompt.ask("Deadline ([bold]YYYY-MM-DD[/bold])"), '%Y-%m-%d').date()
            except ValueError as e:
                print(f"[red]Invalid date format: {e}")
                continue
            break

        new_issue['due_date'] = deadline
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
        new_issue['description'] = f"Who: \nWhat: {what}\nWhy: {why}"        
        new_issue['project_id'] = project.id
        new_issue['tracker_id'] = 7  # Task
        new_issue['status_id'] = 1  # In Progress
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

        prev_issue = redmine.issue.get(issue.id - 1)
        if prev_issue.project.id == project.id:
            blocker = Confirm.ask(f'Is this issue a blocked by the previous issue {prev_issue.id}: {prev_issue.subject}?')
            if blocker:
                try:
                    redmine.issue_relation.create(issue_id=prev_issue.id, issue_to_id=issue.id, relation_type='blocks')
                    print(f'Added blocker: {REDMINE_URL}/issues/{prev_issue.id} blocks {REDMINE_URL}/issues/{issue.id}')
                except Exception as e:
                    print(f'[red]Error adding blocker: {e}')
        

        loop = Confirm.ask("Add another issue?")
        if not loop:
            break  

if __name__ == "__main__":
    app()
    