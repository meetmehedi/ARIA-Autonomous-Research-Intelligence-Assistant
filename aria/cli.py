import sys
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.text import Text
from rich.prompt import Prompt

import aria.memory as memory

from aria.config import LLM_PROVIDER
from aria.rl_agent import execute_rl_agent

console = Console()

BANNER = """
 █████╗ ██████╗ ██╗ █████╗ 
██╔══██╗██╔══██╗██║██╔══██╗
███████║██████╔╝██║███████║
██╔══██║██╔══██╗██║██╔══██║
██║  ██║██║  ██║██║██║  ██║
╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
"""

def show_welcome():
    """Prints a beautiful banner and status summary on startup."""
    # Print logo
    console.print(Panel(
        Text(BANNER, style="bold cyan", justify="center"),
        subtitle="[bold white]Autonomous Research & Intelligence Assistant[/bold white]",
        subtitle_align="center",
        border_style="cyan"
    ))
    
    # Init DB
    memory.init_db()
    
    # Load profile details
    profile = memory.get_profile()
    name = profile.get("name", "Mehedi")
    role = profile.get("role", "Researcher")
    
    console.print(f"[bold green]Connected successfully![/bold green] Welcome back, [bold cyan]{name}[/bold cyan] ({role}).")
    console.print(f"Active LLM Provider: [bold yellow]{LLM_PROVIDER.upper()}[/bold yellow]\n")
    
    # Show active tasks
    show_tasks_summary()

def show_tasks_summary():
    """Displays a simple summary table of pending/in-progress tasks."""
    tasks = memory.get_tasks()
    active_tasks = [t for t in tasks if t["status"] in ("pending", "in_progress")]
    
    if not active_tasks:
        console.print("[dim]No active tasks pending. Great job![/dim]\n")
        return
        
    table = Table(title="Pending / Active Tasks", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=4)
    table.add_column("Task Description", style="white")
    table.add_column("Status", style="yellow")
    
    for t in active_tasks:
        status_style = "yellow" if t["status"] == "in_progress" else "red"
        table.add_row(str(t["id"]), t["description"], f"[{status_style}]{t['status']}[/{status_style}]")
        
    console.print(table)
    console.print("[dim]Type [bold cyan]/tasks[/bold cyan] to manage your tasks or add new ones.[/dim]\n")

def handle_tasks_command(args):
    """Handles /tasks subcommand router."""
    if not args:
        # Just list all tasks
        tasks = memory.get_tasks()
        if not tasks:
            console.print("[yellow]Your task list is empty.[/yellow]")
            return
            
        table = Table(title="ARIA Task Manager", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Description")
        table.add_column("Status")
        table.add_column("Created At", style="dim")
        
        for t in tasks:
            status_style = "green" if t["status"] == "completed" else ("yellow" if t["status"] == "in_progress" else "red")
            table.add_row(
                str(t["id"]), 
                t["description"], 
                f"[{status_style}]{t['status']}[/{status_style}]",
                t["created_at"]
            )
        console.print(table)
        console.print("[dim]Usage: /tasks add <desc> | /tasks status <id> <pending|in_progress|completed> | /tasks delete <id>[/dim]")
        return
        
    subcmd = args[0].lower()
    
    if subcmd == "add" and len(args) > 1:
        desc = " ".join(args[1:])
        task_id = memory.add_task(desc)
        console.print(f"[green]Added task #{task_id}:[/green] {desc}")
        
    elif subcmd == "status" and len(args) > 2:
        try:
            task_id = int(args[1])
            status = args[2].lower()
            if status not in ("pending", "in_progress", "completed"):
                console.print("[red]Invalid status. Must be pending, in_progress, or completed.[/red]")
                return
            memory.update_task_status(task_id, status)
            console.print(f"[green]Updated task #{task_id} status to {status}[/green]")
        except ValueError:
            console.print("[red]Task ID must be an integer.[/red]")
            
    elif subcmd == "delete" and len(args) > 1:
        try:
            task_id = int(args[1])
            memory.delete_task(task_id)
            console.print(f"[green]Deleted task #{task_id}[/green]")
        except ValueError:
            console.print("[red]Task ID must be an integer.[/red]")
    else:
        console.print("[red]Unknown subcommand. Use add, status, or delete.[/red]")

def handle_profile_command(args):
    """Handles /profile subcommand router."""
    if not args:
        profile = memory.get_profile()
        table = Table(title="User Profile", show_header=True, header_style="bold cyan")
        table.add_column("Field", style="bold yellow")
        table.add_column("Value")
        
        for k, v in profile.items():
            table.add_row(k.replace("_", " ").title(), v)
            
        console.print(table)
        console.print("[dim]Usage: /profile update <field_name_in_lowercase> <new_value>[/dim]")
        return
        
    subcmd = args[0].lower()
    if subcmd == "update" and len(args) > 2:
        field = args[1].lower()
        value = " ".join(args[2:])
        memory.update_profile_field(field, value)
        console.print(f"[green]Updated profile field '{field}' to:[/green] {value}")
    else:
        console.print("[red]Invalid profile command. Usage: /profile update <field> <value>[/red]")

def handle_agents_command():
    """Lists built agents index."""
    agents = memory.get_built_agents()
    if not agents:
        console.print("[yellow]No agents built yet. Ask ARIA 'build me an agent that...' to create one![/yellow]")
        return
        
    table = Table(title="Built Agents Index", show_header=True, header_style="bold green")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="bold white")
    table.add_column("Description")
    table.add_column("Local Path", style="dim")
    table.add_column("Created At", style="dim")
    
    for a in agents:
        table.add_row(str(a["id"]), a["name"], a["description"], a["path"], a["created_at"])
        
    console.print(table)

