import warnings
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Union

import numpy as np

from ..common.wrappers import needs_optional_package

try:
    import matplotlib.pyplot as plt

    plt.rcParams['font.size'] = 8
    plt.rcParams['mathtext.fontset'] = 'cm'
    plt.rcParams['savefig.format'] = 'svg'
    plt.rcParams['figure.figsize'] = 6.7, 3.35
except (ModuleNotFoundError, ImportError):
    pass

__all__ = ('EstimatedEffects',)

SpecialSlice = Union[int, str, List[int], List[str], slice]


class EstimatedEffects:
    # TODO Numpy warnings?
    # TODO Complete parameters
    # TODO Complete attributes
    """ Implementation of Morris screening strategy.
    Based on the original work of Morris (1991) but includes extensions published over the years.
    Global sensitivity method for expensive functions. Uses minimal number of function evaluations to develop a good
    proxy for the total sensitivity of each input factor. Produces three sensitivity measures (:math:`\\mu`,
    :math:`\\mu^*` and :math:`\\sigma`) that are able to capture magnitude and direction the sensitivity, as well as
    nonlinear and interaction effects. The user is directed to the references below for a detailed explanation of the
    meaning of each of these measures.

    Parameters
    ----------
    groupings
        :math:`k \\times g` array grouping each :math:`k` factor into one and only one of the :math:`g` groups.
        See :attr:`groupings`.

        .. warning::

           The use of groups comes at the cost of the :math:`\\mu` and :math:`\\sigma` metrics. They are unobtainable
           in this regime because it is not possible to define . Only :math:`\\mu^*` is accessible.

    trajectory_style
        Type of trajectories used in the sensitivity analysis. Accepts 'radial' and 'stairs'

    References
    ----------
    Morris, M. D. (1991). Factorial Sampling Plans for Preliminary Computational Experiments. *Technometrics*, 33(2),
    161–174. https://doi.org/10.1080/00401706.1991.10484804

    Campolongo, F., Cariboni, J., & Saltelli, A. (2007). An effective screening design for sensitivity analysis of large
    models. *Environmental Modelling & Software*, 22(10), 1509–1518. https://doi.org/10.1016/j.envsoft.2006.10.004

    Saltelli, A., Ratto, M., Andres, T., Campolongo, F., Cariboni, J., Gatelli, D., Saisana, M., & Tarantola, S. (2007).
    Global Sensitivity Analysis. The Primer (A Saltelli, M. Ratto, T. Andres, F. Campolongo, J. Cariboni, D. Gatelli,
    M. Saisana, & S. Tarantola (eds.)). *John Wiley & Sons, Ltd.* https://doi.org/10.1002/9780470725184

    Ruano, M. V., Ribes, J., Seco, A., & Ferrer, J. (2012). An improved sampling strategy based on trajectory design for
    application of the Morris method to systems with many input factors. *Environmental Modelling & Software*, 37,
    103–109. https://doi.org/10.1016/j.envsoft.2012.03.008

    Vanrolleghem, P. A., Mannina, G., Cosenza, A., & Neumann, M. B. (2015). Global sensitivity analysis for urban water
    quality modelling: Terminology, convergence and comparison of different methods. *Journal of Hydrology*, 522,
    339–352. https://doi.org/10.1016/J.JHYDROL.2014.12.056

    Attributes
    ----------
    dims: int
        The number of input factors for which sensitivity is being tested. Often referred to as :math:`k` throughout the
        documentation here to match literature.
    out_dims: int
        Dimensionality of the output if one would like to investigate factor sensitivities against multiple function
        responses. Often reffered to as :math:`h` in the documentation of equations.
    outputs : numpy.ndarray
        :math:`r \\times (k+1) \\times h` array of function evaluations corresponding to the input factors in
        :attr:`trajectories`. :math:`h` is the dimensionality of the outputs.
    """

    @property
    def mu(self):
        """ Shortcut access to the Estimated Effects :meth:`\\mu` metric using all trajectories, for all input
        dimensions, taking the average along output dimensions. Equivalent to: :code:`ee['mu', :, 'mean', :]`

        Warnings
        --------
        Unavailable if using groups, will raise a :obj:`ValueError`. See :attr:`groupings`.
        """
        return self['mu', :, 'mean', :].squeeze()

    @property
    def mu_star(self):
        """ Shortcut access to the Estimated Effects :meth:`\\mu^*` metric using all trajectories, for all input
        dimensions, taking the average along output dimensions. Equivalent to:
        :code:`ee['mu_star', :, 'mean', :]`
        """
        return self['mu_star', :, 'mean', :].squeeze()

    @property
    def sigma(self):
        """ Shortcut access to the Estimated Effects :meth:`\\sigma` metric using all trajectories, for all input
        dimensions, taking the average along output dimensions. Equivalent to: :code:`ee['sigma', :, 'mean', :]`

        Warnings
        --------
        Unavailable if using groups, will raise a :obj:`ValueError`. See :attr:`groupings`.
        """
        return self['sigma', :, 'mean', :].squeeze()

    @property
    def r(self) -> int:
        """ The number of trajectories in the set. """
        return len(self.trajectories)

    @property
    def k(self) -> int:
        """ Pseudonym for :attr:`dims` """
        return self.dims

    @property
    def h(self) -> int:
        """ Pseudonym for :attr:`out_dims` """
        return self.out_dims

    @property
    def g(self) -> int:
        """ The number of factor groups if one is not analysing each factor individually. """
        return self.groupings.shape[1]

    @property
    def groupings(self) -> np.ndarray:
        """ :math:`k \\times g` array grouping each :math:`k` factor into one and only one of the :math:`g` groups. This
        allows one to perform a sensitivity analysis with far fewer function evaluations and sensitivities are reported
        for groups rather than factors.

        .. note::

           This attribute cannot be altered. It is not possible to go from grouped analysis to a individual factor
           analysis (or vice versa), or to a different grouping due to the manner in which trajectories are constructed.
           One would need to start a new :class:`EstimatedEffects` instance and generate new trajectories to analyze a
           different grouping.
        """
        return self._groupings

    @property
    def is_grouped(self) -> bool:
        """ :obj:`True` if a grouped factor analysis is being conducted. """
        return self._is_grouped

    @property
    def is_converged(self, out_index: SpecialSlice = 'mean') -> bool:
        """ Converged if the instance has enough trajectories for the factor ordering to be stable.
        Returns :obj:`True` if the change in :meth:`position_factor` over the last 10 trajectory entries is smaller
        than :attr:`convergence_threshold`.

        Parameters
        ----------
        out_index
            See :meth:`__get_item__`.
        """
        # TODO Rethink definition of converged
        return np.squeeze(self.position_factor(self.r - 10, self.r, out_index) < self.convergence_threshold)

    @property
    def classification(self, out_index: Union[int, str] = 'mean') -> Dict[str, np.ndarray]:
        """ Returns a dictionary with each factor index classified as :code:`'important'`, :code:`'interacting'` and
        :code:`'non-influential'`. Follows the definitive classification system of
        `Vanrolleghem et al. (2105) <https://doi.org/10.1016/J.JHYDROL.2014.12.056>`_.

        Categories are defined as follows:

        :code:`'important'`:
           These factors have a linear effect on the model output.

        :code:`'interacting'`:
           These factors have a nonlinear effect on the model output.

        :code:`'non-influential'`:
            These factors do not have a significant impact on model output.

        Parameters
        ----------
        out_index
            Output dimension along which to do the classification.

        Warnings
        --------
        Unavailable if using groups, will raise a :obj:`ValueError`. See :attr:`groupings`.

        References
        ----------
        Vanrolleghem, P. A., Mannina, G., Cosenza, A., & Neumann, M. B. (2015). Global sensitivity analysis for urban
        water quality modelling: Terminology, convergence and comparison of different methods. *Journal of Hydrology*,
        522, 339–352. https://doi.org/10.1016/J.JHYDROL.2014.12.056
        """
        mu, ms, sd = self[:, :, out_index, :]
        return {'important': np.argwhere((ms > self.ct) & (sd < ms * np.sqrt(self.r) / 2)).ravel(),
                'interacting': np.argwhere((ms > self.ct) & (sd >= ms * np.sqrt(self.r) / 2)).ravel(),
                'non-influential': np.argwhere(ms < self.ct).ravel()}

    @property
    def ranking(self, out_index: SpecialSlice = 'mean') -> np.ndarray:
        """ Returns factor indices in descending order of their influence on the outputs.

        Parameters
        ----------
        out_index
            See :meth:`__get_item__`.
        """
        return np.squeeze(self[1, :, out_index].argsort()[:, -1::-1] + 1)

    def __init__(self, input_dims: int,
                 output_dims: int,
                 groupings: Optional[np.ndarray] = None,
                 convergence_threshold: float = 0,
                 cutoff_threshold: float = 0.1,
                 trajectory_style: str = 'radial'):
        self._metrics = np.array([[[]]])

        self.trajectories = np.array([])
        self.dims: int = input_dims
        self.traj_style = trajectory_style
        self._groupings = groupings if groupings is not None else np.identity(input_dims)
        self._is_grouped = groupings is not None
        if np.sum(self._groupings) != input_dims:
            raise ValueError("Invalid grouping matrix, each factor must be in exactly 1 group.")

        self.outputs = np.array([])
        self.out_dims = output_dims

        self.convergence_threshold = convergence_threshold
        self.ct = cutoff_threshold

    def __getitem__(self, item):
        """ Retrieves the sensitivity metrics (:math:`\\mu, \\mu^*, \\sigma`) for a particular calculation configuration
        The indexing has a maximum length of 4:

        * First index (code:`metric_index`):
            Indexes the metric. If :code:`:` is used, all metrics are returned.
            Also accepts strings which are paired to the following corresponding ints:
            === ===
            int str
            === ===
            0   'mu'
            1   'mu_star'
            2   'sigma'
            === ===

        * Second index (code:`factor_index`):
           Indexes the factor. :code:`:` returns metrics for all factors.

        * Third index (code:`out_index`):
            Only applicable if a multidimensional output is being investigated. Determines which metrics to use in the
            calculation. Accepts one of the following:

               * Any integers or slices of 0, 1, ... :math:`h`: The metrics for the outputs at the corresponding index
                 will be used.

               * :code:`'mean'`: The metrics will be averaged across the output dimension.

               * :code:`:, 'all', None`: Metrics will be returned for all outputs.

        * Fourth Index (code:`traj_index`):
           Which trajectories to use in the calculation. If not supplied or :code:`:`, all trajectories will be used.
           Accepts slices as well as lists of integers. Helpful for bootstrapping.

        Parameters
        ----------
        item
            Tuple of slices and indices. Maximum length of 4.

        Returns
        -------
        numpy.ndarray
            :math:`m \\times \\times k \\times h` array of sensitivity metrics where :math:`m` is the metric, :math:`k`
            is the factor and :math:`h` is the output dimensionality.

        Raises
        ------
        ValueError
            If an attempt is made to access :math:`\\mu` or :math:`\\sigma` while using groups.

        Examples
        --------
        Return all metrics for all factors and outputs, using all available trajectories:

        >>> ee[]

        Return :math:`\\mu^*` for the second factor, averaged over all outputs:

        >>> ee[1, 1, 'mean']

        Return :math:`\\mu` and :math:`\\sigma` metrics for the first three factors and output 6:

        >>> ee[['mu', 'sigma'], 0:3, 6]

        Return the metrics using the first 20 trajectories only:

        >>> ee[:, :, :, :20]

        """
        if self.trajectories.size == 0:
            warnings.warn("Please add at least one trajectory before attempting to access calculations.", UserWarning)
            return np.array([[[]]])

        m, h, k, t = (*item, *(slice(None),) * (4 - len(item)))

        if not isinstance(m, slice):
            m = np.atleast_1d(m)
            for s, i in (('mu', 0), ('mu_star', 1), ('sigma', 2)):
                m[m == s] = i
            m = m.astype(int)

        if self.is_grouped and (isinstance(m, slice) or any([i in m for i in [0, 2]])):
            raise ValueError('Cannot access mu and sigma metrics if groups are being used')

        mean_out = k == 'mean'
        k = slice(None) if mean_out or k == 'all' or k is None else k

        # Attempt to access existing results
        if t == slice(None) and self._metrics.size > 0:
            metrics = self._metrics
        else:
            metrics = self._calculate(k, t)
            if k == slice(None) and t == slice(None):
                # Save results to cache if a full calculation was done.
                self._metrics = metrics

        metrics = metrics[m, k, h]

        if mean_out:
            metrics = np.mean(metrics, 2)

        return metrics

    def add_trajectory(self, trajectory: np.ndarray, outputs: np.ndarray):
        """ Add a trajectory of points and their corresponding model output to the calculation.

        Parameters
        ----------
        trajectory
            A trajectory of points as produced by one of the trajectory generation functions (see :mod:`.trajectories`).
            Should have a shape of :math:`(k+1) \\times k` where :math:`k` is the number of factors / dimensions of the
            input.
        outputs
            :math:`(k+1) \\times h` model outputs corresponding to the points in the `trajectory`. Where :math:`h` is
            the dimensionality of the outputs.

        Raises
        ------
        ValueErrror
            If `trajectory` or `outputs` do not match the dimensions above.

        Notes
        -----
        The actual calculation of the Estimated Effects metrics is not performed in this method. Add new trajectories is
        essentially free. The calculation is only performed the moment the user attempts to access any of the metrics.
        The results of the calculation are held in memory, thus if the number of trajectories remains unchanged, the
        user may continue accessing the metrics at no further cost.
        """
        # Clear old results
        self._metrics = np.array([[[]]])

        if trajectory.shape != (self.g + 1, self.k):
            raise ValueError(f"Cannot parse trajectory with shape {trajectory.shape}, must be ({self.g + 1}, "
                             f"{self.k}).")
        if self.h > 1 and outputs.shape != (self.g + 1, self.h):
            raise ValueError(f"Cannot parse outputs with shape {outputs.shape}, must be ({self.g + 1}, {self.h})")

        if self.h == 1 and (outputs.shape != (self.g + 1, self.h) or outputs.shape != (self.g + 1,)):
            raise ValueError(f"Cannot parse outputs with length {len(outputs)}, {self.g + 1} values expected.")

        if self.h == 1:
            outputs = outputs.reshape((self.g + 1, self.h))

        if len(self.trajectories) > 0:
            self.trajectories = np.append(self.trajectories, [trajectory], axis=0)
            self.outputs = np.append(self.outputs, [outputs], axis=0)
        else:
            self.trajectories = np.array([trajectory])
            self.outputs = np.array([outputs])

    def generate_add_trajectory(self, style: Optional[None]):
        """ Convenience method to automatically generate a trajectory and add it to the calculation. """

    def build_until_convergence(self,
                                func: Callable[[np.ndarray], float],
                                r_max: int):
        """  """
        # TODO Implement
        raise NotImplementedError

    def position_factor(self, i: int, j: int, out_index: SpecialSlice = 'mean') -> np.ndarray:
        """ Returns the position factor metric.
        This is a measure of convergence. Measures the changes between the factor rankings obtained when using `i`
        trajectories and `j` trajectories.  Where `i` and `j` are a number of trajectories such that
        :math:`0 < i < j \\leq M` where :math:`M` is the number of trajectories added to the calculation.

        The position factor metric (:math:`PF_{r_i \\shortrightarrow r_j}`) is calculated as:

        .. math::

           PF_{r_i \\shortrightarrow r_j} = \\sum_{k=1}^k \\frac{2(P_{k,i} - P_{k,j})}{P_{k,i} + P_{k,j}}

        where:
           :math:`P_{k,i}` is the ranking of factor :math:`k` using :math:`i` trajectories.
           :math:`P_{k,j}` is the ranking of factor :math:`k` using :math:`j` trajectories.

        Parameters
        ----------
        i
            Initial trajectory index from which to start the comparison.
        j
            Final trajectory index against which the comparision is made.
        out_index
            See :meth:`__get_item__`.

        References
        ----------
        Ruano, M. V., Ribes, J., Seco, A., & Ferrer, J. (2012). An improved sampling strategy based on trajectory design
        for application of the Morris method to systems with many input factors. *Environmental Modelling & Software*,
        37, 103–109. https://doi.org/10.1016/j.envsoft.2012.03.008
        """
        # TODO Being calculated correctly?
        mus_i = self[1, :, out_index, :i]
        mus_j = self[1, :, out_index, :j]

        pos_i = np.abs(mus_i.argsort().argsort() - self.g)
        pos_j = np.abs(mus_j.argsort().argsort() - self.g)

        return np.sum(2 * (pos_i - pos_j) / (pos_i + pos_j), axis=1).squeeze()

    @needs_optional_package('matplotlib')
    def plot_sensitivities(self,
                           path: Union[Path, str] = 'sensitivities',
                           out_index: SpecialSlice = 'mean',
                           factor_labels: Optional[Sequence[str]] = None):
        """ Saves a sensitivity plot.
        The plot is a scatter of :math:`\\mu^*` versus :math:`\\sigma` with dividers between 'important', 'interacting'
        and 'non-influential' categories.

        Parameters
        ----------
        path
            If one plot is being produced (see `out_index`) this is interpreted as the filename with which to save the
            figure. If multiple plots are produced for all the outputs then this is interpreted as a directory into
            which the figures will be saved.
        out_index
            See :meth:`__get_item__`. If :obj:`None` or :code:`'all'`, one plot will be created for each output.
        factor_labels
            Optional sequence of descriptive names for each factor to add to the figure. Defaults to the factor's
            index position.

        Warnings
        --------
        Unavailable if using groups, will raise a :obj:`ValueError`. See :attr:`groupings`.

        References
        ----------
        Vanrolleghem, P. A., Mannina, G., Cosenza, A., & Neumann, M. B. (2015). Global sensitivity analysis for urban
        water quality modelling: Terminology, convergence and comparison of different methods. *Journal of Hydrology*,
        522, 339–352. https://doi.org/10.1016/J.JHYDROL.2014.12.056
        """
        self._plotting_core(path, out_index, self._plot_sensitivities_stub, factor_labels=factor_labels)

    @needs_optional_package('matplotlib')
    def plot_rankings(self,
                      path: Union[Path, str] = 'ranking',
                      out_index: SpecialSlice = 'mean',
                      factor_labels: Optional[Sequence[str]] = None):
        """ Saves the factor rankings as a plot.
        Plots the ordered :math:`\\mu^*` values against their corresponding parameter indices.

        Parameters
        ----------
        See :meth:`plot_sensitivities`.
        """
        self._plotting_core(path, out_index, self._plot_ranking_stub, factor_labels=factor_labels)

    @needs_optional_package('matplotlib')
    def plot_convergence(self,
                         path: Union[Path, str] = 'sensi_convergence',
                         out_index: SpecialSlice = 'mean',
                         step_size: int = 10,
                         out_labels: Optional[Sequence[str]] = None):
        """ Plots the evolution of the Position Factor ($PF_{i \\to j}$) metric as a function of increasing
        number of trajectories.

        Parameters
        ----------
        path
            Path to file into which the plot should be saved.
        out_index
            See :meth:`__get_item__`. If multiple output dimensions are selected, they will be included on the same plot
        step_size
            The step size in number of trajectories when calculating the position factor.
        out_labels
            Optional sequence of descriptive labels for the plot legend corresponding to the outputs selected to be
            plotted. Defaults to 'Output 0', 'Output 1', 'Output 2', ...

        Notes
        -----
        The Position Factor metric is a measure of how much rankings have changed between the rankings calculated
        using :math:`i` trajectories, and the rankings calculated using :math:`j` trajectories sometime later. Thus, if
        `step_size` is 10 then the plot would show the evolution of the Position Factor at:
        :math:`0 \\to 10, 10 \\to 20, 20 \\to 30, ...`

        See Also
        --------
        :meth:`position_factor`
        """
        steps = np.clip([(i, i + step_size) for i in range(0, self.r, step_size)], None, self.r)
        pf = np.array([self.position_factor(*pair, out_index) for pair in steps])

        fig, ax = plt.subplots()
        fig: plt.Figure
        ax: plt.Axes

        ax.set_title('Convergence of sensitivity rankings ($PF$ v $r$)')
        ax.set_xlabel('Trajectories Compared ($i \\to j$)')
        ax.set_ylabel('Position Factor ($PF_{i \\to j}$)')

        ax.plot(pf, marker='.')
        if len(pf) > 1:
            labs = out_labels if out_labels is not None else [f'Output {i}' for i in range(pf.shape[0])]
            ax.legend(labels=labs)

        ax.set_xticks([i for i, _ in enumerate(steps)])
        ax.set_xticklabels([f'{s[0]}$\\to${s[1]}' for s in steps])

        fig.tight_layout()
        fig.savefig(path)

        plt.close(fig)

    def invert(self):
        """  """
        # TODO Implement

    def _calculate(self,
                   out_index: SpecialSlice,
                   traj_index: Union[int, slice, List[int]]) -> np.ndarray:
        """ Calculates the Estimated Effects metrics (:math:`\\mu`, :math:`\\mu^*` and :math:`\\sigma`).

        Parameters
        ----------
        out_index
            See :meth:`__get_item__`.
        traj_index
            See :meth:`__get_item__`.

        Returns
        -------
        numpy.ndarray
            :math:`m \\times \\times k \\times h` array of sensitivity metrics where :math:`m` is the metric, :math:`k`
            is the factor and :math:`h` is the output dimensionality.

            Metrics are ordered: :math:`\\mu`, :math:`\\mu^*` and :math:`\\sigma`.

        Notes
        -----
        If `traj_index` is provided then the results will *not* be saved as the :attr:`mu`, :attr:`mu_star` and :
        attr:`sigma` attributes of the class.

        If all available trajectories are used *and* all metrics for all the outputs are calculated, then the results
        are saved into the above mentioned attributes.

        If a user attempts to access any of the attributes (and the number of trajectories has changed since the last
        call), this method is automatically called for all available trajectories. In other words, there is never any
        risk of accessing metrics which are out-of-sync with the number of trajectories appended to the calculation.
        """
        if self.traj_style == 'stairs':
            x_diffs = self.trajectories[traj_index, :-1] - self.trajectories[traj_index, 1:]
            y_diffs = self.outputs[traj_index, :-1, out_index] - self.outputs[traj_index, 1:, out_index]

        else:  # Radial style trajectories
            x_diffs = self.trajectories[traj_index, 0] - self.trajectories[traj_index, 1:]
            y_diffs = self.outputs[traj_index, 0, out_index] - self.outputs[traj_index, 1:, out_index]

        where = np.where(x_diffs @ self.groupings)[0::2]
        if not self.is_grouped:  # If not using groups
            x_diffs = np.sum(x_diffs, axis=2)
        else:
            x_diffs = np.sqrt(np.sum(x_diffs ** 2, axis=2))

        ee = y_diffs / x_diffs[:, :, None]
        ee[where] = ee.copy().ravel().reshape(-1, self.h)

        mu = np.mean(ee, axis=0)
        mu_star = np.mean(np.abs(ee), axis=0)
        sigma = np.std(ee, axis=0, ddof=1)

        return np.array([mu, mu_star, sigma])

    def _plotting_core(self, path: Union[Path, str], out_index: SpecialSlice, plot_stub: Callable[..., None], **kwargs):
        """ Most plot function require the same looping and gathering of metrics, this is done here and then passed
        to the `plot_stub` method which have the individualized plot commands.
        """
        if not self.is_grouped:
            metrics = np.atleast_3d(self[:, :, out_index])
        else:
            metrics = np.atleast_3d(self[['mu_star'], :, out_index])

        path = Path(path)
        is_multi = False
        if metrics.shape[2] > 1:
            path.mkdir(exist_ok=True, parents=True)
            is_multi = True

        for i in range(metrics.shape[2]):
            fig, ax = plt.subplots(figsize=(6.7, 6.7))
            fig: plt.Figure
            ax: plt.Axes

            if self.is_grouped:
                plot_stub(fig, ax, mu_star=metrics[0, :, i], **kwargs)
            else:
                plot_stub(fig, ax, mu=metrics[0, :, i], mu_star=metrics[1, :, i], sigma=metrics[2, :, i], **kwargs)

            fig.tight_layout()
            fig.savefig(path / f'{i:03}' if is_multi else path)
            plt.close(fig)

    def _plot_sensitivities_stub(self, fig: plt.Figure, ax: plt.Axes,
                                 mu: Optional[np.ndarray] = None,
                                 mu_star: Optional[np.ndarray] = None,
                                 sigma: Optional[np.ndarray] = None,
                                 factor_labels: Optional[Sequence[str]] = None):
        ax.set_title("Sensitivity classification of all input factors.")
        ax.set_xlabel("$\\mu^*$")
        ax.set_ylabel("$\\sigma$")

        # Influencial / Non-influencial Line
        max_sd = max(sigma)
        ax.vlines(self.ct, 0, max_sd, color='red')
        ax.annotate('Non-Influential   ', (self.ct, max_sd), ha='right')

        # Linear / Nonlinear Effect Line
        max_mu = max(mu_star)
        ax.plot([0, max_mu], [0, max_mu * np.sqrt(self.r) / 2], color='red')
        ax.annotate('   Interacting', (self.ct, max_sd), ha='left')
        ax.annotate('   Important', (self.ct, 0), ha='left')

        # Sensitivities
        ax.scatter(mu_star, sigma, marker='.')
        labs = factor_labels if factor_labels is not None else range(self.g)
        for j, lab in enumerate(labs):
            ax.annotate(lab, (mu_star[j], sigma[j]), fontsize=9)

    def _plot_ranking_stub(self, fig: plt.Figure, ax: plt.Axes,
                           mu: Optional[np.ndarray] = None,
                           mu_star: Optional[np.ndarray] = None,
                           sigma: Optional[np.ndarray] = None,
                           factor_labels: Optional[Sequence[str]] = None):
        ax.set_title("Parameter Ranking")
        ax.set_xlabel("Parameter Index")
        ax.set_ylabel("$\\mu^*$")

        i_sort = np.argsort(mu_star)
        if factor_labels is None:
            labs = i_sort.astype(str)
        else:
            labs = np.array(factor_labels)[i_sort]
        ax.bar(labs, mu_star[i_sort])