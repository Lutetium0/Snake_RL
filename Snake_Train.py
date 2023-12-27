from flask import Flask, jsonify, request
import logging
import json

import gymnasium as gym
from gymnasium import spaces
from collections import deque
import numpy as np
from stable_baselines3.common.env_checker import check_env

gameBegin = True
gameEnd = False
curAction = 0

SNAKE_LEN_GOAL = 30

head_x = 0
head_y = 0
apple_delta_x = 0
apple_delta_y = 0
snake_length = 0

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route('/initinfo', methods=['GET'])
def get_initInfo():
    global gameBegin
    app.logger.info(gameBegin)
    return jsonify({'begin': gameBegin})

@app.route('/curAction', methods=['GET'])
def get_curAction():
    return jsonify({'curAction': curAction})

@app.route('/setState', methods=['GET', 'POST'])
def set_curState():
    global gameBegin
    data = json.loads(request.data)
    #app.logger.info(data["gameEnd"])
    #app.logger.info(data["head_x"])
    #app.logger.info(data["head_y"])
    #app.logger.info(data["apple_delta_x"])
    #app.logger.info(data["apple_delta_y"])
    #app.logger.info(data["snake_length"])
    if data["gameEnd"] == False:
      gameBegin = False
    return jsonify({'begin': gameBegin})

if __name__ == '__main__':
    app.run(debug=True)

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
    self.total_reward = snake_length - 3
    self.reward = self.total_reward - self.prev_reward
    self.prev_reward = self.total_reward
    
    self.terminated = gameEnd
    info = {}
    observation = [head_x, head_y, apple_delta_x, apple_delta_y, snake_length] + list(self.prev_actions)
    observation = np.array(observation, dtype=np.float32)
    return observation, self.reward, self.terminated, False, info
  
  def reset(self, seed=None, options=None):
    global gameEnd
    global curAction
    global head_x
    global head_y
    global apple_delta_x
    global apple_delta_y
    global snake_length
    
    self.score = 0
    self.prev_button_direction = 1
    self.prev_reward = 0
    self.terminated = False
    self.prev_actions = deque(maxlen = SNAKE_LEN_GOAL)
    for i in range(SNAKE_LEN_GOAL):
      self.prev_actions.append(-1) # to create history
    observation = [head_x, head_y, apple_delta_x, apple_delta_y, snake_length] + list(self.prev_actions)
    observation = np.array(observation, dtype=np.float32)
    info = {}
    return observation, info