import typer
import requests
import uuid
import time
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

app = typer.Typer(help="AICIPC Command Line Interface")
console = Console()
API_BASE = "http://localhost:8000/api/v1"
API_KEY = "aicipc-secret-2026"
HEADERS = {"X-API-KEY": API_KEY}

@app.command()
def list_agents():
    """List all registered Rack Manager Agents"""
    try:
        resp = requests.get(f"{API_BASE}/agents")
        agents = resp.json()
        
        table = Table(title="Registered Rack Managers")
        table.add_column("Rack ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("IP Address")
        table.add_column("DUTs")
        table.add_column("Last Seen")

        for data in agents:
            table.add_row(
                data["rack_id"], 
                data["status"], 
                data["ip_address"], 
                str(data["dut_count"]),
                data["last_seen"]
            )
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

@app.command()
def deploy(
    rack_id: str, 
    action: str = "OS_INSTALL", 
    dut_id: str = "DUT-01", 
    model: str = "default",
    overheat: bool = False
):
    """Deploy a task to a specific Rack/DUT with optional model and overheat simulation"""
    task_id = f"cli-{uuid.uuid4().hex[:8]}"
    params = {"model": model}
    if overheat:
        params["simulate_overheat"] = "true"
        
    payload = {
        "task_id": task_id,
        "rack_id": rack_id,
        "dut_id": dut_id,
        "action": action,
        "params": params
    }
    
    try:
        resp = requests.post(f"{API_BASE}/tasks", json=payload, headers=HEADERS)
        resp.raise_for_status()
        console.print(f"[green]SUCCESS:[/green] Task {task_id} submitted.")
        
        # Monitor progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task_bar = progress.add_task(f"Executing {action}...", total=100)
            
            while not progress.finished:
                status_resp = requests.get(f"{API_BASE}/tasks/{task_id}")
                status_data = status_resp.json()
                
                progress.update(task_bar, completed=status_data["progress"], description=status_data["message"])
                
                if status_data["status"] in ["SUCCESS", "FAILED"]:
                    break
                
                time.sleep(1)
                
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")

if __name__ == "__main__":
    app()
