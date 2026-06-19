import os
from stable_baselines3 import PPO
from sentence_transformers import SentenceTransformer
import numpy as np

# Map discrete actions to tool names
ACTION_TO_TOOL = {
    0: "search_web",
    1: "scrape_url",
    2: "read_pdf",
    3: "send_telegram",
    4: "send_gmail",
    5: "execute_python"
}

class RLToolAgent:
    def __init__(self):
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        model_path = os.path.join(os.path.dirname(__file__), "aria_rl_model.zip")
        
        if os.path.exists(model_path):
            self.model = PPO.load(model_path)
            self.trained = True
        else:
            self.trained = False
            print(f"Warning: Model not found at {model_path}. Run train.py first.")

    def get_action(self, prompt: str) -> str:
        if not self.trained:
            return "Error: RL Agent not trained. Please run `python aria/train.py`."
        
        obs = self.encoder.encode(prompt)
        # Predict the discrete action
        action, _states = self.model.predict(np.array(obs, dtype=np.float32), deterministic=True)
        
        tool_name = ACTION_TO_TOOL.get(int(action), "unknown")
        
        return f"RL Agent Selected Tool: {tool_name}\n(To execute complex tasks, the RL agent needs a custom integration for arguments, which discrete RL cannot generate natively.)"

# Async wrapper for compatibility with existing UI
async def execute_rl_agent(user_input: str, history: list) -> str:
    agent = RLToolAgent()
    return agent.get_action(user_input)
