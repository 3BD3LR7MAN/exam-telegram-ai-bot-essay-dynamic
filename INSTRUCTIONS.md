# Installation and Operations Instructions

## 1. Scope and tested configuration

This project is an n8n workflow for an Arabic essay exam delivered through Telegram. The workflow reads question text and model answers from Google Sheets, stores progress by Telegram user ID, and submits completed answers to Google Gemini for grading.

The sanitized template reflects the corrected workflow configuration as of **2026-11-18**. The production spreadsheet URL, spreadsheet ID, sheet IDs, credential references, workflow IDs, and webhook-specific identifiers have been removed. The live deployment that informed this template used one active corrected workflow and kept a duplicate/legacy workflow inactive. Do not activate two workflows that use the same Telegram bot token at the same time.

## 2. Requirements

- An n8n instance with Telegram, Google Sheets, and Google Gemini nodes available. Node versions can differ between n8n installations; inspect the imported workflow for node compatibility before activation.
- A Telegram bot created with BotFather. Keep its token only in an n8n Telegram credential.
- A Google spreadsheet accessible to the Google account used by the n8n Google Sheets OAuth2 credential.
- A Google Gemini credential configured in n8n. Keep its API key only in the n8n credential store.
- Two separate Telegram user accounts for a basic concurrency test.

## 3. Google Sheets workbook

Use one workbook for all three tables. Recommended tab names are `Questions`, `Student State`, and `Results`. If your existing state tab has another title, select that exact tab in n8n.

### Questions tab

Required headers, spelled exactly:

| Column | Meaning |
|---|---|
| `id` | Consecutive integer starting at 1; the workflow uses it to find each question. |
| `question` | Question shown to the student. |
| `model_answer` | Reference answer passed to the grader after the exam. |

Do not leave blank rows within the question table. The question IDs must be consecutive, beginning with `1`.

### Student State tab

Required headers:

`user_id`, `current_q`, `answers`, `started_at`, `total_questions`, `max_score`

There should be one state row per Telegram user. `user_id` is the Telegram sender ID (`message.from.id`), not the group/chat ID. The workflow's upsert and update operations match on `user_id`.

### Results tab

Required headers:

`user_id`, `total_score`, `percentage`, `feedback`, `evaluated_at`, `total_questions`, `max_score`, `name`, `username`, `answers_json`

The `answers_json` header must match exactly. Results are appended; they are not automatically deduplicated. Protect this tab because it contains student scores and answer text.

## 4. Credentials and import

1. Create the three credentials in n8n: Telegram Bot, Google Sheets OAuth2, and Google Gemini.
2. Grant the Google account access to the workbook. If n8n reports an invalid or expired authorization grant, reconnect the existing Google Sheets OAuth credential through the n8n UI and complete Google's consent flow.
3. Import `workflow/ExamTelegramAIBot-EssayDynamic.template.json` into n8n.
4. Assign the correct credentials to all relevant nodes. The template intentionally omits credential references.
5. In **every Google Sheets node**, select the same workbook and the correct tab. Replace the spreadsheet placeholders; do not activate the workflow with placeholders.
6. Select each tab from the n8n sheet selector, or enter its numeric `sheetId` in the supported ID mode. Do not type a URL fragment such as `gid=1977210369` as the sheet ID. The API expects the numeric sheet ID itself. A sheet's numeric ID can be found in its Google Sheets URL after `gid=` or in spreadsheet metadata.
7. Check the `Questions` nodes point to the `Questions` tab; state nodes point to `Student State`; and the result node points to `Results`.
8. Check the result column mappings and confirm `answers_json` exists before activation.
9. Save the workflow and run the test plan below before enabling the production Telegram Trigger.

## 5. Student journey and grading

1. A student opens a **private chat** with the bot and sends `/start`.
2. The workflow counts the rows in `Questions`, initializes or replaces only that student's state row, and sends question 1.
3. Each answer is stored under that student's `user_id`; the workflow updates `current_q` and sends the next question.
4. After the last answer, the workflow reads the model answers, merges them with that student's saved answers, and asks Gemini to return JSON containing `total`, `percentage`, and Arabic feedback.
5. The parser clamps `total` to the valid range from zero to `max_score`, calculates the percentage itself, and constructs `answers_json`.
6. The workflow appends the result to `Results` and sends the score and feedback to the incoming chat.

The grading prompt assigns 0–10 points per question, so `max_score` is `number_of_questions × 10`. The model's percentage field is not trusted; the workflow recalculates it from the clamped total.

