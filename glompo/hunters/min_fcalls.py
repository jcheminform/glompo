
from .basehunter import BaseHunter
from ..core.logger import Logger
from ..core.regression import DataRegressor


__all__ = ("MinFuncCalls",)


class MinFuncCalls(BaseHunter):

    def __init__(self, min_pts: int):
        """ Returns True if the victim has evaluated the objective function at least min_pts times. """
        super().__init__()
        if min_pts > 0 and isinstance(min_pts, int):
            self.min_pts = min_pts
        else:
            raise ValueError("min_pts must be a positive integer.")

    def __call__(self,
                 log: Logger,
                 regressor: DataRegressor,
                 hunter_opt_id: int,
                 victim_opt_id: int) -> bool:

        fcalls = log.get_history(victim_opt_id, "f_call_opt")[-1]
        self._last_result = fcalls >= self.min_pts
        return self._last_result