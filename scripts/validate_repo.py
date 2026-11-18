#!/usr/bin/env python3
"""Validate the public, sanitized workflow before import or publication."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow_path = ROOT / "workflow" / "ExamTelegramAIBot-EssayDynamic.template.json"
data = json.loads(workflow_path.read_text(encoding="utf-8"))
nodes = {n["name"]: n for n in data.get("nodes", [])}
required = {
    "Telegram Trigger", "Normalize Incoming Message", "Switch", "Get Total Questions",
    "Get Student State", "Update State Code", "AI Agent", "Save Results",
}
missing = sorted(required - nodes.keys())
if missing:
    raise SystemExit(f"Missing required nodes: {', '.join(missing)}")

switch = nodes["Switch"]["parameters"]
if switch.get("value1") != "={{ $json.command }}":
    raise SystemExit("Switch must route on the normalized command")
expected_routes = {"/start", "/help", "/cancel", "__answer__", "__unsupported__", "__unknown_command__"}
routes = {r.get("value2") for r in switch.get("rules", {}).get("rules", [])}
if routes != expected_routes:
    raise SystemExit(f"Unexpected switch routes: {routes}")

connections = data.get("connections", {})
if connections.get("Telegram Trigger", {}).get("main", [[]])[0][0].get("node") != "Normalize Incoming Message":
    raise SystemExit("Telegram Trigger must feed Normalize Incoming Message")
if len(connections.get("Switch", {}).get("main", [])) != 6:
    raise SystemExit("Switch must have six explicit UX routes")

# Public templates may contain only the documented placeholder, never live keys.
text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts)
patterns = [r"AIza[0-9A-Za-z_-]{20,}", r"Bearer\s+[A-Za-z0-9._-]{20,}", r"gh[pousr]_[A-Za-z0-9_]{20,}", r"https://hooks\.n8n\.cloud/\S+"]
for pattern in patterns:
    if re.search(pattern, text):
        raise SystemExit(f"Possible secret detected: {pattern}")

print("Repository validation passed")
