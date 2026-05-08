"""Fake terminal for simulating command execution in training missions."""

def run_command(command: str) -> str:
    """Simulate running a command and return output."""
    return f"[SIMULATED] Executing: {command}\n[SIMULATED] Output placeholder"

def format_output(output: str) -> str:
    """Format terminal output for display."""
    return f"```terminal\n{output}\n```"
