#!/usr/bin/env python 

# cython: language_level=3
# cython: profile=True

__author__ = 'Florian Hase'

#========================================================================

import  cython 
cimport cython
import  numpy as np 
cimport numpy as np
from libc.math cimport exp, round

#========================================================================

cdef double _gauss(double x, double loc, double sqrt_prec):
    cdef double argument, result
    argument = 0.5 * ( sqrt_prec * (x - loc) )**2
    if argument > 200.:
        result = 0.
    else:
        result = exp( - argument) * sqrt_prec * 0.3989422804014327  # the number is 1. / np.sqrt(2 * np.pi)
    return result

#========================================================================

cdef class KernelEvaluator:

    cdef int    num_samples, num_obs, num_kernels, num_cats
    cdef double lower_prob_bound, inv_vol

    cdef np.ndarray np_locs, np_sqrt_precs, np_cat_probs
    cdef np.ndarray np_kernel_types, np_kernel_sizes
    cdef np.ndarray np_objs
    cdef np.ndarray np_probs

    var_dict = {}

    def __init__(self, locs, sqrt_precs, cat_probs, kernel_types, kernel_sizes, lower_prob_bound, objs, inv_vol):

        self.np_locs          = locs
        self.np_sqrt_precs    = sqrt_precs
        self.np_cat_probs     = cat_probs
        self.np_kernel_types  = kernel_types
        self.np_kernel_sizes  = kernel_sizes
        self.np_objs          = objs

        self.num_samples      = locs.shape[0]
        self.num_obs          = locs.shape[1]
        self.num_kernels      = locs.shape[2]
        self.lower_prob_bound = lower_prob_bound
        self.inv_vol          = inv_vol

        self.np_probs = np.zeros(self.num_obs, dtype = np.float64)


    @cython.boundscheck(False)
    @cython.cdivision(True)
    cdef double [:] _probs(self, double [:] sample):

        cdef int    sample_index, obs_index, feature_index, kernel_index
        cdef int    num_indices
        cdef int    num_continuous, num_categorical
        cdef double total_prob, prec_prod, exp_arg_sum

        cdef double [:, :, :] locs       = self.np_locs
        cdef double [:, :, :] sqrt_precs = self.np_sqrt_precs
        cdef double [:, :, :] cat_probs  = self.np_cat_probs

        cdef int [:] kernel_types = self.np_kernel_types
        cdef int [:] kernel_sizes = self.np_kernel_sizes

        cdef double inv_sqrt_two_pi = 0.3989422804014327

        cdef double [:] probs = self.np_probs
        for obs_index in range(self.num_obs):
            probs[obs_index] = 0.

        cdef double cat_prob
        cdef double obs_probs

        # get number of continuous variables
        num_continuous = 0
        while kernel_index < self.num_kernels:
            num_continuous += 1
            kernel_index   += kernel_sizes[kernel_index]

        # for each kernel location
        for obs_index in range(self.num_obs):
            obs_probs = 0.

            # for each BNN sample
            for sample_index in range(self.num_samples):
                total_prob     = 1.
                prec_prod      = 1.
                exp_arg_sum    = 0.
                feature_index, kernel_index = 0, 0

                # for each kernel/dimension
                while kernel_index < self.num_kernels:

                    if kernel_types[kernel_index] == 0:
                        # continuous kernel
                        prec_prod      = prec_prod * sqrt_precs[sample_index, obs_index, kernel_index]
                        exp_arg_sum    = exp_arg_sum + (sqrt_precs[sample_index, obs_index, kernel_index] * (sample[feature_index] - locs[sample_index, obs_index, kernel_index]))**2

                    elif kernel_types[kernel_index] == 1:
                        # categorical kernel
                        total_prob *= cat_probs[sample_index, obs_index, kernel_index + <int>round(sample[feature_index])]

                    kernel_index  += kernel_sizes[kernel_index]  # kernel size can be >1 for a certain param
                    feature_index += 1

                obs_probs += total_prob * prec_prod * exp( - 0.5 * exp_arg_sum) #* inv_sqrt_two_pi**num_continuous

                # we assume 1000 BNN samples, so 100 is 10%
                if sample_index == 100:
                    if 0.01 * obs_probs * inv_sqrt_two_pi**num_continuous < self.lower_prob_bound:
                        probs[obs_index] = 0.01 * obs_probs
                        break
                else:
                    # we take the average across the BNN samples
                    probs[obs_index] = (obs_probs * inv_sqrt_two_pi**num_continuous) / self.num_samples
        return probs

    cpdef get_kernel_contrib(self, np.ndarray sample):

        cdef int obs_index
        cdef double temp_0, temp_1
        cdef double inv_den

        cdef double [:] sample_memview = sample
        probs_sample = self._probs(sample_memview)

        # construct numerator and denominator of acquisition
        cdef double num = 0.
        cdef double den = 0.
        cdef double [:] objs = self.np_objs

        for obs_index in range(self.num_obs):
            temp_0 = objs[obs_index]
            temp_1 = probs_sample[obs_index]
            num += temp_0 * temp_1
            den += temp_1

        inv_den = 1. / (self.inv_vol + den)

        return num, inv_den, probs_sample

    cpdef get_regression_surrogate(self, np.ndarray sample):

        cdef int obs_index
        cdef double temp_0, temp_1
        cdef double inv_den
        cdef double y_pred
        cdef double [:] sample_memview = sample
        probs_sample = self._probs(sample_memview)

        # construct numerator and denominator of acquisition
        cdef double num = 0.
        cdef double den = 0.
        cdef double [:] objs = self.np_objs

        for obs_index in range(self.num_obs):
            temp_0 = objs[obs_index]
            temp_1 = probs_sample[obs_index]
            num += temp_0 * temp_1
            den += temp_1

        y_pred = num / den
        return y_pred

    cpdef get_binary_kernel_densities(self, np.ndarray sample):

        cdef int obs_index
        cdef double density_0 = 0.  # density of feasible
        cdef double density_1 = 0.  # density of infeasible
        cdef double num_0 = 0.
        cdef double num_1 = 0.
        cdef double log_density_0
        cdef double log_density_1

        cdef double [:] sample_memview = sample
        probs_sample = self._probs(sample_memview)

        for obs_index, obj in enumerate(self.np_objs):
            if obj > 0.5:
                density_1 += probs_sample[obs_index]
                num_1 += 1.
            else:
                density_0 += probs_sample[obs_index]
                num_0 += 1.

        # normalize wrt the number of kernels
        log_density_0 = np.log(density_0) - np.log(num_0)
        log_density_1 = np.log(density_1) - np.log(num_1)

        return log_density_0, log_density_1

    cpdef get_probability_of_infeasibility(self, np.ndarray sample, double log_prior_0, double log_prior_1):

        # 0 = feasible, 1 = infeasible
        cdef double prob_infeas
        cdef double log_density_0
        cdef double log_density_1
        cdef double posterior_0
        cdef double posterior_1

        # get log probabilities
        log_density_0, log_density_1 = self.get_binary_kernel_densities(sample)

        # compute unnormalized posteriors
        posterior_0 = exp(log_density_0 + log_prior_0)
        posterior_1 = exp(log_density_1 + log_prior_1)

        # guard against zero division. This may happen if both densities are zero
        if np.log(posterior_0 + posterior_1) < - 230:  # i.e. less then 1e-100
            return exp(log_prior_1) / (exp(log_prior_0) + exp(log_prior_1))  # return prior prob

        # get normalized posterior for prob of infeasible
        prob_infeas = posterior_1 / (posterior_0 + posterior_1)

        return prob_infeas

    cpdef get_probability_of_feasibility(self, np.ndarray sample, double log_prior_0, double log_prior_1):

        # 0 = feasible, 1 = infeasible
        cdef double prob_feas
        cdef double log_density_0
        cdef double log_density_1
        cdef double posterior_0
        cdef double posterior_1

        # get log probabilities
        log_density_0, log_density_1 = self.get_binary_kernel_densities(sample)

        # compute unnormalized posteriors
        posterior_0 = exp(log_density_0 + log_prior_0)
        posterior_1 = exp(log_density_1 + log_prior_1)

        # guard against zero division. This may happen if both densities are zero
        if np.log(posterior_0 + posterior_1) < - 230:  # i.e. less then 1e-100
            return exp(log_prior_1) / (exp(log_prior_0) + exp(log_prior_1))  # return prior prob

        # get normalized posterior for prob of infeasible
        prob_feas = posterior_0 / (posterior_0 + posterior_1)

        return prob_feas
