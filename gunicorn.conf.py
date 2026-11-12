"""Gunicorn settings for the BIIN production service.

Nginx owns the client connections. Gunicorn deliberately handles a much
smaller bounded set of active Django requests so 500 idle/slow clients do not
turn into 500 Python processes or database connections.
"""

bind = "unix:/run/biin/gunicorn.sock"
umask = 0o007
backlog = 512

# Sized for a service capped at two CPU cores and 1 GiB RAM.
workers = 3
worker_class = "gthread"
threads = 8

# The remove-background integration can wait up to 45 seconds.
timeout = 60
graceful_timeout = 30
keepalive = 5

# Recycle workers gradually to bound damage from slow memory growth.
max_requests = 1200
max_requests_jitter = 120

# Nginx writes the access log; duplicate Gunicorn access logging wastes I/O.
accesslog = None
errorlog = "-"
loglevel = "info"
capture_output = True

preload_app = True
