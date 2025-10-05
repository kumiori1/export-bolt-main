# Environment Variables Structure

## Current .env.example (Template)
```bash
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379/0

API_TITLE=Video Processing Webhook API
API_VERSION=1.0.0
DEBUG=false

MAX_CONCURRENT_TASKS=100
TASK_TIMEOUT=300

# fal.ai Configuration
FAL_KEY=your_fal_key_here

# OpenAI Configuration  
OPENAI_API_KEY=your_openai_api_key_here

# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

## How Environment Variables are Used

### 1. **Configuration Loading** (`app/config.py`)
- Uses `pydantic_settings.BaseSettings`
- Automatically loads from `.env` file
- Provides defaults for development

### 2. **Key Variables Needed**
- **FAL_KEY**: Your fal.ai API key for AI services
- **OPENAI_API_KEY**: OpenAI API key for GPT-4
- **SUPABASE_URL**: Your Supabase project URL
- **SUPABASE_ANON_KEY**: Supabase anonymous key
- **SUPABASE_SERVICE_ROLE_KEY**: Supabase service role key (for backend)
- **REDIS_URL**: Redis connection string

### 3. **Setting Up Environment Variables**

#### For Local Development:
```bash
# Copy the example file
cp .env.example .env

# Edit with your actual values
nano .env
```

#### For Production Deployment:
- Set environment variables in your hosting platform
- Never commit `.env` files to version control
- Use platform-specific environment variable settings

### 4. **Accessing in Code**
```python
from app.config import get_settings

settings = get_settings()
fal_key = settings.fal_key
openai_key = settings.openai_api_key
```

## Security Notes
- `.env` files are in `.gitignore` to prevent accidental commits
- Use different values for development/staging/production
- Rotate API keys regularly
- Never expose service role keys in frontend code