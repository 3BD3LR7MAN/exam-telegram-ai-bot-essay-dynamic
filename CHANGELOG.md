# Changelog

## 2026-11-18 — GitHub-ready documentation package

- Documented import, credentials, workbook schemas, student flow, grading, concurrency, testing, rollback, and troubleshooting.
- Added a sanitized n8n workflow template with the live spreadsheet and credential references removed.
- Documented the corrected numeric sheet-ID requirement and per-student `user_id` state key.
- Added bounded retry settings to the Google Gemini Chat Model node: 3 attempts total, 5 seconds between attempts.
- Recorded the known limits: Google Sheets is not transactional; separate private chats are required; high-volume deployments should use a database and queue.
