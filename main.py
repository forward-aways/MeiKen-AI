"""MeiKen AI — Launcher.

Usage:
    uv run python main.py backend              → FastAPI   http://127.0.0.1:8000
    uv run python main.py backend --reload     → FastAPI with hot-reload
    uv run python main.py frontend             → Frontend  http://127.0.0.1:3000
"""

import os, platform, subprocess, sys


def run_backend():
    reload = "--reload" in sys.argv
    args = [
        sys.executable, "-m", "uvicorn", "backend.main:app",
        "--host", "127.0.0.1", "--port", "8000",
    ]
    if reload:
        args.append("--reload")
    print("Backend  → http://127.0.0.1:8000")
    print("API Docs → http://127.0.0.1:8000/docs\n")
    subprocess.run(args)


def run_frontend():
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    dist_dir = os.path.join(frontend_dir, "dist")
    npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"

    if not os.path.isdir(dist_dir):
        print("Building frontend...")
        subprocess.run([npm_cmd, "install"], cwd=frontend_dir, check=True)
        subprocess.run([npm_cmd, "run", "build"], cwd=frontend_dir, check=True)

    os.chdir(dist_dir)
    print("Frontend → http://127.0.0.1:3000\n")
    subprocess.run([sys.executable, "-m", "http.server", "3000"])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "backend"
    if cmd == "backend":
        run_backend()
    elif cmd == "frontend":
        run_frontend()
    else:
        print("Usage: python main.py [backend|frontend]")
        sys.exit(1)
