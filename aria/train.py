import os
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from aria.environment import AriaEnv

def train_agent(timesteps=10000):
    env = AriaEnv()
    
    # Verify environment follows Gymnasium API
    check_env(env)
    
    print("Training ARIA Discrete RL Agent...")
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=timesteps)
    
    model_path = os.path.join(os.path.dirname(__file__), "aria_rl_model.zip")
    model.save(model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_agent()
