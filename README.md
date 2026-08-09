# Shire Villas AI Sales OS - FINAL Runtime Fix

Fixes Railway runtime error:
`ModuleNotFoundError: No module named 'psycopg2'`

Changes:
- Forces SQLAlchemy to use psycopg v3 with `postgresql+psycopg://`
- Installs `psycopg2-binary` as a compatibility fallback
- Keeps Railway `$PORT` startup
- Keeps existing `DATABASE_URL`

Upload these files directly to the ROOT of the existing GitHub repository.
Do not create a subfolder, new Railway project, or new Postgres database.

Expected health response:
`{"status":"ok","service":"shire-villas-ai-sales-os","version":"2.0.0"}`
