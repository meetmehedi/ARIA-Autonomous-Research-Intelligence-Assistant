import gymnasium as gym
from gymnasium import spaces
import numpy as np
from sentence_transformers import SentenceTransformer
import random


class AriaEnv(gym.Env):
    """
    A classic RL environment for ARIA.
    Instead of generating text, the agent observes the user prompt's embedding
    and learns to select the correct discrete tool action.
    """

    metadata = {"render_modes": ["console"]}

    def __init__(self):
        super(AriaEnv, self).__init__()

        # Tools: 0=Search, 1=Scrape, 2=PDF, 3=Telegram, 4=Gmail, 5=Execute
        self.action_space = spaces.Discrete(6)

        # Using a lightweight local embedding model (runs entirely on-device)
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(384,), dtype=np.float32
        )

        # Labelled training examples: (prompt, optimal_action_id)
        self.training_data = [
            ("search the web for artificial intelligence news", 0),
            ("find me information about reinforcement learning online", 0),
            ("look up the latest machine learning papers", 0),
            ("scrape the content from this webpage url", 1),
            ("extract text from that HTML site", 1),
            ("get me the text from this website", 1),
            ("read the contents of this PDF file", 2),
            ("parse the pdf document", 2),
            ("extract text from this PDF report", 2),
            ("send a telegram message to my phone", 3),
            ("notify me on telegram", 3),
            ("push an alert to my telegram", 3),
            ("send an email to my supervisor via gmail", 4),
            ("draft an email", 4),
            ("email my professor", 4),
            ("execute this python script locally", 5),
            ("run the code sandboxed", 5),
            ("run this script and give me the output", 5),
        ]

        self.current_target_action = None
        self.current_prompt = None

    def reset(self, seed=None, options=None):
        """Reset the environment by selecting a new random training example."""
        super().reset(seed=seed)
        self.current_prompt, self.current_target_action = random.choice(
            self.training_data
        )
        state = self.encoder.encode(self.current_prompt)
        return np.array(state, dtype=np.float32), {}

    def step(self, action):
        """Take one step: reward +1 for correct tool, -1 for wrong tool."""
        terminated = True  # Single-step episode
        truncated = False

        if action == self.current_target_action:
            reward = 1.0
            info = {
                "msg": f"Correct! Chose tool {action} for: {self.current_prompt}"
            }
        else:
            reward = -1.0
            info = {
                "msg": f"Wrong! Chose {action}, expected {self.current_target_action}"
            }

        # Encode again for the terminal observation
        state = self.encoder.encode(self.current_prompt)
        return np.array(state, dtype=np.float32), reward, terminated, truncated, info

    def render(self):
        """Print the current prompt."""
        print(f"Current Prompt: {self.current_prompt}")
