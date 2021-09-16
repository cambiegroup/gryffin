#!/usr/bin/env python

import pytest
import numpy as np
from gryffin import Gryffin

from benchmark_functions.benchmark_functions_cont import dejong
from benchmark_functions.benchmark_functions_cat import Michalewicz

PARAM_DIM = 2
NUM_OPTS = 21
BUDGET = 3
SAMPLING_STRATEGIES = np.array([-1, 1])

surface_cont = dejong
surface_cat  = Michalewicz(num_dims=2, num_opts=NUM_OPTS)

def known_constraints_cont(params):
	x0 = params['param_0']
	x1 = params['param_1']
	y = (x0-0.5)**2 + (x1-0.5)**2

	if np.abs(x0-x1) < 0.1:
		return False

	if 0.05 < y < 0.15:
		return False
	else:
		return True

def known_constraints_cat(params):
	x0 = params['param_0']  # str
	x1 = params['param_1']  # str
	Xi = str2array([x0, x1])
	x0 = Xi[0]  # float
	x1 = Xi[1]  # float

	y = ((x0-14))**2 + (x1-10)**2
	if 5 < y < 30:
		return False
	if 12.5 < x0 < 15.5:
		if x1 < 5.5:
			return False
	if 8.5 < x1 < 11.5:
		if x0 < 9.5:
			return False
	return True

def str2array(sample):
	return np.array([round(float(entry[2:])) for entry in np.squeeze(sample)])

def test_constraints_cont():
	config = {
		"general": {
			"num_cpus": 4,
			"auto_desc_gen": False,
			"batches": 1,
			"sampling_strategies": 1,
			"boosted":  False,
			"caching": True,
			"random_seed": 2021,
			"acquisition_optimizer": "adam",
			"verbosity": 3
			},
		"parameters": [
			{"name": "param_0", "type": "continuous", "low": 0., "high": 1.},
			{"name": "param_1", "type": "continuous", "low": 0., "high": 1.},
		],
		"objectives": [
			{"name": "obj", "goal": "min"},
		]
	}

	gryffin = Gryffin(
		config_dict=config, known_constraints=known_constraints_cont,
	)
	# TODO: check if the estimated feasible reagion is reasonably accurate
	observations = []
	for iter_ in range(BUDGET):
		select_ix = iter_ % len(SAMPLING_STRATEGIES)
		sampling_strategy = SAMPLING_STRATEGIES[select_ix]

		samples = gryffin.recommend(observations, sampling_strategies=[sampling_strategy])
		sample = samples[0]
		observation = surface_cont([sample['param_0'], sample['param_1']])
		sample['obj'] = observation
		observations.append(sample)

	assert len(observations)==BUDGET
	assert len(observations[0])==3
	# check to see if all the resulting observations are indeed feasible
	for obs in observations:
		assert known_constraints_cont(obs)


def test_constraints_cat():

	param_0_details = {f'x_{i}': [i] for i in range(NUM_OPTS)}
	param_1_details  = {f'x_{i}': [i] for i in range(NUM_OPTS)}

	config = {
		"general": {
			"num_cpus": 4,
			"auto_desc_gen": True,
			"batches": 1,
			"sampling_strategies": 1,
			"boosted":  False,
			"caching": True,
			"random_seed": 2021,
			"acquisition_optimizer": "adam",
			"verbosity": 3
			},
		"parameters": [
			{"name": "param_0", "type": "categorical", "category_details": param_0_details},
			{"name": "param_1", "type": "categorical", "category_details": param_1_details},
		],
		"objectives": [
			{"name": "obj", "goal": "min"},
		]
	}

	gryffin = Gryffin(
		config_dict=config, known_constraints=known_constraints_cat
	)
	observations = []
	for iter_ in range(BUDGET):
		select_ix = iter_ % len(SAMPLING_STRATEGIES)
		sampling_strategy = SAMPLING_STRATEGIES[select_ix]

		samples = gryffin.recommend(observations, sampling_strategies=[sampling_strategy])
		sample = samples[0]
		observation = surface_cat([sample['param_0'], sample['param_1']])
		sample['obj'] = observation
		observations.append(sample)

	assert len(observations)==BUDGET
	assert len(observations[0])==3
	# check to see if all the resulting observations are indeed feasible
	for obs in observations:
		assert known_constraints_cat(obs)
