# docker/gunicorn.conf.py
import multiprocessing
import os

# ── Workers ───────────────────────────────────────────────────────────
# Formula: (2 × CPU cores) + 1 — standard for I/O-bound async apps
workers     = int(os.getenv("WEB_CONCURRENCY", (2 * multiprocessing.cpu_count()) + 1))
worker_class = "uvicorn.workers.UvicornWorker"
threads      = 1          # UvicornWorker is async — no thread needed per worker

# ── Binding ───────────────────────────────────────────────────────────
bind    = "0.0.0.0:8000"
backlog = 2048

# ── Timeouts ─────────────────────────────────────────────────────────
timeout          = 120    # worker silent for 120s → killed and replaced
graceful_timeout = 30     # seconds to finish in-flight requests on shutdown
keepalive        = 5      # seconds to wait for next request on a kept-alive conn

# ── Logging ──────────────────────────────────────────────────────────
accesslog  = "-"          # stdout
errorlog   = "-"          # stderr
loglevel   = os.getenv("LOG_LEVEL", "warning").lower()
access_log_format = (
    '{"time":"%(t)s","method":"%(m)s","path":"%(U)s",'
    '"status":%(s)s,"duration_ms":%(D)s,"pid":%(p)s}'
)

# ── Process naming ────────────────────────────────────────────────────
proc_name = "import-logistics"

# ── Security ─────────────────────────────────────────────────────────
limit_request_line    = 4094
limit_request_fields  = 100
limit_request_field_size = 8190

# ── Server hooks ─────────────────────────────────────────────────────
def on_starting(server):
    server.log.info("Gunicorn starting — workers=%d", workers)

def worker_exit(server, worker):
    server.log.info("Worker exited: pid=%d", worker.pid)