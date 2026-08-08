import os
import subprocess
import sys

def main():
    port = int(os.environ.get("PORT", 10000))
    host = os.environ.get("HOST", "0.0.0.0")

    # Ensure upload/output dirs exist on ephemeral filesystem
    for d in [
        os.environ.get("UPLOADS_DIR", "/tmp/uploads"),
        os.environ.get("OUTPUT_DIR", "/tmp/output"),
    ]:
        os.makedirs(d, exist_ok=True)

    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", host,
        "--port", str(port),
        "--workers", "1",
        "--timeout-keep-alive", "120",
    ]
    print(f"[startup] Starting Navik Voiceover backend on {host}:{port}", flush=True)
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