def handle_history_command():
    """Prints recent message history."""
    history = memory.get_conversation_history(30)
    if not history:
        console.print("[yellow]No conversation history yet.[/yellow]")
        return
        
    for msg in history:
        role_style = "bold cyan" if msg["role"] == "user" else "bold magenta"
        role_name = "Mehedi" if msg["role"] == "user" else "ARIA"
        console.print(f"[{role_style}]{role_name}:[/{role_style}] {msg['content']}")
        console.print("[dim]----------------------------------------[/dim]")

def print_help():
    """Displays available CLI commands."""
    console.print("\n[bold cyan]Available Commands:[/bold cyan]")
    console.print("  [bold yellow]/help[/bold yellow]          - Display this help message")
    console.print("  [bold yellow]/tasks[/bold yellow]         - List all tasks")
    console.print("  [bold yellow]/tasks add <d>[/bold yellow] - Add a new task")
    console.print("  [bold yellow]/tasks status <id> <st>[/bold yellow] - Change task status (pending, in_progress, completed)")
    console.print("  [bold yellow]/tasks delete <id>[/bold yellow] - Delete a task")
    console.print("  [bold yellow]/profile[/bold yellow]       - View user profile details")
    console.print("  [bold yellow]/profile update <f> <v>[/bold yellow] - Update user profile field")
    console.print("  [bold yellow]/agents[/bold yellow]        - List built agents")
    console.print("  [bold yellow]/history[/bold yellow]       - Display conversation history")
    console.print("  [bold yellow]/clear[/bold yellow]         - Clear conversation history")
    console.print("  [bold yellow]/exit[/bold yellow]          - Exit ARIA CLI\n")

def run_cli():
    """Main execution loop for the terminal interface."""
    show_welcome()
    print_help()
    
    while True:
        try:
            # Styled prompt input
            user_input = Prompt.ask("[bold cyan]Mehedi[/bold cyan]").strip()
            
            if not user_input:
                continue
                
            # Intercept slash command typos (missing slash)
            cleaned_input = user_input.lower().split()[0]
            if cleaned_input in ["help", "tasks", "profile", "agents", "history", "clear", "exit"]:
                console.print(f"[bold yellow]Hint: Did you mean to run a command? Try using: [cyan]/{cleaned_input}[/cyan][/bold yellow]\n")
                continue
                
            # Parse commands
            if user_input.startswith("/"):
                parts = user_input.split()
                cmd = parts[0].lower()
                args = parts[1:]
                
                if cmd == "/exit":
                    console.print("[bold red]Goodbye Mehedi![/bold red]")
                    break
                elif cmd == "/help":
                    print_help()
                elif cmd == "/tasks":
                    handle_tasks_command(args)
                elif cmd == "/profile":
                    handle_profile_command(args)
                elif cmd == "/agents":
                    handle_agents_command()
                elif cmd == "/history":
                    handle_history_command()
                elif cmd == "/clear":
                    memory.clear_conversation_history()
                    console.print("[green]Chat history cleared.[/green]")
                else:
                    console.print(f"[red]Unknown command: {cmd}. Type /help for options.[/red]")
                console.print()
                continue
                
            # Regular interaction: assistant mode query
            console.print("[dim italic]ARIA is thinking...[/dim italic]")
            
            # Fetch context history (last 20 messages)
            history = memory.get_conversation_history(20)
            
            try:
                # Classify request: Agent Builder vs Personal Assistant
                is_builder_request = any(phrase in user_input.lower() for phrase in [
                    "build me an agent", "build an agent", "create an agent", 
                    "make me an agent", "generate an agent", "build a chatbot"
                ])
                
                if is_builder_request:
                    response = asyncio.run(execute_rl_agent(user_input, history=[]))
                else:
                    response = asyncio.run(execute_rl_agent(user_input, history))
                
                # Save conversation
                memory.add_conversation_message("user", user_input)
                memory.add_conversation_message("aria", response)
                
                # Render response
                console.print(Panel(
                    Markdown(response),
                    title="[bold magenta]ARIA[/bold magenta]",
                    title_align="left",
                    border_style="magenta",
                    expand=False
                ))
            except Exception as e:
                err_msg = str(e)
                console.print(f"[bold red]Error executing request:[/bold red] {err_msg}")
                if "invalid_api_key" in err_msg.lower() or "incorrect api key" in err_msg.lower() or "your_openai_api_key_here" in err_msg or "401" in err_msg:
                    console.print("[bold yellow]Hint: It looks like your LLM API keys are not set yet in the .env file. Please open and edit the .env file in the workspace to insert your API key.[/bold yellow]")
                
            console.print()
            
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold red]Goodbye Mehedi![/bold red]")
            break

if __name__ == "__main__":
    run_cli()
