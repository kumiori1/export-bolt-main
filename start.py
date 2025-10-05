#!/usr/bin/env python3
"""
Process manager to run both FastAPI server and ARQ worker
"""
import os
import sys
import asyncio
import signal
import subprocess
from multiprocessing import Process
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_server():
    """Run the FastAPI server"""
    logger.info("Starting FastAPI server...")
    port = int(os.getenv("PORT", "8000"))
    
    # Import and run uvicorn
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        workers=1,
        log_level="info"
    )

def run_worker():
    """Run the ARQ worker"""
    logger.info("Starting ARQ worker...")
    
    # Import and run ARQ worker
    from arq import run_worker
    from app.worker import WorkerSettings
    
    run_worker(WorkerSettings)

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("Starting both FastAPI server and ARQ worker...")
    
    # Create processes for both server and worker
    server_process = Process(target=run_server)
    worker_process = Process(target=run_worker)
    
    try:
        # Start both processes
        server_process.start()
        worker_process.start()
        
        logger.info("Both server and worker started successfully!")
        logger.info(f"Server PID: {server_process.pid}")
        logger.info(f"Worker PID: {worker_process.pid}")
        
        # Wait for both processes
        server_process.join()
        worker_process.join()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        
        # Terminate both processes
        if server_process.is_alive():
            server_process.terminate()
            server_process.join()
            
        if worker_process.is_alive():
            worker_process.terminate()
            worker_process.join()
            
        logger.info("Shutdown complete")