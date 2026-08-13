"""Reproducibility Seed Utility.

Ensures deterministic execution across Python random, NumPy, PyTorch, and Transformers.
"""

from __future__ import annotations

import os
import random
import numpy as np


def set_all_seeds(seed: int = 42) -> int:
    """Set global random seed across all libraries."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)

    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
    except ImportError:
        pass

    return seed
