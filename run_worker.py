#!/usr/bin/env python
"""
Start rq workers to process annotation queue jobs.

Run this in a SEPARATE terminal from the FastAPI server:
    python run_worker.py

For production, run multiple workers:
    rq worker annotations reviews default --url redis://localhost:6379

Workers listen on all three queues: annotations, reviews, default.
"""
import os
import sys
import logging
import argparse

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Start the rq worker."""
    from redis import Redis
    from rq import Worker, Queue
    from app.core.config import settings
    
    # Queues to listen on (in priority order)
    LISTEN_QUEUES = ["annotations", "reviews", "default"]
    
    parser = argparse.ArgumentParser(description="Start rq worker for annotation tasks")
    parser.add_argument(
        "--queues", "-q",
        nargs="+",
        default=LISTEN_QUEUES,
        help=f"Queues to listen on (default: {' '.join(LISTEN_QUEUES)})"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"Starting rq worker")
    logger.info(f"Redis URL: {settings.REDIS_URL}")
    logger.info(f"Queues: {args.queues}")
    
    try:
        redis_conn = Redis.from_url(settings.REDIS_URL)
        
        # Test connection
        redis_conn.ping()
        logger.info("Redis connection successful")
        
        # Create queues
        queues = [Queue(name, connection=redis_conn) for name in args.queues]
        
        # Create and start worker
        worker = Worker(queues, connection=redis_conn)
        logger.info(f"Worker started, listening on: {args.queues}")
        
        # Start processing (blocking)
        worker.work(with_scheduler=True)
        
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()