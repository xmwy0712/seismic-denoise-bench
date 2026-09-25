"""首要指标包：ΔSNR 与 Lsig。

* :mod:`bench.metrics.snr`  —— ``snr_db`` / ``delta_snr_db``（+ 带状态的 ``snr_outcome``）
* :mod:`bench.metrics.lsig` —— ``event_mask`` / ``lsig`` / ``dilation_length_samples``
"""

from .lsig import dilation_length_samples, event_mask, lsig
from .snr import (
    SnrOutcome,
    delta_snr_db,
    denominator_was_zero,
    reset_denominator_flag,
    snr_db,
    snr_outcome,
)

__all__ = [
    "snr_db",
    "delta_snr_db",
    "snr_outcome",
    "SnrOutcome",
    "denominator_was_zero",
    "reset_denominator_flag",
    "event_mask",
    "lsig",
    "dilation_length_samples",
]
