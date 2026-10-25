"""
Persistent Auto-Reconnecting Public Tunnel Runner for Energy-to-CO2 Engine
Connects via SSH to localhost.run with keepalive and automatic reconnection on reset.
Saves the active public HTTPS link to live_url.txt.
"""
import subprocess
import time
import re
import sys

def run_tunnel():
    cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ServerAliveInterval=15",
        "-o", "ServerAliveCountMax=3",
        "-R", "80:127.0.0.1:8000",
        "nokey@localhost.run"
    ]
    
    while True:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Launching SSH tunnel to localhost.run...", flush=True)
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in iter(proc.stdout.readline, ""):
                sys.stdout.write(line)
                sys.stdout.flush()
                if "tunneled with tls termination" in line or ".lhr.life" in line:
                    match = re.search(r"https://[a-zA-Z0-9]+\.lhr\.life", line)
                    if match:
                        url = match.group(0).rstrip(".")
                        print(f"\n[ACTIVE_PUBLIC_URL]: {url}\n", flush=True)
                        with open("live_url.txt", "w", encoding="utf-8") as f:
                            f.write(url)
                            
            proc.wait()
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Tunnel disconnected (exit code {proc.returncode}). Reconnecting in 3 seconds...", flush=True)
        except Exception as e:
            print(f"Tunnel runner exception: {e}. Retrying in 5 seconds...", flush=True)
            time.sleep(5)
            
        time.sleep(3)

if __name__ == "__main__":
    run_tunnel()
