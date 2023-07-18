import jax
import jax.numpy as jnp
import numpy as np

from typing import List
 
def hard_update(new_tensors, old_tensors, steps: int, update_period: int):
	update = (steps % update_period == 0)
	return jax.tree_map(
			lambda new, old: jax.lax.select(update, new, old), new_tensors, old_tensors)
				
def soft_update(new_tensors, old_tensors, tau : float):
		return jax.tree_map(
			lambda new, old: tau * new + (1.0 - tau) * old,
			new_tensors, old_tensors)

def t_soft_function(new, old, W, tau, v):
	pass

def t_soft_update(new_tensors, old_tensors, W_tensors,tau : float, v=1.0):
	return jax.tree_map(
		lambda new, old: tau * new + (1.0 - tau) * old,
		new_tensors, old_tensors, W_tensors)
	
def truncated_mixture(quantiles, cut):
	quantiles = jnp.concatenate(quantiles,axis=1)
	sorted = jnp.sort(quantiles,axis=1)
	return sorted[:,:-cut]
		
def convert_states(obs : List):
	return [(o* 255.0).astype(np.uint8) if len(o.shape) >= 4 else o for o in obs]

def convert_jax(obs : List):
	return [jax.device_get(o).astype(jnp.float32) for o in obs]
	#return [jax.device_get(o).astype(jnp.float32)/256.0 - 0.5 if len(o.shape) >= 4 else jax.device_get(o) for o in obs]

def q_log_pi(q,entropy_tau):
	q_submax = q - jnp.max(q, axis=1, keepdims=True)
	logsum = jax.nn.logsumexp(q_submax/entropy_tau,axis=1,keepdims=True)
	tau_log_pi = (q_submax - entropy_tau*logsum)
	return q_submax, tau_log_pi

def discounted(rewards,gamma=0.99): #lfilter([1],[1,-gamma],x[::-1])[::-1]
	_gamma = 1
	out = 0
	for r in rewards:
		out += r*_gamma
		_gamma *= gamma
	return out


def discount_with_terminal(rewards, dones, terminals, next_values, gamma):
	def f(ret, info):
		reward, done, term, nextval = info
		ret = reward + gamma * (ret * (1. - term) + nextval * (1. - done) * term)
		return ret, ret
	terminals.at[-1].set(jnp.ones((1,),dtype=jnp.float32))
	_, discounted = jax.lax.scan(f, jnp.zeros((1,),dtype=jnp.float32), (rewards, dones, terminals, next_values),reverse=True)
	return discounted
'''

def discount_with_terminal(rewards, dones, terminals, next_values, gamma):
	ret = rewards[-1] + gamma * next_values[-1] * (1. - dones[-1])
	discounted = [ret]
	for reward, done, term, nextval in zip(rewards[-2::-1], dones[-2::-1], terminals[-2::-1], next_values[-2::-1]):
		ret = reward + gamma * (ret * (1. - term) + nextval * (1. - done) * term) # fixed off by one bug
		discounted.append(ret)
	return discounted[::-1]
'''
def get_gaes(rewards, dones, terminals, values, next_values, gamma, lamda):
	deltas = rewards +  gamma * (1. - dones) * next_values - values
	def f(last_gae_lam, info):
		delta, don, term = info
		last_gae_lam = delta + gamma * lamda * (1. - don) * (1. - term) * last_gae_lam
		return last_gae_lam, last_gae_lam
	_, advs = jax.lax.scan(f, jnp.zeros((1,),dtype=jnp.float32), (deltas, dones, terminals),reverse=True)
	return advs

'''
def get_gaes(rewards, dones, terminals, values, next_values, gamma, lamda):
	last_gae_lam = 0
	delta = rewards[-1] + gamma * next_values[-1] * (1. - dones[-1]) - values[-1]
	last_gae_lam = delta + gamma * lamda * (1. - dones[-1]) * last_gae_lam
	advs = [last_gae_lam]
	for reward, done, value, nextval, term in zip(rewards[-2::-1], dones[-2::-1], values[-2::-1], next_values[-2::-1], terminals[-2::-1]):
		delta = reward + gamma * (nextval * (1. - done)) - value
		last_gae_lam = delta + gamma * lamda * (1. - term) * last_gae_lam
		advs.append(last_gae_lam)
	advs = jnp.array(advs[::-1])
	return advs
'''

def get_vtrace(rewards, rhos, c_ts, dones, terminals, values, next_values, gamma):
	deltas = rhos*(rewards +  gamma * (1. - dones) * next_values - values)
	def f(last_v, info):
		delta, c_t, don, term = info
		last_v = delta + gamma * c_t * (1. - don) * (1. - term) * last_v
		return last_v, last_v
	_, A = jax.lax.scan(f, jnp.zeros((1,),dtype=jnp.float32), (deltas, c_ts, dones, terminals), reverse=True)
	v = A + values
	return  v

def formatData(t,s):
	if not isinstance(t,dict) and not isinstance(t,list):
		print(": "+str(t), end ="")
	else:
		for key in t:
			print("\n"+"\t"*s+str(key), end ="")
			if not isinstance(t,list):
				formatData(t[key],s+1)

def print_param(name,params):
	print(name, end ="")
	param_tree_map = jax.tree_map(lambda x: x.shape, params)
	formatData(param_tree_map,1)
	print()