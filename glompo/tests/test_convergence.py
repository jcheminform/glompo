

from glompo.convergence.basechecker import BaseChecker, _AnyChecker, _AllChecker, _CombiChecker
from glompo.convergence.tmax import MaxSeconds
from glompo.convergence.fmax import MaxFuncCalls
from glompo.convergence.nconv import NOptConverged
from glompo.convergence.nkills import MaxKills
from glompo.convergence.omax import MaxOptsStarted
from glompo.convergence.nkillsafterconv import KillsAfterConvergence

import pytest
import numpy as np


class PlainChecker(BaseChecker):
    def __init__(self):
        super().__init__()
    
    def check_convergence(self, manager) -> bool:
        pass


class TrueChecker(BaseChecker):
    def __init__(self):
        super().__init__()
        self._converged = True

    def check_convergence(self, manager) -> bool:
        return True


class FalseChecker(BaseChecker):
    def check_convergence(self, manager) -> bool:
        return False


class FancyChecker(BaseChecker):
    def __init__(self, a, b, c):
        super().__init__()
        self.a = a
        self.b = b + c

    def check_convergence(self, manager) -> bool:
        pass


def any_checker():
    return _AnyChecker(PlainChecker(), PlainChecker())


def all_checker():
    return _AllChecker(PlainChecker(), PlainChecker())


class TestBase:
    @pytest.mark.parametrize("base1, base2", [(PlainChecker(), PlainChecker()),
                                              (PlainChecker(), any_checker()),
                                              (any_checker(), PlainChecker()),
                                              (PlainChecker(), all_checker()),
                                              (all_checker(), PlainChecker()),
                                              (any_checker(), all_checker())])
    def test_additions(self, base1, base2):
        assert (base1 + base2).__class__.__name__ == "_AnyChecker"

    @pytest.mark.parametrize("base1, base2", [(PlainChecker(), PlainChecker()),
                                              (PlainChecker(), any_checker()),
                                              (any_checker(), PlainChecker()),
                                              (PlainChecker(), all_checker()),
                                              (all_checker(), PlainChecker()),
                                              (any_checker(), all_checker())])
    def test_multiplications(self, base1, base2):
        assert (base1 * base2).__class__.__name__ == "_AllChecker"

    @pytest.mark.parametrize("checker, output", [(PlainChecker(), "PlainChecker()"),
                                                (any_checker(), "(PlainChecker() OR \nPlainChecker())"),
                                                (all_checker(), "(PlainChecker() AND \nPlainChecker())"),
                                                (FancyChecker(1, 2, 3), "FancyChecker(a=1, b=5, c)")])
    def test_str(self, checker, output):
        assert str(checker) == output

    @pytest.mark.parametrize("checker, output", [(PlainChecker(), "PlainChecker() = False"),
                                                 (TrueChecker(), "TrueChecker() = True"),
                                                 (any_checker(), "(PlainChecker() = False OR \nPlainChecker() = "
                                                                 "False)"),
                                                 (all_checker(), "(PlainChecker() = False AND \nPlainChecker() = "
                                                                 "False)"),
                                                 (FancyChecker(1, 2, 3), "FancyChecker(a=1, b=5, c) = False"),
                                                 (FalseChecker() + FalseChecker() * TrueChecker() + TrueChecker() *
                                                  (TrueChecker() + FalseChecker()), "((FalseChecker() = False OR \n"
                                                                                    "(FalseChecker() = False AND \n"
                                                                                    "TrueChecker() = True)) OR \n"
                                                                                    "(TrueChecker() = True AND \n"
                                                                                    "(TrueChecker() = True OR \n"
                                                                                    "FalseChecker() = False)))")])
    def test_conv_str(self, checker, output):
        assert checker.is_converged_str() == output

    def test_combi_init(self):
        with pytest.raises(TypeError):
            _CombiChecker(1, 2, 3)

    def test_convergence(self):
        checker = FalseChecker() + FalseChecker() * TrueChecker() + TrueChecker() * (TrueChecker() + FalseChecker())
        assert checker.check_convergence(None) is True


class TestOthers:
    class Manager:
        def __init__(self):
            self.f_counter = 300
            self.conv_counter = 2
            self.kill_counter = 6
            self.o_counter = 10
            self.t_start = 1584521316.09197
            self.hunt_victims = {1, 2, 3, 5, 6, 7}

    @pytest.mark.parametrize("checker, output", [(MaxSeconds(60), True),
                                                 (KillsAfterConvergence(2, 1), False),
                                                 (MaxFuncCalls(200), True),
                                                 (NOptConverged(2), True),
                                                 (MaxKills(6), True),
                                                 (MaxOptsStarted(10), True)])
    def test_conditions(self, checker, output):
        manager = self.Manager()
        assert checker.check_convergence(manager) is output