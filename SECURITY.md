# Security Policy

## Sensitive information

This project handles Telegram identities, student answers, grades, and feedback. Treat the Google Sheets workbook and n8n execution data as confidential educational records.

Never commit:

- Telegram bot tokens or BotFather messages.
- Google OAuth access/refresh tokens, service-account JSON, or credential exports.
- Google Gemini API keys.
- Production spreadsheet IDs/URLs or n8n instance/API keys.
- Student names, usernames, Telegram IDs, answers, scores, results rows, or execution payloads.

Keep credentials in n8n's credential store or a dedicated secrets manager. Use a separate test bot and workbook for development. Apply least-privilege access to the workbook, especially the `Results` tab.

## Reporting issues

Before opening a public GitHub issue, remove personal data and secrets from screenshots, logs, and execution exports. Report only the n8n version, failing node name, a sanitized error message, and reproduction steps. Never attach a raw execution payload containing `answers_json`.

## Repository safety checks

The workflow template omits credential references and replaces spreadsheet references with placeholders. Review every proposed commit and search for common secret patterns and live spreadsheet URLs before publishing. If a secret is accidentally committed, revoke or rotate it immediately; deleting it in a later commit is not sufficient because Git history retains it.
