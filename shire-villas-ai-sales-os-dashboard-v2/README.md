# Shire Villas AI Sales OS — Dashboard V2

## Rating
- Simplicity: 9.2/10
- Effectiveness for current MVP: 9.0/10
- Deployment difficulty: 2/10

## What this upgrade adds
- Executive dashboard KPIs
- Pipeline snapshot across 10 sales stages
- Lead-source summary
- Search and filters
- Lead status updates from the dashboard
- Lead scoring
- Email and WhatsApp drafts with human approval status
- Responsive layout
- Existing `/api/leads`, `/health` and PostgreSQL behavior preserved

## Railway upgrade
Replace the files in your existing GitHub repository with all files in this folder. Do not change your Railway PostgreSQL service or `DATABASE_URL` variable. Commit the files. Railway should redeploy automatically.

After deployment test:
- `/health`
- `/`
- `/docs`

No message is sent automatically by this version.
