# Copyright 2021-2023 Lawrence Livermore National Security, LLC and other
# MuyGPyS Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: MIT

"""
Hyperparameters and kernel functors

Defines the Matérn kernel functor (inheriting
:class:`~MuyGPyS.gp.kernels.kernel_fn.KernelFn`) that transform crosswise
distance matrices into cross-covariance matrices and pairwise distance matrices
into covariance or kernel matrices.

See the following example to initialize an :class:`MuyGPyS.gp.kernels.Matern`
object.

Example:
    >>> from MuyGPyS.gp.kernels import Matern
    >>> kern = Matern(
    ...         nu = {"val": "log_sample", "bounds": (0.1, 2.5)},
    ...         length_scale = {"val": 7.2},
    ...         metric = "l2",
    ... }

One uses a previously computed `pairwise_dists` tensor (see
:func:`MuyGPyS.gp.distance.pairwise_distance`) to compute a kernel tensor whose
second two dimensions contain square kernel matrices. Similarly, one uses a
previously computed `crosswise_dists` matrix (see
:func:`MuyGPyS.gp.distance.crosswise_distance`) to compute a cross-covariance
matrix. See the following example, which assumes that you have already
constructed the distance `numpy.nparrays` and the kernel `kern` as shown above.

Example:
    >>> K = kern(pairwise_dists)
    >>> Kcross = kern(crosswise_dists)
"""

from typing import Callable, Dict, List, Optional, Tuple, Union

import MuyGPyS._src.math as mm
from MuyGPyS._src.gp.kernels import (
    _matern_05_fn,
    _matern_15_fn,
    _matern_25_fn,
    _matern_inf_fn,
    _matern_gen_fn,
)
from MuyGPyS.gp.kernels.hyperparameters import (
    _init_hyperparameter,
    Hyperparameter,
)
from MuyGPyS.gp.kernels.kernel_fn import KernelFn


