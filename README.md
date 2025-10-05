# FastAPI Webhook Backend

A high-performance Python FastAPI backend with Redis and ARQ for handling webhook requests and processing video tasks concurrently.

## Features

- **High Concurrency**: Handles 1000+ concurrent requests
- **Webhook Processing**: Extracts and processes webhook data
- **Task Queue**: Uses ARQ (Async Redis Queue) for background processing
- **Redis Integration**: For caching and task management
- **Real-time Status**: Track task processing status
- **Supabase Integration**: Stores scene data in PostgreSQL database
- **Statistics**: Monitor processing metrics

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration including FAL_KEY, OPENAI_API_KEY, and Supabase credentials
```

3. Set up Supabase:
- Create a Supabase project
- Run the migration: The scenes table will be created automatically
- Add your Supabase URL, Anon Key, and Service Role Key to .env

4. Start Redis server (required):
```bash
redis-server
```

## Running the Application

### Start the API Server
```bash
python run_server.py
```

### Start the Worker (in a separate terminal)
```bash
python run_worker.py
```

## API Endpoints

- `POST /webhook` - Main webhook endpoint
- `GET /health` - Health check
- `GET /task/{task_id}` - Get task status
- `GET /stats` - Get processing statistics

## Webhook Data Structure

The webhook endpoint expects data with the following fields:
- `prompt` - The video prompt content
- `image_url` - URL of the product image
- `video_id` - Unique video identifier
- `chat_id` - Chat session ID
- `user_id` - User identifier
- `user_email` - User email
- `user_name` - User name
- `is_revision` - Boolean for revision flag
- `request_timestamp` - Request timestamp
- `source` - Request source
- `version` - API version
- `idempotency_key` - Idempotency key
- `callback_url` - Callback URL
- `webhookUrl` - Webhook URL
- `executionMode` - Execution mode

## Architecture

- **FastAPI**: High-performance async web framework
- **ARQ**: Async task queue using Redis
- **Redis**: In-memory data store for caching and queuing
- **Pydantic**: Data validation and serialization
- **Uvicorn**: ASGI server with optimal performance settings
- **fal.ai**: AI-powered image reframing service

## Performance Configuration

- Multiple workers for horizontal scaling
- Connection pooling for Redis
- Async/await throughout for non-blocking operations
- Optimized for high concurrency workloads