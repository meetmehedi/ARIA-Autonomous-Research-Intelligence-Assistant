# ARIA (Autonomous Research & Intelligence Assistant)

**Owner:** Md. Mehedi Hasan (BSc CSE student, Researcher, DIU CPC President)  
**Version:** 1.0 (Local Reinforcement Learning Edition)

ARIA is an entirely local, self-contained personal AI agent designed exclusively for Mehedi. 

Initially built around Generative AI SDKs, ARIA has now been fundamentally re-architected into a **Classic Reinforcement Learning (RL) Tool-Selector Agent**. It operates 100% offline without any external LLM APIs (No OpenAI, No Gemini, No Anthropic).

## Architecture

ARIA uses a discrete Reinforcement Learning (PPO) policy to map natural language intents into executable tool actions.

1. **State Embedding**: User prompts are converted into fixed 384-dimensional vector embeddings using a lightweight local `sentence-transformers` model (`all-MiniLM-L6-v2`).
2. **Policy Network**: A Proximal Policy Optimization (PPO) Multi-Layer Perceptron (`stable-baselines3`) evaluates the state.
3. **Action Space**: The policy outputs a discrete integer corresponding to the optimal tool to use.

### Available Tools (Action Space)
- `0`: Web Search (`duckduckgo`)
- `1`: Web Scraper
- `2`: PDF Reader (`pymupdf`)
- `3`: Telegram Notifier
- `4`: Gmail Sender
- `5`: Python Executor (Sandboxed)

> **Note:** Because ARIA uses classic RL instead of generative models, it does not hold open-ended conversations or write complex code. It acts as an intelligent local intent-router for pre-built Python tools.

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/meetmehedi/ARIA-Autonomous-Research-Intelligence-Assistant.git
   cd ARIA-Autonomous-Research-Intelligence-Assistant
   ```

2. **Install dependencies:**
   *(Requires Python 3.10+)*
   ```bash
   pip install -r requirements.txt
   ```

3. **Train the Agent (Optional):**
   A pre-trained policy weight file (`aria_rl_model.zip`) is generated automatically, but you can retrain the PPO agent on your local M-series Mac:
   ```bash
   python aria/train.py
   ```

## Usage

ARIA provides several interfaces:

- **Terminal CLI:** `python main.py --cli`
- **Streamlit Web UI:** `python main.py --web`
- **Telegram Bot:** `python main.py --telegram`
- **Voice Mode (macOS):** `python main.py --voice`

## Memory system
ARIA remembers user profiles, tasks, and historical states using a custom, local SQLite database (`aria_memory.db`). You can manage tasks from the CLI using `/tasks` or view your profile with `/profile`.