Sending `/start` again initializes that student's state again. Explain this restart behavior before giving students access; it can replace the in-progress attempt for that student.

### Student commands and message types

- `/start` begins or restarts an attempt. `/start@your_bot` also works when Telegram includes the bot mention.
- `/help` shows the short Arabic student instructions.
- `/cancel` does not delete state; it explains how to restart safely. This avoids an accidental destructive action.
- Unknown slash commands show the help message and are not stored as exam answers.
- Only text messages are accepted as answers. Photos, stickers, voice notes, and other unsupported updates receive a reminder instead of becoming blank answers.
- Questions are sent as plain text without Markdown parsing, so punctuation and formatting in the question cannot cause Telegram parse errors.

## 6. Multi-student use and concurrency

The workflow separates different students by `message.from.id` and uses that value as `user_id` for state reads, upserts, and updates. There is no shared AI memory node. Separate private chats can therefore run concurrently without intentionally sharing a student's answer state.

Do not use one shared group chat for an exam. Replies are sent to the incoming Telegram `chat.id`; in a group, everyone can see the questions, answers, and bot responses even though state rows are keyed by individual sender IDs.

Google Sheets does not provide the transaction/locking guarantees of a database. A large burst can hit Google Sheets quotas, and two rapid messages from the same student can race while both executions read and update the same row. For a classroom-scale pilot, test with multiple accounts and watch n8n executions. For sustained or heavy concurrency, move state and results to PostgreSQL (or another transactional database), add a queue, and serialize updates per `user_id`.

The Google Gemini Chat Model node is configured to retry on failure up to **3 attempts total**, waiting **5 seconds** between attempts. This adds up to about 10 seconds before a final failure. It helps with transient model service errors but does not solve a prolonged provider outage or Google Sheets throttling.

## 7. Test plan before production

Use a test workbook and two separate private Telegram accounts. Do not use real student records during the test.

1. Start both accounts with `/start` and confirm each receives question 1.
2. Answer in interleaved order (Account A, then B, then A, then B). Confirm that each response advances only that account's state.
3. Inspect `Student State` and confirm two distinct `user_id` rows with no crossed answers.
4. Complete both attempts. Confirm each account receives its own final score and the `Results` tab gets one row per completed attempt.
5. Confirm each `answers_json` value corresponds to the same `user_id` in that row. Do not paste student answer content into issue reports or public logs.
6. Send a message before `/start`, send `/start` again during an attempt, and send an extra answer after completion; verify the expected guard messages.
7. Review n8n execution statuses and node errors. A successful execution should include `Save Results` and `Send Final Result`.

## 8. Activation, rollback, and recovery

- Keep only one workflow with a Telegram Trigger using a given bot token active. A legacy and corrected workflow may conflict over Telegram's webhook.
- Before switching workflow versions, record which one is active. Deactivate the current workflow, activate the intended workflow, then verify the status in n8n.
- Existing per-student state lives in Google Sheets, so a brief workflow pause does not itself delete it. Messages sent during the pause may not be processed; ask students not to submit during maintenance.
- If a test fails, inspect the failed execution's node name and error. Avoid copying execution payloads containing student answers into GitHub issues.
- For an OAuth invalid-grant error, reconnect the Google credential in n8n. For a sheet-not-found error, reselect the tab and verify its numeric `sheetId`. For Gemini `Service unavailable`, allow the configured retries, then check Google Gemini service status, quota, and credential configuration.
- Do not clear the `Student State` or `Results` tabs as a generic troubleshooting step. Remove only a known test row after confirming its `user_id` and obtaining permission.

## 9. Security and GitHub publishing

The workflow template is sanitized and contains placeholders. Before publishing:

- Never commit Telegram bot tokens, Gemini API keys, OAuth refresh tokens, service-account JSON, live workflow credentials, real spreadsheet IDs/URLs, student names, usernames, scores, answers, or n8n execution exports.
- Keep secrets in n8n credentials or a protected secrets manager.
- Use a separate test spreadsheet and test bot when developing.
- Restrict workbook access to people who need it; `Results` contains personal and educational data.
- Review the final Git diff and search for `REPLACE_WITH`, `AIza`, `Bearer`, `access_token`, `refresh_token`, and real spreadsheet URLs before pushing.
- The repository does not specify a license. Choose one explicitly before inviting reuse.

See [`SECURITY.md`](SECURITY.md) for additional guidance.
