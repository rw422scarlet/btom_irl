import numpy as np
from copy import deepcopy
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.distributions as torch_dist
import torch.distributions.transforms as torch_transform

# model imports
from src.agents.nn_models import MLP, DoubleQNetwork
from src.agents.rl_utils import ReplayBuffer

class TanhTransform(torch_transform.Transform):
    """ Adapted from Pytorch implementation with clipping """
    domain = torch_dist.constraints.real
    codomain = torch_dist.constraints.real
    bijective = True
    event_dim = 0
    def __init__(self, limits):
        super().__init__() 
        assert isinstance(limits, torch.Tensor)
        self.limits = nn.Parameter(limits, requires_grad=False)
        self.eps = 1e-5

    def __call__(self, x):
        return self.limits * torch.tanh(x)
    
    def _inverse(self, y):
        y = torch.clip(y / self.limits, -1. + self.eps, 1. - self.eps) # prevent overflow
        return torch.atanh(y)

    def log_abs_det_jacobian(self, x, y):
        ldj = (2. * (np.log(2.) - x - F.softplus(-2. * x)))
        ldj += torch.abs(self.limits).log()
        return ldj


class SAC(nn.Module):
    """ Soft actor critic """
    def __init__(
        self, obs_dim, act_dim, act_lim, hidden_dim, num_hidden, activation, 
        gamma=0.9, beta=0.2, polyak=0.995, norm_obs=False, buffer_size=int(1e6), 
        batch_size=100, steps=50, lr=1e-3, decay=0., grad_clip=None
        ):
        """
        Args:
            obs_dim (int): observation dimension
            act_dim (int): action dimension
            hidden_dim (int): value network hidden dim
            num_hidden (int): value network hidden layers
            activation (str): value network activation
            algo (str, optional): imitation algorithm. choices=[ail, nail]
            gamma (float, optional): discount factor. Default=0.9
            beta (float, optional): softmax temperature. Default=0.2
            polyak (float, optional): target network polyak averaging factor. Default=0.995
            norm_obs (bool, optional): whether to normalize observations. Default=False
            buffer_size (int, optional): replay buffer size. Default=1e6
            batch_size (int, optional): discriminator and critic batch size. Default=100
            d_steps (int, optional): discriminator update steps per training step. Default=50
            a_steps (int, optional): actor critic update steps per training step. Default=50
            lr (float, optional): learning rate. Default=1e-3
            decay (float, optional): weight decay. Default=0.
            grad_clip (float, optional): gradient clipping. Default=None
        """
        super().__init__()
        self.obs_dim = obs_dim
        self.act_dim = act_dim
        self.act_lim = act_lim
        self.gamma = gamma
        self.beta = beta
        self.polyak = polyak
        self.norm_obs = norm_obs
    
        self.buffer_size = buffer_size
        self.batch_size = batch_size
        self.steps = steps
        self.lr = lr
        self.decay = decay
        self.grad_clip = grad_clip
        
        self.actor = MLP(obs_dim, act_dim * 2, hidden_dim, num_hidden, activation)
        self.critic = DoubleQNetwork(
            obs_dim, act_dim, hidden_dim, num_hidden, activation
        )
        self.critic_target = deepcopy(self.critic)
        
        self.tanh = TanhTransform(act_lim)

        # freeze target parameters
        for param in self.critic_target.parameters():
            param.requires_grad = False
        
        self.actor_optimizer = torch.optim.Adam(
            self.actor.parameters(), lr=lr, weight_decay=decay
        )
        self.critic_optimizer = torch.optim.Adam(
            self.critic.parameters(), lr=lr, weight_decay=decay
        )
        
        self.replay_buffer = ReplayBuffer(obs_dim, act_dim, buffer_size)

        self.obs_mean = nn.Parameter(torch.zeros(obs_dim), requires_grad=False)
        self.obs_variance = nn.Parameter(torch.ones(obs_dim), requires_grad=False)
        
        self.plot_keys = ["eps_return_avg", "eps_len_avg", "critic_loss_avg", "actor_loss_avg"]
    
    def __repr__(self):
        s_critic = self.critic.__repr__()
        s = "{}(gamma={}, beta={}, polyak={}, norm_obs={}, "\
            "buffer_size={}, batch_size={}, steps={}, "\
            "lr={}, decay={}, grad_clip={}, "\
            "\n    critic={}\n)".format(
            self.__class__.__name__, self.gamma, self.beta, 
            self.polyak, self.norm_obs, self.replay_buffer.max_size, 
            self.batch_size, self.steps, self.lr, self.decay, self.grad_clip,
            s_critic
        )
        return s

    def update_normalization_stats(self):
        if self.norm_obs:
            mean = torch.from_numpy(self.replay_buffer.moving_mean).to(torch.float32)
            variance = torch.from_numpy(self.replay_buffer.moving_variance).to(torch.float32)

            self.obs_mean.data = mean
            self.obs_variance.data = variance
    
    def normalize_obs(self, obs):
        obs_norm = (obs - self.obs_mean) / self.obs_variance**0.5
        return obs_norm
    
    def sample_action(self, obs):
        mu, lv = torch.chunk(self.actor.forward(obs), 2, dim=-1)
        std = torch.exp(lv.clip(np.log(1e-3), np.log(100)))
        base_dist = torch_dist.Normal(mu, std)
        act = base_dist.rsample()
        logp = base_dist.log_prob(act).sum(-1, keepdim=True)

        ldj = (2. * (np.log(2.) - act - F.softplus(-2. * act)))
        ldj += torch.abs(self.act_lim).log()

        act = torch.tanh(act) * self.act_lim
        logp -= ldj.sum(-1, keepdim=True)
        return act, logp

    def choose_action(self, obs):
        with torch.no_grad():
            obs_norm = self.normalize_obs(obs)
            a, _ = self.sample_action(obs_norm)
        return a

    def compute_critic_loss(self):
        batch = self.replay_buffer.sample(self.batch_size)
        
        obs = batch["obs"]
        # absorb = batch["absorb"]
        act = batch["act"]
        r = batch["rwd"]
        next_obs = batch["next_obs"]
        # next_absorb = batch["next_absorb"]
        done = batch["done"]
        
        # normalize observation
        obs_norm = self.normalize_obs(obs)
        next_obs_norm = self.normalize_obs(next_obs)
        
        with torch.no_grad():
            # sample next action
            next_act, logp = self.sample_action(next_obs_norm)
            
            critic_input = torch.cat([obs_norm, act], dim=-1)
            critic_next_input = torch.cat([next_obs_norm, next_act], dim=-1)

            # compute value target
            q1_next, q2_next = self.critic_target(critic_next_input)
            q_next = torch.min(q1_next, q2_next)
            v_next = q_next - self.beta * logp
            q_target = r + (1 - done) * self.gamma * v_next
        
        q1, q2 = self.critic(critic_input)
        q1_loss = torch.pow(q1 - q_target, 2).mean()
        q2_loss = torch.pow(q2 - q_target, 2).mean()
        q_loss = (q1_loss + q2_loss) / 2 
        return q_loss
    
    def compute_actor_loss(self):
        batch = self.replay_buffer.sample(self.batch_size)

        obs = batch["obs"]
        obs_norm = self.normalize_obs(obs)
        
        act, logp = self.sample_action(obs_norm)
        
        critic_input = torch.cat([obs_norm, act], dim=-1)
        q1, q2 = self.critic(critic_input)
        q = torch.min(q1, q2)

        a_loss = torch.mean(self.beta * logp - q)
        return a_loss

    def take_gradient_step(self, logger=None):
        self.actor.train()
        self.critic.train()
        self.update_normalization_stats()
        
        actor_loss_epoch = []
        critic_loss_epoch = []
        for i in range(self.steps):
            # train critic
            critic_loss = self.compute_critic_loss()
            critic_loss.backward()
            if self.grad_clip is not None:
                nn.utils.clip_grad_norm_(self.critic.parameters(), self.grad_clip)
            self.critic_optimizer.step()
            self.critic_optimizer.zero_grad()
            self.actor_optimizer.zero_grad()
            
            critic_loss_epoch.append(critic_loss.data.item())

            # train actor
            actor_loss = self.compute_actor_loss()
            actor_loss.backward()
            if self.grad_clip is not None:
                nn.utils.clip_grad_norm_(self.actor.parameters(), self.grad_clip)
            self.actor_optimizer.step()
            self.actor_optimizer.zero_grad()
            self.critic_optimizer.zero_grad()
            
            actor_loss_epoch.append(actor_loss.data.item())
            
            # update target networks
            with torch.no_grad():
                for p, p_target in zip(
                    self.critic.parameters(), self.critic_target.parameters()
                ):
                    p_target.data.mul_(self.polyak)
                    p_target.data.add_((1 - self.polyak) * p.data)

            if logger is not None:
                logger.push({
                    "actor_loss": actor_loss.cpu().data.item(),
                    "critic_loss": critic_loss.cpu().data.item(),
                })

        stats = {
            "actor_loss": np.mean(actor_loss_epoch),
            "critic_loss": np.mean(critic_loss_epoch),
        }
        
        self.actor.eval()
        self.critic.eval()
        return stats
        