import logging
import asyncio
import re
from pathlib import Path
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.error import BadRequest

from aria.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import aria.memory as memory
from aria.assistant import execute_assistant_task
from aria.builder import build_agent
from aria.companion import Companion
from aria.logging_setup import configure_root_logging

# Configure root logging through the shared setup (ARIA_LOG_LEVEL respected)
configure_root_logging()
logger = logging.getLogger(__name__)


# A single Companion instance lives for the life of the bot process.
companion = Companion()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a greeting message and lists pending tasks."""
    profile = memory.get_profile()
    name = profile.get("name", "Mehedi")
    role = profile.get("role", "Researcher")
    
    welcome_text = (
        f"🤖 <b>Hey {name}! I am ARIA, your personal assistant and agent builder.</b>\n\n"
        f"<b>Role:</b> {role}\n\n"
        f"Send me any task to research, outline, write, or type <i>'build me an agent that...'</i> to generate python projects.\n\n"
        f"<b>Available Commands:</b>\n"
        f"/tasks - Manage active tasks\n"
        f"/profile - View user profile details\n"
        f"/agents - View index of built agents\n"
        f"/help - Show command options"
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML")
    
    # List task summary
    tasks = memory.get_tasks()
    active_tasks = [t for t in tasks if t["status"] in ("pending", "in_progress")]
    if active_tasks:
        tasks_list = "\n".join([f"• [{t['status'].upper()}] #{t['id']}: {t['description']}" for t in active_tasks])
        await update.message.reply_text(f"📝 <b>Active Tasks Summary:</b>\n{tasks_list}", parse_mode="HTML")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends help instructions."""
    help_text = (
        "🤖 <b>ARIA Telegram Command Reference:</b>\n\n"
        "<b>Quick meta commands:</b>\n"
        "/notes — show everything I remember about you\n"
        "/note &lt;key&gt;: &lt;value&gt; — remember a fact\n"
        "/forget &lt;key&gt; — drop a fact\n"
        "/jobs — list scheduled jobs\n"
        "/job &lt;name&gt; | &lt;cron&gt; | &lt;prompt&gt; — schedule a recurring task\n"
        "/jobon &lt;id&gt; / /joboff &lt;id&gt; / /jobdel &lt;id&gt;\n"
        "/build &lt;desc&gt; — build a new agent (also triggered by 'build me an agent...')\n\n"
        "<b>Task + profile:</b>\n"
        "/tasks — Lists all tasks\n"
        "/tasks_add &lt;desc&gt; — Adds a task\n"
        "/tasks_status &lt;id&gt; &lt;status&gt; — Updates task status (pending / in_progress / completed)\n"
        "/profile — Displays your user profile\n"
        "/agents — Lists generated agents\n"
        "/clear — Clears chat memory\n"
        "/help — Displays this menu"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")

async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays user profile details."""
    profile = memory.get_profile()
    profile_text = "👤 <b>User Profile Information:</b>\n\n"
    for k, v in profile.items():
        profile_text += f"• <b>{k.replace('_', ' ').title()}:</b> {v}\n"
    await update.message.reply_text(profile_text, parse_mode="HTML")

async def list_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists generated agents."""
    agents = memory.get_built_agents()
    if not agents:
        await update.message.reply_text("📁 No agents built yet. Message me 'build me an agent that...' to create one!")
        return
        
    agents_text = "📁 <b>Built Agents Directory:</b>\n\n"
    for a in agents:
        agents_text += f"• <b>{a['name']}</b>: {a['description']}\n  <i>Path:</i> {a['path']}\n\n"
    await update.message.reply_text(agents_text, parse_mode="HTML")

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all tasks."""
    tasks = memory.get_tasks()
    if not tasks:
        await update.message.reply_text("📝 Your task list is empty.")
        return
        
    tasks_text = "📝 <b>ARIA Task List:</b>\n\n"
    for t in tasks:
        status_emoji = "⏳" if t["status"] == "pending" else ("⚡" if t["status"] == "in_progress" else "✅")
        tasks_text += f"{status_emoji} <b>#{t['id']}</b>: {t['description']} ({t['status']})\n"
    await update.message.reply_text(tasks_text, parse_mode="HTML")

async def add_task_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adds a task."""
    desc = " ".join(context.args)
    if not desc:
        await update.message.reply_text("Usage: /tasks_add <task description>")
        return
    task_id = memory.add_task(desc)
    await update.message.reply_text(f"✅ Added task #{task_id}: {desc}")

async def status_task_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Updates task status."""
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /tasks_status <id> <pending|in_progress|completed>")
        return
    try:
        task_id = int(context.args[0])
        status = context.args[1].lower()
        if status not in ("pending", "in_progress", "completed"):
            await update.message.reply_text("Invalid status. Choose pending, in_progress, or completed.")
            return
        memory.update_task_status(task_id, status)
        await update.message.reply_text(f"✅ Updated task #{task_id} status to '{status}'.")
    except ValueError:
        await update.message.reply_text("Task ID must be an integer.")

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clears SQLite chat history."""
    memory.clear_conversation_history()
    await update.message.reply_text("✅ Chat history cleared.")

async def _safe_reply(update: Update, text: str, **kwargs):
    """reply_text wrapper that degrades gracefully on BadRequest."""
    try:
        await update.message.reply_text(text, **kwargs)
    except BadRequest as exc:
        logger.warning("reply_text failed (%s); retrying without parse_mode", exc)
        kwargs.pop("parse_mode", None)
        await update.message.reply_text(text, **kwargs)


async def _maybe_send_zip(update: Update, context: ContextTypes.DEFAULT_TYPE, response: str):
    """If the response mentions a built_agents zip, send the file too."""
    zip_match = re.search(r"file://([^\s\)]+\.zip)", response)
    if not zip_match:
        return
    zip_path = Path(zip_match.group(1))
    if not zip_path.exists():
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="upload_document")
    with open(zip_path, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename=zip_path.name,
            caption=f"📦 Agent Package: {zip_path.stem}"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Single entry point — hands the message to the Companion brain."""
    user_input = update.message.text
    chat_id = update.effective_chat.id

    # Typing indicator while we think
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        response = await companion.reply(user_input)
    except Exception as exc:
        logger.exception("Companion reply failed")
        await _safe_reply(update, f"⚠️ Error: {exc}")
        return

    # Default to plain text — the LLM output may contain stray * or _ that
    # would break Markdown parsing. Only switch to HTML if it looks safe.
    parse_mode = None
    if response.startswith("<") and "</" in response:
        parse_mode = "HTML"

    await _safe_reply(update, response, parse_mode=parse_mode)
    await _maybe_send_zip(update, context, response)


async def job_tick_callback(context: ContextTypes.DEFAULT_TYPE):
    """JobQueue callback — fires every 60s and runs any due companion jobs."""
    from datetime import datetime
    fired = await companion.tick(datetime.now())
    if not fired:
        return
    chat_id = TELEGRAM_CHAT_ID
    if not chat_id:
        logger.warning("Job fired but TELEGRAM_CHAT_ID unset: %s", fired)
        return
    for name, prompt in fired:
        try:
            reply_text = await companion.reply(prompt)
        except Exception as exc:
            logger.exception("Job %s failed: %s", name, exc)
            continue
        try:
            await context.bot.send_message(chat_id=int(chat_id), text=f"⏰ {name}\n\n{reply_text}")
        except (BadRequest, ValueError) as exc:
            logger.warning("Failed to deliver job output: %s", exc)

def run_telegram_bot():
    """Initializes and runs the Telegram Bot application in polling mode."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not configured in environment.", flush=True)
        return

    memory.init_db()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", view_profile))
    app.add_handler(CommandHandler("agents", list_agents))
    app.add_handler(CommandHandler("tasks", list_tasks))
    app.add_handler(CommandHandler("tasks_add", add_task_cmd))
    app.add_handler(CommandHandler("tasks_status", status_task_cmd))
    app.add_handler(CommandHandler("clear", clear_history))
    # Companion slash commands
    app.add_handler(CommandHandler("notes", lambda u, c: handle_message(u, c)))
    app.add_handler(CommandHandler("note", lambda u, c: handle_message(u, c)))
    app.add_handler(CommandHandler("forget", lambda u, c: handle_message(u, c)))
    app.add_handler(CommandHandler("jobs", lambda u, c: handle_message(u, c)))
    app.add_handler(CommandHandler("job", lambda u, c: handle_message(u, c)))
    app.add_handler(CommandHandler("jobon", lambda u, c: handle_message(u, c)))
    app.add_handler(CommandHandler("joboff", lambda u, c: handle_message(u, c)))
    app.add_handler(CommandHandler("jobdel", lambda u, c: handle_message(u, c)))
    app.add_handler(CommandHandler("build", lambda u, c: handle_message(u, c)))

    # Message handler for normal text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # 60-second tick for scheduled companion jobs.
    app.job_queue.run_repeating(job_tick_callback, interval=60, first=10)

    print("ARIA Telegram Bot listening... (companion + job tick active)", flush=True)
    app.run_polling()

if __name__ == "__main__":
    run_telegram_bot()
