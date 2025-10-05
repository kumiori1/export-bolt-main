#!/usr/bin/env python3
"""
Run the ARQ worker for processing tasks
"""
import os
import asyncio
import logging
from arq import run_worker
from app.worker import WorkerSettings
from app.config import get_settings

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get settings to ensure timeout is loaded
settings = get_settings()
logger.info(f"Worker starting with ARQ job timeout: {WorkerSettings.job_timeout} seconds")
logger.info(f"Worker max concurrent jobs: {WorkerSettings.max_jobs}")
logger.info(f"Worker max tries per job: {WorkerSettings.max_tries}")
logger.info(f"Redis URL configured: {'Yes' if os.getenv('REDIS_URL') else 'No (using default)'}")

if __name__ == "__main__":
    run_worker(WorkerSettings)