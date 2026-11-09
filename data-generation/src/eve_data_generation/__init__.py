"""Synthetic GTM source generators."""

__version__ = "1.0.0"

from eve_data_generation.dataset import build_dataset
from eve_data_generation.loader import load_dataset

__all__ = ["__version__", "build_dataset", "load_dataset"]
