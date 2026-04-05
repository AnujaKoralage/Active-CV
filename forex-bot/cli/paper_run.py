import subprocess
import argparse

def run_paper(config_path: str):
    """Alias for run_live.py with --paper flag."""
    subprocess.run(["python3", "cli/run_live.py", "--config", config_path, "--paper"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()
    run_paper(args.config)
