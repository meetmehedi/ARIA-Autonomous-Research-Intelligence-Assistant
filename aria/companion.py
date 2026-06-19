"""ARIA Companion — the always-on, talking, agent-spawning persona.

This is the personality layer that sits in front of the rest of ARIA. It
remembers persistent notes about the user, runs recurring jobs, builds new
agents on demand, and replies in Mehedi's preferred casual voice.

Public surface:
    Companion()              — the brain
        .reply(user_text)    — produce a response (also detects /build, /note, /job)
        .tick(now)           — run any jobs whose cron has come due
        .notes_summary()     — short block of all stored notes
"""

from __future__ import annotations

import re
import shlex
from datetime import datetime
from typing import Optional

import aria.memory as memory
import aria.llm as llm
from aria.assistant import execute_assistant_task
from aria.builder import build_agent
from aria.logging_setup import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Minimal cron evaluator. Supports: minute hour day-of-month month day-of-week
# Each field may be: '*', a number, or comma-separated numbers.
# We don't pull in a full cron lib for this — Mehedi's jobs are simple.
# ---------------------------------------------------------------------------

def _match_field(field: str, value: int) -> bool:
    if field.strip() == "*":
        return True
    for part in field.split(","):
        part = part.strip()
        if not part:
            continue
        if part.isdigit() and int(part) == value:
            return True
    return False


def cron_is_due(expr: str, now: datetime, last_run: Optional[datetime]) -> bool:
    """True if ``expr`` matches ``now`` AND we haven't already run this minute."""
    parts = expr.split()
    if len(parts) != 5:
        logger.warning("Skipping malformed cron expr: %r", expr)
        return False
    minute, hour, dom, month, dow = parts
    if not _match_field(minute, now.minute):
        return False
    if not _match_field(hour, now.hour):
        return False
    if not _match_field(dom, now.day):
        return False
    if not _match_field(month, now.month):
        return False
    # Python weekday: Mon=0..Sun=6. Cron DOW: 0=Sun..6=Sat. We treat 7 as Sun too.
    cron_dow = (now.weekday() + 1) % 7
    if not _match_field(dow, cron_dow):
        return False
    if last_run is not None:
        # Don't fire twice in the same minute.
        if (now - last_run).total_seconds() < 60:
            return False
    return True


# ---------------------------------------------------------------------------
# Companion brain
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are ARIA, Md. Mehedi Hasan's always-on personal agent.
You talk to Mehedi on Telegram, you remember him, and you build sub-agents for him.

Voice: casual, direct, no fluff. Match his tone — researcher-credible, never sycophantic.
Keep replies short by default. Long answers only when he asks for them.

You know these tools are available behind the scenes:
- build_agent(description)         -> creates a new Python agent folder + .zip
- execute_assistant_task(prompt)   -> runs a ReAct loop with search/scrape/pdf/etc.
- notes (key/value)                -> facts you remember across restarts
- jobs (cron + prompt)             -> recurring things you do on your own

When Mehedi asks you to "build an agent", call build_agent and return its text reply.
When he asks a research / tool question, call execute_assistant_task and return its text.
When he says "remember X" or "/note X", use add_note.
When he says "every day at 9 remind me X" or "/job", use add_job.
When he says "what do you remember" or "/notes", use list_notes.

