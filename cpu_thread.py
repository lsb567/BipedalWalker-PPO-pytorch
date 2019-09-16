import os
import gym
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from parameters import parameters


def preprocess_state(state):
    return np.clip(state, -10, 10).astype('float32')


def process_reward(reward):
    return 0.01*reward


def generate_game(env, pid, process_queue, common_dict):
    observation = env.reset()
    done = False
    reward_list = []
    action_list = []
    observation_list = []
    prob_list = []
    while not done:
        observation_list.append(observation)
        process_queue.put((pid, observation))
        while pid not in common_dict:
            time.sleep(0.0001)
        action, prob = common_dict[pid]
        del common_dict[pid]
        observation, reward, done, _ = env.step(np.clip(action, -1, 1))
        action_list.append(action)
        prob_list.append(prob)
        reward_list.append(process_reward(reward))
    print('Distance: {0:7.3f}'.format(np.sum(observation_list, 0)[2]), flush=True)
    for i in range(len(reward_list) - 2, -1, -1):
        reward_list[i] += reward_list[i + 1] * parameters.GAMMA  # compute the discounted obtained reward for each step
    return observation_list, reward_list, action_list, prob_list


def play(env, pid, process_queue, common_dict):
    while 'epoch' not in common_dict:
        time.sleep(0.001)
    while True:
        if common_dict['epoch'] % 25 == 0:
            episode = common_dict['epoch']
            observation = env.reset()
            frames = []
            done = False
            while not done:
                process_queue.put((pid, observation))
                while pid not in common_dict:
                    time.sleep(0.0001)
                action, prob = common_dict[pid]
                del common_dict[pid]
                observation, _, done, _ = env.step(np.clip(action, -1, 1))
                frames.append(env.render(mode='rgb_array'))
            try:
                display_frames_as_gif(frames, 'Episode {}.gif'.format(episode))
            except:
                pass


def display_frames_as_gif(frames, name):
    """
    Displays a list of frames as a gif, with controls
    """
    plt.figure(figsize=(frames[0].shape[1] / 72.0, frames[0].shape[0] / 72.0), dpi=72)
    patch = plt.imshow(frames[0])
    plt.axis('off')
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    def animate(i):
        patch.set_data(frames[i])

    anim = animation.FuncAnimation(plt.gcf(), animate, frames=len(frames), interval=33)
    try:
        anim.save('gifs/' + name)
    except:
        anim.save('gifs/' + name, writer=animation.PillowWriter(fps=40))


def cpu_thread(render, memory_queue, process_queue, common_dict, worker):
    import psutil
    p = psutil.Process()
    p.cpu_affinity([worker])
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        env = gym.make("BipedalWalker-v2")
        pid = os.getpid()
        print('process started with pid: {} on core {}'.format(os.getpid(), worker), flush=True)
        if render:
            play(env, pid, process_queue, common_dict)
        while True:
            observation_list, reward_list, action_list, prob_list = generate_game(env, pid, process_queue, common_dict)
            for i in range(len(observation_list)):
                memory_queue.put((observation_list.pop(), reward_list.pop(), action_list.pop(), prob_list.pop()))
    except Exception as e:
        print(e, flush=True)