class Matern(KernelFn):
    """
    The Màtern kernel.

    The Màtern kernel includes a length scale parameter :math:`\\ell>0` and an
    additional smoothness parameter :math:`\\nu>0`. :math:`\\nu` is inversely
    proportional to the smoothness of the resulting function. The Màtern kernel
    also depends upon a distance function :math:`d(\\cdot, \\cdot)`.
    As :math:`\\nu\\rightarrow\\infty`, the kernel becomes equivalent to
    the :class:`RBF` kernel. When :math:`\\nu = 1/2`, the Matérn kernel
    becomes identical to the absolute exponential kernel.
    Important intermediate values are
    :math:`\\nu=1.5` (once differentiable functions)
    and :math:`\\nu=2.5` (twice differentiable functions).
    NOTE[bwp] We currently assume that the kernel is isotropic, so
    :math:`|\\ell| = 1`.

    The kernel is defined by

    .. math::
         k(x_i, x_j) =  \\frac{1}{\\Gamma(\\nu)2^{\\nu-1}}\\Bigg(
         \\frac{\\sqrt{2\\nu}}{l} d(x_i , x_j )
         \\Bigg)^\\nu K_\\nu\\Bigg(
         \\frac{\\sqrt{2\\nu}}{l} d(x_i , x_j )\\Bigg),

    where :math:`K_{\\nu}(\\cdot)` is a modified Bessel function and
    :math:`\\Gamma(\\cdot)` is the gamma function.

    Typically, :math:`d(\\cdot,\\cdot)` is the Euclidean distance or
    :math:`\\ell_2` norm of the difference of the operands.

    Args:
        nu:
            A hyperparameter dict defining the length_scale parameter.
        length_scale:
            A hyperparameter dict defining the length_scale parameter.
        metric:
            The distance function to be used. Defaults to `"l2"`.
    """

    def __init__(
        self,
        nu: Dict[str, Union[str, float, Tuple[float, float]]] = dict(),
        length_scale: Dict[
            str, Union[str, float, Tuple[float, float]]
        ] = dict(),
        metric: Optional[str] = "l2",
    ):
        super().__init__()
        self.nu = _init_hyperparameter(1.0, "fixed", **nu)
        self.length_scale = _init_hyperparameter(1.0, "fixed", **length_scale)
        self.hyperparameters["nu"] = self.nu
        self.hyperparameters["length_scale"] = self.length_scale
        self.metric = metric

    def __call__(self, dists):
        """
        Compute Matern kernels from distance tensor.

        Takes inspiration from
        [scikit-learn](https://github.com/scikit-learn/scikit-learn/blob/95119c13a/sklearn/gaussian_process/kernels.py#L1529)

        Args:
            squared_dists:
                A matrix or tensor of pairwise distances (usually squared l2 or
                F2) of shape `(data_count, nn_count, nn_count)` or
                `(data_count, nn_count)`. In the tensor case, matrix diagonals
                along last two dimensions are expected to be 0.

        Returns:
            A cross-covariance matrix of shape `(data_count, nn_count)` or a
            tensor of shape `(data_count, nn_count, nn_count)` whose last two
            dimensions are kernel matrices.
        """
        return self._fn(dists, nu=self.nu(), length_scale=self.length_scale())

    @staticmethod
    def _fn(dists: mm.ndarray, nu: float, length_scale: float) -> mm.ndarray:
        if nu == 0.5:
            return _matern_05_fn(dists, length_scale)
        elif nu == 1.5:
            return _matern_15_fn(dists, length_scale)
        elif nu == 2.5:
            return _matern_25_fn(dists, length_scale)
        elif nu == mm.inf:
            return _matern_inf_fn(dists, length_scale)
        else:
            return _matern_gen_fn(dists, nu, length_scale)

    def get_optim_params(
        self,
    ) -> Tuple[List[str], List[float], List[Tuple[float, float]]]:
        """
        Report lists of unfixed hyperparameter names, values, and bounds.

        Returns
        -------
            names:
                A list of unfixed hyperparameter names.
            params:
                A list of unfixed hyperparameter values.
            bounds:
                A list of unfixed hyperparameter bound tuples.
        """
        names = []
        params = []
        bounds = []
        if not self.nu.fixed():
            names.append("nu")
            params.append(self.nu())
            bounds.append(self.nu.get_bounds())
        if not self.length_scale.fixed():
            names.append("length_scale")
            params.append(self.length_scale())
            bounds.append(self.length_scale.get_bounds())
        return names, params, bounds

    def get_opt_fn(self) -> Callable:
        """
        Return a kernel function with fixed parameters set.

        This function is designed for use with
        :func:`MuyGPyS.optimize.chassis.optimize_from_tensors()` and assumes
        that optimization parameters will be passed as keyword arguments.

        Returns:
            A function implementing the kernel where all fixed parameters are
            set. The function expects keyword arguments corresponding to current
            hyperparameter values for unfixed parameters.
        """
        return self._get_opt_fn(
            _matern_05_fn,
            _matern_15_fn,
            _matern_25_fn,
            _matern_inf_fn,
            _matern_gen_fn,
            self.nu,
            self.length_scale,
        )

    @staticmethod
    def _get_opt_fn(
        m_05_fn: Callable,
        m_15_fn: Callable,
        m_25_fn: Callable,
        m_inf_fn: Callable,
        m_gen_fn: Callable,
        nu: Hyperparameter,
        length_scale: Hyperparameter,
    ) -> Callable:
        nu_fixed = nu.fixed()
        ls_fixed = length_scale.fixed()
        if nu_fixed is False and ls_fixed is True:

            def caller_fn(dists, **kwargs):
                return m_gen_fn(
                    dists, length_scale=length_scale(), nu=kwargs["nu"]
                )

        elif nu_fixed is False and ls_fixed is False:

            def caller_fn(dists, **kwargs):
                return m_gen_fn(
                    dists, length_scale=kwargs["length_scale"], nu=kwargs["nu"]
                )

        elif nu_fixed is True and ls_fixed is False:
            if nu() == 0.5:

                def caller_fn(dists, **kwargs):
                    return m_05_fn(dists, length_scale=kwargs["length_scale"])

            elif nu() == 1.5:

                def caller_fn(dists, **kwargs):
                    return m_15_fn(dists, length_scale=kwargs["length_scale"])

            elif nu() == 2.5:

                def caller_fn(dists, **kwargs):
                    return m_25_fn(dists, length_scale=kwargs["length_scale"])

            elif nu() == mm.inf:

                def caller_fn(dists, **kwargs):
                    return m_inf_fn(dists, length_scale=kwargs["length_scale"])

            else:

                def caller_fn(dists, **kwargs):
                    return m_gen_fn(
                        dists, nu=nu(), length_scale=kwargs["length_scale"]
                    )

        else:

            if nu() == 0.5:

                def caller_fn(dists, **kwargs):
                    return m_05_fn(dists, length_scale=length_scale())

            elif nu() == 1.5:

                def caller_fn(dists, **kwargs):
                    return m_15_fn(dists, length_scale=length_scale())

            elif nu() == 2.5:

                def caller_fn(dists, **kwargs):
                    return m_25_fn(dists, length_scale=length_scale())

            elif nu() == mm.inf:

                def caller_fn(dists, **kwargs):
                    return m_inf_fn(dists, length_scale=length_scale())

            else:

                def caller_fn(dists, **kwargs):
                    return m_gen_fn(dists, nu=nu(), length_scale=length_scale())

        return caller_fn
