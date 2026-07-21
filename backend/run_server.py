"""Helper to daemonize the FastAPI server so a foreground terminal call can
return immediately while the server keeps running in its own session."""
import os
import sys
import subprocess

ENV = {**os.environ, "MOCK": "true"}
# Prefer an in-repo venv, fall back to the system python.
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(_REPO, ".venv", "bin", "python")
if not os.path.exists(PY):
    PY = sys.executable

pid = os.fork()
if pid == 0:
    # child
    os.setsid()
    # detach from stdin/stdout/stderr
    sys.stdout.flush()
    sys.stderr.flush()
    devnull = open("/dev/null", "r")
    log = open("/tmp/dash_backend.log", "a")
    os.dup2(devnull.fileno(), 0)
    os.dup2(log.fileno(), 1)
    os.dup2(log.fileno(), 2)
    os.execve(
        PY,
        [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"],
        ENV,
    )
    os._exit(127)
else:
    # parent
    print(f"server detached pid={pid}")
    # write pidfile for easy cleanup
    with open("/tmp/dash_backend.pid", "w") as f:
        f.write(str(pid))