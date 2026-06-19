import gymnasium as gym
from gymnasium import spaces
import numpy as np
from sentence_transformers import SentenceTransformer
import random

class AriaEnv(gym.Env):
    \"\"\"
    A classic RL environment for ARIA.
    Instead of generating text, the agent observes the user prompt's embedding
    and learns to select the correct discrete tool action.
    \"\"\"
    
    metadata = {"render_modes": ["console"]}

    def __init__(self):
        super(AriaEnv, self).__init__()
        
        # Tools: 0=Search, 1=Scrape, 2=PDF, 3=Telegram, 4=Gmail, 5=Execute
        self.action_space = spaces.Discrete(6)
        
        # Using a lightweight local embedding model
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(384,), dtype=np.float32)
        
        # Mock dataset of user requests and their optimal actions
        self.training_data = [
            ("search the web for artificial intelligence news", 0),
            ("find me information about reinforcement learning online", 0),
            ("scrape the content from this webpage url", 1),
            ("extract text from that HTML site", 1),
            ("read the contents of this PDF file", 2),
            ("parse the pdf document", 2),
            ("send a telegram message to my phone", 3),
            ("notify me on telegram", 3),
            ("send an email to my supervisor via gmail", 4),
            ("draft an email", 4),
            ("execute this python script locally", 5),
            ("run the code sandboxed", 5)
        ]
        
        self.current_target_action = None
        self.current_prompt = None

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # Randomly select a task
        self.current_prompt, self.current_target_action = random.choice(self.training_data)
        
        # Create state embedding
        state = self.encoder.encode(self.current_prompt)
        return np.array(state, dtype=np.float32), {}

    def step(self, action):
        terminated = True  # One-step episode for simplicity
        truncated = False
        
        if action == self.current_target_action:
            reward = 1.0
            info = {"msg": f"Success: Chose correct tool {action} for prompt: {self.current_prompt}"}
        else:
            reward = -1.0
            info = {"msg": f"Fail: Chose {action}, expected {self.current_target_action}"}
            
        # We need a dummy next state
        state = self.encoder.encode(self.current_prompt)
        return np.array(state, dtype=np.float32), reward, terminated, truncated, info

    def render(self):
        print(f"Current Prompt: {self.current_prompt}")
