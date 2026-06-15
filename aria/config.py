import os
from pathlib import Path
from dotenv import load_dotenv

# Find workspace root directory and load .env
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
dotenv_path = WORKSPACE_ROOT / ".env"

if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    # Try current directory fallback
    load_dotenv()

# LLM Config
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

# DB Config
DATABASE_PATH = os.getenv("DATABASE_PATH", "aria_memory.db")
# Resolve database relative to workspace root if it is a relative path
db_path_obj = Path(DATABASE_PATH)
if not db_path_obj.is_absolute():
    DATABASE_PATH = str(WORKSPACE_ROOT / DATABASE_PATH)

# Telegram Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def print_config_summary():
    """Prints a censored/masked summary of config for debugging/verification."""
    print("=== ARIA System Configuration Summary ===")
    print(f"Workspace Root: {WORKSPACE_ROOT}")
    print(f"LLM Provider: {LLM_PROVIDER}")
    print(f"Database Path: {DATABASE_PATH}")
    print(f"OpenAI Key Configured: {'Yes' if OPENAI_API_KEY else 'No'}")
    print(f"Anthropic Key Configured: {'Yes' if ANTHROPIC_API_KEY else 'No'}")
    print(f"Gemini Key Configured: {'Yes' if GEMINI_API_KEY else 'No'}")
    print(f"Telegram Token Configured: {'Yes' if TELEGRAM_BOT_TOKEN else 'No'}")
    print("=========================================")
