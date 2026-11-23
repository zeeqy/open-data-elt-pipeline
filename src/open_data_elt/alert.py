"""Telegram failure alert. Called by the scheduled workflow when a step fails.

Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID. Without them it prints the
message and returns False, so a missing secret never hides the real failure.
"""

import os
from pathlib import Path

import requests

MAX_LOG_LINES = 8
TELEGRAM_LIMIT = 4096


def run_url() -> str | None:
    server, repo, run_id = (
        os.environ.get("GITHUB_SERVER_URL"),
        os.environ.get("GITHUB_REPOSITORY"),
        os.environ.get("GITHUB_RUN_ID"),
    )
    return f"{server}/{repo}/actions/runs/{run_id}" if server and repo and run_id else None


def tail(log_path: Path | None, lines: int = MAX_LOG_LINES) -> list[str]:
    """Last lines of the step log that look like the cause, else the last few lines."""
    if not log_path or not log_path.exists():
        return []
    text = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    key = [
        line
        for line in text
        if any(k in line for k in ("FAILED", "ERROR", "Error", "FAIL ", "WARN "))
    ]
    return (key or text)[-lines:]


def build_message(step: str, log_path: Path | None = None) -> str:
    parts = [f"[FAILED] open-data-elt pipeline, step: {step}"]
    detail = tail(log_path)
    if detail:
        parts += ["", *detail]
    url = run_url()
    if url:
        parts += ["", url]
    return "\n".join(parts)[:TELEGRAM_LIMIT]


def send(text: str, session=requests) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Telegram not configured; alert would have been:\n" + text)
        return False
    resp = session.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    if resp.status_code != 200:
        # Never echo the URL: it contains the bot token.
        print(f"Telegram send failed with HTTP {resp.status_code}")
        return False
    return True
