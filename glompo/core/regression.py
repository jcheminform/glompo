

""" Contains the DataRegressor used to perform inference and model fitting on provided data. Used to infer the final
    value of a given optimizer.
"""

from typing import *
import warnings

import numpy as np
import emcee
from scipy.optimize import minimize

from .logprob import LogPosterior, LogLikelihood
from ..common.namedtuples import RegressorCacheItem


__all__ = ("DataRegressor",)


class DataRegressor:
    """ Provides a class of methods to regress optimizer data against the function (y0-c*yn)exp(-bt) + c*yn using both
        frequentist and Bayesian techniques.

        Attributes
        ----------
        log_post: Callable
            Function which returns the log-posterior.
        log_like: Callable
            Function returning the value of the log-likelihood.
        mle_cache: Dict[Int, RegressorCacheItem]
            Saves previous runs of the MLE optimization.
            The dictionary keys are optimizer IDs.
            The values are a NamedTuple of:
                1) hash: A hash key of the data used in the last run. Only if the hash of the new data matches the
                         previous run can the answers in the cache be accessed.
                2) result: Tuple of the MLE for the three parameters.
        mcc_cache: Dict[Int, RegressorCacheItem]
            Saves summary results of the MCMC sampling.
            The dictionary keys are optimizer IDs.
            The values are a NamedTuple of:
                1) hash: A hash key of the data used in the last run. Only if the hash of the new data matches the
                         previous run can the answers in the cache be accessed.
                2) result: Sequence of 3 item tuples of sample medians, 5% quantile and 95% quantile value for the
                           three parameters.
    """

    def __init__(self):
        self.log_post = LogPosterior(0, 0.1)
        self.log_like = LogLikelihood()
        self.mle_cache = {}
        self.mcc_cache = {}

    def estimate_mle(self, t: np.ndarray, y: np.ndarray, cache_key: int = None) -> Tuple[float, float, float]:
        """ Returns the Maximum Likelihood Estimation of the exponential function through the given data.
            If multiple attempts at optimization fail a rudimentary fitting is returned based on a least-squares linear
            fit.

            Parameters
            ----------
            t: np.ndarray
                1D array of time or iteration coordinates from the optimizer logs.
            y: np.ndarray
                1D array of function evaluations.
            cache_key: int = None
                If provided the function will look for previous valid results in the cache and return them if
                found. If not found/valid then the calculation proceeds as normal and saves its result into the cache
                using the provided cache key.

            Returns
            -------
            b_est: float
                Estimate for the decay parameter.
            c_est: float
                Estimate for the asymptote parameter.
            s_est: float
                Estimate for the noise parameter.
        """
        hash_key = hash((tuple(t), tuple(y)))
        if cache_key and cache_key in self.mle_cache and hash_key == self.mle_cache[cache_key].hash:
            return self.mle_cache[cache_key].result

        try:
            quick_fit = np.polyfit(t, np.log(y - np.min(y) + 0.01), 1)

            b_est = np.clip(-quick_fit[0], 0.0001, 4.999)
            c_est = 1
            s_est = np.clip(np.mean(np.abs(y - np.exp(quick_fit[1] + quick_fit[0] * t)) / y[0]), 0.0001, 0.4999)
        except ValueError:
            b_est = 0.001
            c_est = y[0] - 0.001
            s_est = 0.001

        for i in range(10):

            if i > 0:
                b_est, c_est, s_est = np.array([b_est, c_est, s_est]) * np.random.uniform(0.75, 1.25, 3)

            mle = minimize(fun=lambda *args: -self.log_like(*args),
                           x0=np.array([b_est, c_est, s_est]),
                           args=(t, y),
                           method='L-BFGS-B',
                           jac=lambda *args: np.array([-self.log_like.db(*args),
                                                       -self.log_like.dc(*args),
                                                       -self.log_like.ds(*args)]),
                           bounds=((0, 5), (0, 1), (0.0001, 0.5)))

            if mle.success:
                if cache_key:
                    self.mle_cache[cache_key] = RegressorCacheItem(hash_key, mle.x)
                return mle.x

        warnings.warn("Multiple attempts to find the MLE failed. Returning rough estimates. These numbers are"
                      " unreliable.", RuntimeWarning)
        if cache_key:
            self.mle_cache[cache_key] = RegressorCacheItem(hash_key, (b_est, c_est, s_est))
        return b_est, c_est, s_est

    def estimate_parameters(self, t: np.ndarray, y: np.ndarray, parms: Optional[str] = None, nwalkers: int = 32,
                            nsteps: int = 5000, cache_key: Any = None) -> Union[Tuple[Tuple[float, float, float], ...],
                                                                                Tuple[float, float, float]]:
        """ Runs the sampler on the log-posterior given the data. Returns an estimate and uncertainty on each
            parameter. The data is saved in the cache if a cache_key is provided.

            The fit is done using Bayesian non-linear regression. An optimization step first finds the MLE and then
            an Affine Invariant Markov Chain Monte Carlo Ensamble algorithm (Goodman & Weare, 2010) is used to sample
            the posterior. Peturbations of the MLE are used as starting points for the walkers.

            Parameters
            ----------
            t: np.ndarray
                1D array of time or iteration coordinates from the optimizer logs.
            y: np.ndarray
                1D array of function evaluations.
            parms: str = 'all'
                The parameter/s and their uncertainties to be returned. Accepts values 'decay', 'noise' and 'asymptote'.
                Returns all if the key is not provided.
            nwalkers: int = 50
                Number of ensemble samplers to be used in a single MCMC walk
            nsteps: int = 5000
                Number of iterations for the sampler.
            cache_key: Any
                If provided the regressor will first check in its cache for the answer. The cache-key is usually the
                optimizer opt_id. If the data used for the previous calculation and this one do not match then the
                calculation is rerun and the data in the cache is updated.

            Returns
            -------
            Depending on the params parameter provided, returns a result tuple for one parameter or a tuple of all
            parameter result tuples. Each result tuples takes the form:
            median:
                The median value sampled by the MCMC sampler.
            lower_quantile:
                The 5% percentile value sampled by the MCMC sampler.
            upper_quantile:
                The 95% percentile value sampled by the MCMC sampler.
        """

        param_dict = {'decay': 0,
                      'asymptote': 1,
                      'noise': 2}

        hash_key = hash((tuple(t), tuple(y)))
        if cache_key and cache_key in self.mcc_cache and hash_key == self.mcc_cache[cache_key].hash:
            posterior = self.mcc_cache[cache_key].result
            if posterior:
                if parms in param_dict:
                    param_key = param_dict[parms]
                    return posterior[param_key]
                return posterior

        starting_pos = np.transpose([np.random.uniform(0, 4, nwalkers),
                                     np.random.uniform(0, 1, nwalkers),
                                     np.random.uniform(0, 1, nwalkers)])

        sampler = emcee.EnsembleSampler(nwalkers=nwalkers,
                                        ndim=3,
                                        log_prob_fn=self.log_post,
                                        args=(t, y))

        try:
            print("Starting run...")
            sampler.run_mcmc(starting_pos, nsteps)
            print("Done")
        except ValueError:
            warnings.warn("MCMC run failed. Returning MLE estimate.", RuntimeWarning)

            b_mle, c_mle, s_mle = self.estimate_mle(t, y, cache_key)
            if parms == 'decay':
                return b_mle, None
            if parms == 'asymptote':
                return c_mle, None
            if parms == 'noise':
                return s_mle, None
            return (b_mle, None), (c_mle, None), (s_mle, None)

        samples = sampler.get_chain(discard=1000, flat=True)

        median = np.median(samples, axis=0)
        quan_l = np.quantile(samples, 0.05, axis=0)
        quan_u = np.quantile(samples, 0.95, axis=0)

        result = tuple(tuple(set_) for set_ in np.transpose([median, quan_l, quan_u]))

        if cache_key:
            self.mcc_cache[cache_key] = RegressorCacheItem(hash_key, result)

        if parms in param_dict:
            key = param_dict[parms]
            return median[key], quan_l[key], quan_u[key]

        return result
