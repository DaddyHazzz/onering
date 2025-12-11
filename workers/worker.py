# Run this with: rq worker -u redis://localhost:6379 default
# or: python workers/worker.py (which will spin a small worker loop for dev)
import os
import logging
from rq import Worker, Queue, Connection
from redis import Redis
from core.logging import configure_logging

configure_logging()
logger = logging.getLogger("onering")

listen = ['default']

redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
conn = Redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        logger.info("Starting RQ worker (interactive).")
        worker.work()
