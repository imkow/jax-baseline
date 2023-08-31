import numpy as np
import haiku as hk
import jax
import jax.numpy as jnp
from functools import partial


class Actor(hk.Module):
    def __init__(self, action_size, action_type, node=256, hidden_n=2):
        super(Actor, self).__init__()
        self.action_size = action_size
        self.action_type = action_type
        self.node = node
        self.hidden_n = hidden_n
        self.layer = hk.Linear
        self.layer = partial(
            self.layer,
            w_init=hk.initializers.VarianceScaling(scale=2),
            b_init=hk.initializers.VarianceScaling(scale=2),
        )

    def __call__(self, feature: jnp.ndarray) -> jnp.ndarray:
        mlp = hk.Sequential(
            [
                self.layer(self.node) if i % 2 == 0 else jax.nn.relu
                for i in range(2 * self.hidden_n)
            ]
        )(feature)
        if self.action_type == "discrete":
            action_probs = self.layer(self.action_size[0])(mlp)
            return action_probs
        elif self.action_type == "continuous":
            mu = self.layer(self.action_size[0])(mlp)
            log_std = jnp.clip(
                self.layer(self.action_size[0])(mlp), -20, 2
            )  # hk.get_parameter("log_std", [input_size, output_size], dtype, init=w_init)
            return mu, log_std


class Critic(hk.Module):
    def __init__(self, node=256, hidden_n=2):
        super(Critic, self).__init__()
        self.node = node
        self.hidden_n = hidden_n
        self.layer = hk.Linear

    def __call__(self, feature: jnp.ndarray) -> jnp.ndarray:
        net = hk.Sequential(
            [
                self.layer(self.node) if i % 2 == 0 else jax.nn.relu
                for i in range(2 * self.hidden_n)
            ]
            + [self.layer(1)]
        )(feature)
        return net
