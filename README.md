# Template 1: Simple One-Click MVP

**Rating: 9.4/10 for simplicity · 8.3/10 effectiveness · Recommended first deployment**

One container, one dashboard, lead CRUD, starter lead scoring, email/WhatsApp drafts, and human approval status. SQLite works locally. PostgreSQL works by adding `DATABASE_URL`.

## Local Windows
1. Install Python 3.11+ or Docker Desktop.
2. Double-click `START_LOCAL_WINDOWS.bat`, or run Docker commands below.
3. Open http://localhost:8000.

```powershell
docker build -t shire-ai-os .
docker run -p 8000:8000 -v ${PWD}/data:/app/data shire-ai-os
```

## Railway
1. Create a private GitHub repository and upload this folder's files.
2. Railway > New Project > Deploy from GitHub.
3. Add PostgreSQL service.
4. In app Variables, add `DATABASE_URL` using PostgreSQL's provided variable/reference.
5. Deploy and open `/health`.

No message is sent automatically. All generated drafts are marked `READY_FOR_REVIEW`.
