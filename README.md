# ReportPilot AI - Backend 🚀

This is the refactored 10/10 architecture backend for ReportPilot AI.

## 🌟 Key Features
- **Secure Storage**: Supabase Storage with Signed URLs.
- **Multi-Tenancy**: Strict company-level data isolation using customized Authorization Middleware.
- **Async Processing**: Celery + Redis for heavy OCR tasks (Gemini AI).
- **Observability**: Structured JSON logging and Sentry integration.
- **Testing**: Comprehensive Pytest suite (Unit & Integration).

## 🛠️ Tech Stack
- **Framework**: FastAPI
- **Database**: PostgreSQL (SQLAlchemy)
- **Async Task Queue**: Celery + Redis
- **Auth & Storage**: Supabase
- **AI**: Google Gemini Vision 2.0 Flash

## 🚀 Quick Start (Docker)

1. **Environment Config**
   Create a `.env` file in `backend/` with the following:
   ```env
   DATABASE_URL=postgresql://reportpilot:dev123@postgres:5432/reportpilot
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   SUPABASE_JWT_SECRET=your-jwt-secret
   GEMINI_API_KEY=your-gemini-key
   REDIS_URL=redis://redis:6379/0
   SENTRY_DSN=your-sentry-dsn (optional)
   ENVIRONMENT=development
   ```

2. **Run Services**
   ```bash
   docker-compose up --build
   ```
   This will start:
   - Backend API: http://localhost:8000
   - Celery Worker
   - Redis
   - PostgreSQL

## 🧪 Testing

Run the test suite using pytest:
```bash
# Install test dependencies locally if needed
pip install pytest pytest-cov httpx

# Run tests
pytest
```
*Note: Integration tests require database logic. The provided setup uses in-memory SQLite for tests.*

## 🔒 Security
- **Authentication**: JWT validation via Supabase.
- **Authorization**: All data access is scoped to `company_id`.
- **Validation**: Strict file type and ownership checks.
