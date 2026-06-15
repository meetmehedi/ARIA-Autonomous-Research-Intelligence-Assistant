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

from aria.config import TELEGRAM_BOT_TOKEN
import aria.memory as memory
from aria.assistant import execute_assistant_task
from aria.builder import build_agent

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
        "/tasks - Lists all tasks\n"
        "/tasks_add &lt;desc&gt; - Adds a task\n"
        "/tasks_status &lt;id&gt; &lt;status&gt; - Updates task status (pending/in_progress/completed)\n"
        "/profile - Displays your user profile\n"
        "/agents - Lists generated agents\n"
        "/clear - Clears chat memory\n"
        "/help - Displays this menu"
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes message input via LLM, routing to Builder or ReAct Assistant."""
    user_input = update.message.text
    chat_id = update.effective_chat.id
    
    # Notify user that bot is typing/thinking
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # Retrieve conversation logs
    history = memory.get_conversation_history(20)
    
    try:
        # Check if Builder Request
        is_builder_request = any(phrase in user_input.lower() for phrase in [
            "build me an agent", "build an agent", "create an agent", 
            "make me an agent", "generate an agent", "build a chatbot"
        ])
        
        if is_builder_request:
            # Generate code using Builder
            response = build_agent(user_input)
            
            # Save conversation
            memory.add_conversation_message("user", user_input)
            memory.add_conversation_message("aria", response)
            
            # Send textual report
            await update.message.reply_text(response, parse_mode="Markdown")
            
            # Search for zip file links in response to upload directly!
            # Pattern matches something like file:///Users/.../built_agents/agent_name.zip
            match = re.search(r"file://([^\s\)]+\.zip)", response)
            if match:
                zip_path = Path(match.group(1))
                if zip_path.exists():
                    await context.bot.send_chat_action(chat_id=chat_id, action="upload_document")
                    with open(zip_path, "rb") as f:
                        await update.message.reply_document(
                            document=f,
                            filename=zip_path.name,
                            caption=f"📦 Agent Package: {zip_path.stem}"
                        )
        else:
            # Route to ReAct Assistant
            response = execute_assistant_task(user_input, history)
            
            # Save conversation
            memory.add_conversation_message("user", user_input)
            memory.add_conversation_message("aria", response)
            
            await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text(f"⚠️ Error executing request: {e}")

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
    
    # Message handler for normal text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("ARIA Telegram Bot listening...", flush=True)
    app.run_polling()

if __name__ == "__main__":
    run_telegram_bot()
