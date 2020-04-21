

from typing import *
import numpy as np
from .basegenerator import BaseGenerator
from ..common.helpers import is_bounds_valid


__all__ = ("RandomGenerator",)


class RandomGenerator(BaseGenerator):
    """ Generates random starting points within given bounds. """

    def __init__(self, bounds: Sequence[Tuple[float, float]]):
        self.n_params = len(bounds)
        if is_bounds_valid(bounds):
            self.bounds = np.array(bounds)

    def generate(self) -> np.ndarray:
        calc = (self.bounds[:, 1] - self.bounds[:, 0]) * np.random.random(self.n_params) + self.bounds[:, 0]
        return calc
