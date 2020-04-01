

from .basehunter import BaseHunter
from ..core.logger import Logger


__all__ = ("ValBelowGPR",)


class ValBelowGPR(BaseHunter):

    def __init__(self):
        """ Returns True if the current best value seen by the hunter falls below the 95% confidence threshold of the
            victim.
        """

    def is_kill_condition_met(self, log: Logger, hunter_opt_id: int, victim_opt_id: int) -> bool:
        vals = log.get_history(hunter_opt_id, "fx_best")
        if len(vals) > 0:
            mu, sigma = victim_gpr.estimate_mean()
            threshold = mu - 2 * sigma

            return vals[-1] < threshold

        return False
