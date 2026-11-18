# Contributing

Thank you for improving the Telegram exam workflow. This repository is intentionally a sanitized n8n template: pull requests must not contain credentials, live spreadsheet identifiers, student data, execution exports, or production webhook URLs.

## Local checks

Run the same check used by GitHub Actions:

```bash
python3 scripts/validate_repo.py
python3 -m json.tool workflow/ExamTelegramAIBot-EssayDynamic.template.json >/dev/null
```

If you change the workflow, update `INSTRUCTIONS.md` and `CHANGELOG.md` when the student journey, sheet schema, import steps, or operational behavior changes. Test with a disposable bot and workbook, using at least two private Telegram accounts. Never paste raw n8n execution payloads into an issue or pull request.

## Pull requests

Explain the user-facing behavior changed, the n8n version tested, and any migration steps. Keep credentials assigned through n8n's credential store rather than embedding them in JSON.
