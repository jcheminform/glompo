import datetime
from pathlib import Path

import numpy as np
import pytest
import yaml

import glompo.core.optimizerlogger
from glompo.core.optimizerlogger import BaseLogger
from glompo.optimizers.baseoptimizer import BaseOptimizer
from glompo.optimizers.cmawrapper import CMAOptimizer


# from glompo.optimizers.gflswrapper import GFLSOptimizer

# TODO Remove optimizers from logger test


class TestLogger:

    @pytest.fixture(scope='class')
    def filled_log(self):
        log = BaseLogger()

        # opt0 = GFLSOptimizer(0)
        opt1 = CMAOptimizer(1)
        opt2 = BaseOptimizer

        # log.add_optimizer(0, type(opt0).__name__, datetime.datetime.now())
        log.add_optimizer(1, type(opt1).__name__, datetime.datetime.now())
        log.add_optimizer(2, type(opt2).__name__, datetime.datetime.now())

        for i in range(1, 30):
            log.put_iteration(0, i, i, i, i, np.exp(i))
        log.put_metadata(0, "Stop Time", datetime.datetime.now())
        log.put_metadata(0, "End Condition", "GloMPO Termination")

        for i in range(1, 30):
            log.put_iteration(1, i, i, i, [i, i ** 2], np.sin(i))
        log.put_metadata(1, "Stop Time", datetime.datetime.now())
        log.put_metadata(1, "End Condition", "Optimizer convergence")

        for i in range(1, 30):
            log.put_iteration(2, i, i, i, np.array([i ** 2, i / 2 + 3.14]), np.tan(i))
        log.put_metadata(2, "Stop Time", datetime.datetime.now())
        log.put_metadata(2, "End Condition", "fmax condition met")

        log.put_message(1, "This is a test of the logger message system")
        return log

    def test_save(self, filled_log, tmp_path):
        filled_log.save_optimizer(Path(tmp_path, "success"), 1)
        filled_log.save_optimizer(Path(tmp_path, "all"))

        Path(tmp_path, "all", "0_GFLSOptimizer.yml").exists()
        Path(tmp_path, "all", "1_CMAOptimizer.yml").exists()
        Path(tmp_path, "all", "2_ABCMeta.yml").exists()
        Path(tmp_path, "success.yml").exists()

    def test_save_summary(self, filled_log, tmp_path):
        filled_log.save_summary(Path(tmp_path, "summary.yml"))
        with Path(tmp_path, "summary.yml").open("r") as file:
            data = yaml.safe_load(file)
        assert len(data) == 3
        assert all([kw in data[0] for kw in ('end_cond', 'f_calls', 'f_best', 'x_best')])

    def test_history0(self, filled_log):
        hist = filled_log.get_history(0)
        assert [*hist][0] == 1
        assert isinstance([*hist.values()][4], dict)
        assert [*hist.values()][3]['fx'] == np.exp(4)
        assert [*hist.values()][7]['x'] == [8]

    def test_history1(self, filled_log):
        hist = filled_log.get_history(1, "fx")
        assert hist[3] == np.sin(4)

    def test_history2(self, filled_log):
        filled_log.put_iteration(1, 30, 30, 30, [30, 30 ** 2], -5)

        hist = filled_log.get_history(1, "i_best")
        assert hist[29] == 30

        hist = filled_log.get_history(1, "fx_best")
        assert hist[-1] == -5

    def test_history3(self, filled_log):
        hist = filled_log.get_history(1, "x")
        assert hist[4] == [5, 25]

    def test_history4(self, filled_log):
        with pytest.raises(KeyError):
            filled_log.get_history(1, "not a key")

    def test_message(self, filled_log):
        assert filled_log._storage[1].messages[0] == "This is a test of the logger message system"

    def test_len(self, filled_log):
        assert len(filled_log) == 3

    def test_metadata(self, filled_log):
        assert filled_log.get_metadata(0, "End Condition") == "GloMPO Termination"

    @pytest.mark.skipif(not glompo.core.optimizerlogger.HAS_MATPLOTLIB,
                        reason="Matplotlib package needed to use these features.")
    def test_plot_no_matplotlib(self, filled_log, monkeypatch):
        monkeypatch.setattr(glompo.core.optimizerlogger, "HAS_MATPLOTLIB", False)
        with pytest.warns(ImportWarning, match="Matplotlib not present cannot create plots."):
            filled_log.plot_trajectory("")

        with pytest.warns(ImportWarning, match="Matplotlib not present cannot create plots."):
            filled_log.plot_optimizer_trials()

    @pytest.mark.skipif(not glompo.core.optimizerlogger.HAS_MATPLOTLIB,
                        reason="Matplotlib package needed to use these features.")
    @pytest.mark.parametrize("log_scale", [True, False])
    @pytest.mark.parametrize("best_fx", [True, False])
    def test_plot_traj(self, filled_log, log_scale, best_fx, tmp_path):
        filled_log.plot_trajectory(Path(tmp_path, 'traj.png'), log_scale, best_fx)
        assert Path(tmp_path, 'traj.png').exists()

    @pytest.mark.skipif(not glompo.core.optimizerlogger.HAS_MATPLOTLIB,
                        reason="Matplotlib package needed to use these features.")
    def test_plot_opts(self, tmp_path, filled_log):
        filled_log.plot_optimizer_trials(tmp_path)
        for i in range(3):
            assert Path(tmp_path, f"opt{i}_parms.png").exists()