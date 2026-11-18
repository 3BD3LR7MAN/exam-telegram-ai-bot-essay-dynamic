#!/usr/bin/env python3
"""Apply safe, deterministic UX improvements to the sanitized n8n template."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "workflow" / "ExamTelegramAIBot-EssayDynamic.template.json"


def node(name: str):
    return next(n for n in data["nodes"] if n["name"] == name)


def set_text(name: str, text: str) -> None:
    node(name)["parameters"]["text"] = text


data = json.loads(PATH.read_text(encoding="utf-8"))

# Normalize Telegram input once so commands work with /start@bot, whitespace,
# and mixed case, while media/stickers are never treated as exam answers.
normalizer = {
    "parameters": {
        "jsCode": """const message = $json.message || {};
const text = typeof message.text === 'string' ? message.text : '';
const trimmed = text.trim();
const firstToken = trimmed.split(/\\s+/, 1)[0].toLowerCase();
const command = firstToken.startsWith('/') ? firstToken.split('@', 1)[0] : '';
const knownCommands = new Set(['/start', '/help', '/cancel']);
const route = !text ? '__unsupported__' : (command ? (knownCommands.has(command) ? command : '__unknown_command__') : '__answer__');
return { json: { ...$json, command: route, normalized_text: text } };""",
        "mode": "runOnceForEachItem",
    },
    "id": "normalize-incoming-message",
    "name": "Normalize Incoming Message",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [-760, 80],
}

# Replace an existing node if this script is run more than once.
data["nodes"] = [n for n in data["nodes"] if n["name"] != normalizer["name"]]
data["nodes"].append(normalizer)

switch = node("Switch")
switch["parameters"] = {
    "dataType": "string",
    "value1": "={{ $json.command }}",
    "rules": {
        "rules": [
            {"value2": "/start"},
            {"value2": "/help"},
            {"value2": "/cancel"},
            {"value2": "__answer__"},
            {"value2": "__unsupported__"},
            {"value2": "__unknown_command__"},
        ]
    },
    "options": {},
}

# Plain text avoids Markdown parse failures and prevents question text from being
# interpreted as formatting. Keep the messages explicit for a student in Arabic.
set_text("Send Question 1", "=السؤال 1 من {{ $('Prepare Initial State').item.json.total_questions }}\n\n{{ $json.question }}\n\nاكتب إجابتك وأرسلها برسالة واحدة.")
node("Send Question 1")["parameters"]["additionalFields"] = {}
set_text("Send Next Question", "=السؤال {{ $('Update State Code').item.json.current_q + 1 }} من {{ $('Update State Code').item.json.total_questions }}\n\n{{ $json.question }}\n\nاكتب إجابتك وأرسلها برسالة واحدة.")
node("Send Next Question")["parameters"]["additionalFields"] = {}

# Add lightweight help and unsupported-message responses.
extra = [
    {
        "parameters": {"chatId": "={{ $('Telegram Trigger').first().json.message.chat.id }}", "text": "تعليمات الامتحان\n\n/start — بدء محاولة جديدة\n/help — عرض هذه التعليمات\n/cancel — إلغاء الرسالة الحالية\n\nأرسل إجابة نصية واحدة لكل سؤال، وانتظر السؤال التالي قبل الإرسال مرة أخرى. استخدم محادثة خاصة مع البوت.", "additionalFields": {}},
        "id": "send-help", "name": "Send Help", "type": "n8n-nodes-base.telegram", "typeVersion": 1, "position": [-360, -260]
    },
    {
        "parameters": {"chatId": "={{ $('Telegram Trigger').first().json.message.chat.id }}", "text": "تم تجاهل الرسالة. أثناء الامتحان أرسل إجابة نصية فقط. أرسل /help لعرض التعليمات أو /start لبدء محاولة جديدة.", "additionalFields": {}},
        "id": "send-unsupported", "name": "Send Unsupported Message", "type": "n8n-nodes-base.telegram", "typeVersion": 1, "position": [-360, 300]
    },
    {
        "parameters": {"chatId": "={{ $('Telegram Trigger').first().json.message.chat.id }}", "text": "لا توجد عملية لإلغائها. لإعادة بدء المحاولة استخدم /start؛ انتبه إلى أن ذلك يستبدل التقدم الحالي.", "additionalFields": {}},
        "id": "send-cancel", "name": "Send Cancel Guidance", "type": "n8n-nodes-base.telegram", "typeVersion": 1, "position": [-360, -120]
    },
]
for extra_node in extra:
    data["nodes"] = [n for n in data["nodes"] if n["name"] != extra_node["name"]]
    data["nodes"].append(extra_node)

# Rebuild only the affected edges; preserve all other workflow connections.
connections = data["connections"]
connections["Telegram Trigger"] = {"main": [[{"node": "Normalize Incoming Message", "type": "main", "index": 0}]]}
connections["Normalize Incoming Message"] = {"main": [[{"node": "Switch", "type": "main", "index": 0}]]}
connections["Switch"] = {"main": [
    [{"node": "Get Total Questions", "type": "main", "index": 0}],
    [{"node": "Send Help", "type": "main", "index": 0}],
    [{"node": "Send Cancel Guidance", "type": "main", "index": 0}],
    [{"node": "Get Student State", "type": "main", "index": 0}],
    [{"node": "Send Unsupported Message", "type": "main", "index": 0}],
    [{"node": "Send Help", "type": "main", "index": 0}],
]}

# Add a small explanatory note to the workflow canvas.
sticky = node("Sticky Note")
sticky["parameters"]["content"] += "\\n\\nUX safeguards: commands accept /command@bot and surrounding whitespace; unsupported media is ignored; Telegram output uses plain text to avoid Markdown injection/parse errors."

PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Updated {PATH}")
