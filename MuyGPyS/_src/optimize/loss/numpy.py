# Copyright 2021-2023 Lawrence Livermore National Security, LLC and other
# MuyGPyS Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: MIT

from scipy.special import softmax
from sklearn.metrics import log_loss

import MuyGPyS._src.math.numpy as np


def _cross_entropy_fn(
    predictions: np.ndarray,
    targets: np.ndarray,
    ll_eps: float = 1e-15,
) -> float:
    one_hot_targets = np.where(targets > 0.0, 1.0, 0.0)
    softmax_predictions = softmax(predictions, axis=1)
    return log_loss(
        one_hot_targets, softmax_predictions, eps=ll_eps, normalize=False
    )


def _mse_fn_unnormalized(
    predictions: np.ndarray,
    targets: np.ndarray,
) -> float:
    return np.sum((predictions - targets) ** 2)


def _mse_fn(
    predictions: np.ndarray,
    targets: np.ndarray,
) -> float:
    batch_count, response_count = predictions.shape
    return _mse_fn_unnormalized(predictions, targets) / (
        batch_count * response_count
    )


def _lool_fn_unscaled(
    predictions: np.ndarray, targets: np.ndarray, variances: np.ndarray
) -> float:
    return np.sum(
        np.divide((predictions - targets) ** 2, variances) + np.log(variances)
    )


def _lool_fn(
    predictions: np.ndarray,
    targets: np.ndarray,
    variances: np.ndarray,
    sigma_sq: np.ndarray,
) -> float:
    return _lool_fn_unscaled(
        predictions, targets, np.outer(variances, sigma_sq)
    )


def _pseudo_huber_fn(
    predictions: np.ndarray, targets: np.ndarray, boundary_scale: float = 1.5
) -> float:
    return boundary_scale**2 * np.sum(
        np.sqrt(1 + np.divide(targets - predictions, boundary_scale) ** 2) - 1
    )


def _looph_fn_unscaled(
    predictions: np.ndarray,
    targets: np.ndarray,
    variances: np.ndarray,
    boundary_scale: float = 1.5,
) -> float:
    boundary_scale_sq = boundary_scale**2
    return np.sum(
        boundary_scale_sq
        * np.sqrt(
            1
            + np.divide(targets - predictions, variances * boundary_scale) ** 2
        )
        - boundary_scale_sq
        + np.log(variances)
    )


def _looph_fn(
    predictions: np.ndarray,
    targets: np.ndarray,
    variances: np.ndarray,
    sigma_sq: np.ndarray,
    boundary_scale: float = 1.5,
) -> float:
    return _looph_fn_unscaled(
        predictions,
        targets,
        np.outer(variances, sigma_sq),
        boundary_scale=boundary_scale,
    )
