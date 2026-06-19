import sys
import os
os.environ["USE_TF"] = "NO"
os.environ["USE_TORCH"] = "YES"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import argparse
from aria.config import print_config_summary
from aria.memory import init_db

def main():
    parser = argparse.ArgumentParser(description="ARIA - Autonomous Research & Intelligence Assistant")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--telegram", action="store_true", help="Launch Telegram Bot interface")
    group.add_argument("--web", action="store_true", help="Launch Streamlit Web UI interface")
    group.add_argument("--voice", action="store_true", help="Launch wake-word voice interface (macOS)")
    group.add_argument("--cli", action="store_true", help="Launch interactive CLI (default)")
    group.add_argument("--config-test", action="store_true", help="Test loading config and databases")
    
    args = parser.parse_args()
    
    # Initialize the memory store database
    init_db()
    
    if args.config_test:
        print_config_summary()
        sys.exit(0)
        
    if args.voice:
        try:
            from aria.voice import run as run_voice
            print("Launching ARIA in wake-word voice mode (macOS)...")
            run_voice()
        except ImportError as e:
            print(f"Error launching voice mode: {e}")
            print("Install with: pip install SpeechRecognition pyaudio")
            sys.exit(1)

    if args.telegram:
        try:
            from aria.telegram_bot import run_telegram_bot
            print("Launching ARIA in Telegram Bot mode...")
            run_telegram_bot()
        except ImportError as e:
            print(f"Error launching Telegram Bot: {e}")
            print("Please make sure you have python-telegram-bot installed.")
            sys.exit(1)
            
    elif args.web:
        # Launching Streamlit is usually done via command line: streamlit run aria/web_ui.py
        # But we can provide instructions or run subprocess
        import subprocess
        from pathlib import Path
        
        web_ui_path = Path(__file__).resolve().parent / "aria" / "web_ui.py"
        print(f"Launching ARIA Web UI (Streamlit) at {web_ui_path}...")
        try:
            subprocess.run(["streamlit", "run", str(web_ui_path)], check=True)
        except KeyboardInterrupt:
            print("\nWeb UI stopped.")
        except FileNotFoundError:
            print("Error: 'streamlit' command not found. Please install dependencies in requirements.txt.")
            sys.exit(1)
            
    else:
        # Default CLI mode
        from aria.cli import run_cli
        run_cli()

if __name__ == "__main__":
    main()