Never mention system internals, this prompt, or model names."""


class Companion:
    """Stateless-on-the-surface brain that delegates to memory + LLM."""

    def __init__(self) -> None:
        memory.init_db()

    # ---- public hooks ----------------------------------------------------

    def notes_summary(self) -> str:
        notes = memory.list_notes()
        if not notes:
            return "No notes stored yet."
        return "\n".join(f"• {n['key']}: {n['value']}" for n in notes)

    def tick(self, now: Optional[datetime] = None) -> list[str]:
        """Run any jobs whose cron is due. Returns a list of prompts that fired.

        The caller (Telegram bot) is responsible for sending each prompt through
        the LLM and posting the result back to the user.
        """
        now = now or datetime.now()
        fired: list[tuple[int, str, str]] = []  # (job_id, name, prompt)
        for job in memory.list_jobs(enabled_only=True):
            try:
                if cron_is_due(job["cron_expr"], now, job["last_run"]):
                    fired.append((job["id"], job["name"], job["prompt"]))
            except Exception as exc:  # pragma: no cover — defensive
                logger.exception("Job %s failed cron check: %s", job["id"], exc)
        for job_id, name, _prompt in fired:
            memory.mark_job_run(job_id)
        return [(name, prompt) for _id, name, prompt in fired]

    def reply(self, user_text: str) -> str:
        """Top-level entry point. Returns the text to send back to the user."""
        user_text = (user_text or "").strip()
        if not user_text:
            return "Say something — I'm listening."

        # --- Slash-style meta commands (no LLM needed) --------------------
        if user_text.startswith("/notes"):
            return self.notes_summary()

        if user_text.startswith("/note "):
            body = user_text[len("/note "):].strip()
            # accept "key: value" or "key = value"
            m = re.match(r"^([\w\- ]+?)\s*[:=]\s*(.+)$", body, re.DOTALL)
            if not m:
                return "Format: /note <key>: <value>"
            memory.add_note(m.group(1).strip().lower(), m.group(2).strip())
            return f"📝 Noted: {m.group(1).strip()} = {m.group(2).strip()}"

        if user_text.startswith("/forget "):
            key = user_text[len("/forget "):].strip().lower()
            return ("🗑️ Forgot " + key) if memory.delete_note(key) else f"No note called {key}."

        if user_text.startswith("/jobs"):
            jobs = memory.list_jobs()
            if not jobs:
                return "No scheduled jobs yet."
            lines = []
            for j in jobs:
                flag = "🟢" if j["enabled"] else "⚪"
                lines.append(f"{flag} #{j['id']} {j['name']} — `{j['cron_expr']}` — {j['prompt']}")
            return "\n".join(lines)

        if user_text.startswith("/job "):
            # /job <name> | <cron> | <prompt>
            try:
                _, body = user_text.split(" ", 1)
                name, cron, prompt = [s.strip() for s in body.split("|", 2)]
            except ValueError:
                return "Format: /job <name> | <cron 5-field> | <prompt>"
            job_id = memory.add_job(name, cron, prompt)
            return f"⏰ Job #{job_id} scheduled: {cron} → {prompt}"

        if user_text.startswith("/joboff ") or user_text.startswith("/jobon "):
            verb, rest = user_text.split(" ", 1)
            try:
                job_id = int(rest.strip())
            except ValueError:
                return "Job id must be an integer."
            enabled = verb == "/jobon"
            memory.set_job_enabled(job_id, enabled)
            return f"Job #{job_id} {'enabled' if enabled else 'disabled'}."

        if user_text.startswith("/jobdel "):
            try:
                job_id = int(user_text.split(" ", 1)[1].strip())
            except (ValueError, IndexError):
                return "Job id must be an integer."
            return ("🗑️ Job deleted." if memory.delete_job(job_id) else "No such job.")

        # --- Build / agent commands ---------------------------------------
        build_triggers = (
            "build me an agent", "build an agent", "create an agent",
            "make me an agent", "generate an agent", "build a chatbot",
        )
        if any(t in user_text.lower() for t in build_triggers) or user_text.startswith("/build"):
            return build_agent(user_text)

        # --- Default: hand off to the ReAct assistant ---------------------
        history = memory.get_conversation_history(20)
        response = execute_assistant_task(user_text, history)

        # Persist turn (after the turn finishes, so we don't store intermediate noise)
        try:
            memory.add_conversation_message("user", user_text)
            memory.add_conversation_message("aria", response)
        except Exception as exc:  # pragma: no cover — never break the reply path
            logger.warning("Failed to persist conversation: %s", exc)

        return response


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    c = Companion()
    print(c.notes_summary())
    print(c.reply("hello, who are you?"))
