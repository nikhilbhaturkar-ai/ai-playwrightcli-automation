from typing import Dict
import os
import subprocess

def load_pw_cli_steps_library(filepath: str) -> Dict[str, str]:
    """Reads the text file and parses it into a dictionary."""
    lib = {}
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                # Expecting format: "navigate to google", "npx playwright-cli goto http://google.co.in"
                parts = line.split('","')
                if len(parts) == 2:
                    key = parts[0].strip(' "\n')
                    val = parts[1].strip(' "\n')
                    lib[key] = val
    return lib

def run_cli(command: str) -> str:
    """Executes a shell command and returns True if successful."""
    print(f"Executing: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            out = result.stdout.strip()
            return out 
        else:
            print(f"Command Failed. Error: {result.stderr}")
            return 'Command Failed, Error: ' + result.stderr
    except Exception as e:
        print(f"Execution Exception: {e}")
        return 'Command Failed, Error: ' + str(e)
    
def read_snapshot_file(page_name: str) -> str:
    """Reads the snapshot file and returns its content as a string."""
    snapshot_dir = "snapshots"
    # iterate through the snapshot files from the snapshot/ directory and find the one that matches the page name
    if os.path.isdir(snapshot_dir):
        # try to find a file whose name contains the page_name (case-insensitive)
        for fname in os.listdir(snapshot_dir):
            if page_name.lower() in fname.lower():
                filepath = os.path.join(snapshot_dir, fname)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    print(f"Error reading snapshot file {filepath}: {e}")
                    return ""

    # Fallback: look for a file in the working directory named snapshot_<page_name>.txt
    filepath = f"snapshot_{page_name}.txt"
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading snapshot file {filepath}: {e}")
            return ""

    print(f"Snapshot file not found for page: {page_name}")
    return ""