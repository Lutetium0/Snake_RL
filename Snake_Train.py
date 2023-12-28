from operator import truediv
from flask import Flask as _Flask
from flask import jsonify, request
from flask.json.provider import DefaultJSONProvider, _default as FlaskDefault
import json
import threading
import time
import os
import datetime
import math

import gymnasium as gym
from gymnasium import spaces
from collections import deque
import numpy as np
from stable_baselines3.common.env_checker import check_env
from stable_baselines3 import PPO

receiveGameConnection = False
gameBegin = False
gameEnd = False
curAction = 0

head_x = 0
head_y = 0
apple_delta_x = 0
apple_delta_y = 0
snake_length = 3

SNAKE_LEN_GOAL = 30

class FlaskJSONProvider(DefaultJSONProvider):
  @staticmethod
  def _default(obj):
    if isinstance(obj, (np.integer, np.floating, np,bool)):
      return obj.item()
    elif isinstance(obj, np.ndarray):
      return obj.tolist()
    elif isinstance(obj, (datetime.datetime, datetime.timedelta)):
      return obj.__str__()
    else:
      return FlaskDefault(obj)

  default = _default

class Flask(_Flask):
  json_provider_class = FlaskJSONProvider
  
app = Flask(__name__)

@app.route('/initinfo', methods=['GET'])
def get_initInfo():
    global receiveGameConnection
    receiveGameConnection = True
    
    return jsonify({'begin': gameBegin})

@app.route('/curAction', methods=['GET'])
def get_curAction():
    return jsonify({'curAction': curAction})

@app.route('/setState', methods=['GET', 'POST'])
def set_curState():
    
    data = json.loads(request.data)
    global gameBegin
    global gameEnd
    global head_x
    global head_y
    global apple_delta_x
    global apple_delta_y
    global snake_length

    gameEnd =  data["gameEnd"]
    head_x = data["head_x"]
    head_y = data["head_y"]
    apple_delta_x = data["apple_delta_x"]
    apple_delta_y = data["apple_delta_y"]
    snake_length = data["snake_length"]

    if gameEnd == True:
      gameBegin = False
    return jsonify({'begin': gameBegin})

class CustomEnv(gym.Env):
  """Custom Environment that follows gym interface"""
  metadata = {'render.modes': ['human']}

  def __init__(self):
    super(CustomEnv, self).__init__()
    self.action_space = spaces.Discrete(4)
    self.observation_space = spaces.Box(low=-500, high=500,
                                        shape=(5+SNAKE_LEN_GOAL,), dtype=np.float32)

  def step(self, action):
    global gameEnd
    global curAction
    global head_x
    global head_y
    global apple_delta_x
    global apple_delta_y
    global snake_length
    
    curAction = action
    
    self.prev_actions.append(action)
    
    time.sleep(0.05)
  
    self.cur_length = snake_length - 3
    self.length_reward = self.cur_length - self.prev_length
    self.prev_length = self.cur_length
    
    self.cur_apple_delta_mag = math.sqrt(apple_delta_x**2 + apple_delta_y**2)
    self.apple_delta_mag_reward = (self.prev_apple_delta_mag - self.cur_apple_delta_mag) / 100
    self.prev_apple_delta_mag = self.cur_apple_delta_mag
    
    total_reward = self.length_reward * 10 + self.apple_delta_mag_reward
    
    self.terminated = gameEnd
    info = {}
    observation = [head_x, head_y, apple_delta_x, apple_delta_y, snake_length] + list(self.prev_actions)
    observation = np.array(observation, dtype=np.float32)
    return observation, total_reward, self.terminated, False, info
  
  def reset(self, seed=None, options=None):
    global gameBegin
    global gameEnd
    global curAction
    global head_x
    global head_y
    global apple_delta_x
    global apple_delta_y
    global snake_length
    
    gameBegin = True
    gameEnd = False
    curAction = 0
    head_x = 0
    head_y = 0
    apple_delta_x = 0
    apple_delta_y = 0
    snake_length = 3
    
    self.cur_length= 0
    self.length_reward = 0
    self.prev_length = 0
    
    self.prev_apple_delta_mag = 0
    self.cur_apple_delta_mag = 0
    self.apple_delta_mag_reward = 0
    
    self.terminated = False
    self.prev_actions = deque(maxlen = SNAKE_LEN_GOAL)
    for i in range(SNAKE_LEN_GOAL):
      self.prev_actions.append(-1) # to create history
    observation = [head_x, head_y, apple_delta_x, apple_delta_y, snake_length] + list(self.prev_actions)
    observation = np.array(observation, dtype=np.float32)
    info = {}
    return observation, info
  
def run_app():
    app.run(debug=False, threaded=True)

def check_function():
  env = CustomEnv()
  episodes = 50

  for episode in range(episodes):
    done = False
    obs = env.reset()
  while True:#not done:
     random_action = env.action_space.sample()
     print("action",random_action)

def train_function():
    
    models_dir = f"models/{int(time.time())}/"
    logdir = f"logs/{int(time.time())}/"

    if not os.path.exists(models_dir):
      os.makedirs(models_dir)
    if not os.path.exists(logdir):
      os.makedirs(logdir)
    
    global receiveGameConnection
    while receiveGameConnection == False:
      time.sleep(0.5)
    
    env = CustomEnv()
    env.reset()
    
    model = PPO('MlpPolicy', env, verbose=1, tensorboard_log=logdir)

    TIMESTEPS = 10000
    iters = 0
    while True:
      iters += 1
      model.learn(total_timesteps=TIMESTEPS, reset_num_timesteps=False, tb_log_name=f"PPO")
      model.save(f"{models_dir}/{TIMESTEPS*iters}")
        
if __name__ == "__main__":
    first_thread = threading.Thread(target=run_app)
    second_thread = threading.Thread(target=train_function)
    first_thread.start()
    second_thread.start()