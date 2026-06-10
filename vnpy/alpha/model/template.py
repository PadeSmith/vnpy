from abc import ABCMeta, abstractmethod
from typing import Any

import numpy as np
import polars as pl

from vnpy.alpha.dataset import AlphaDataset, Segment


class AlphaModel(metaclass=ABCMeta):
    """Template class for machine learning algorithms"""

    @abstractmethod
    def fit(self, dataset: AlphaDataset) -> None:
        """
        Fit the model with dataset
        """
        pass

    @abstractmethod
    def predict(self, dataset: AlphaDataset, segment: Segment) -> np.ndarray:
        """
        Make predictions using the model
        """
        pass

    @staticmethod
    def _prepare_infer_data(dataset: AlphaDataset, segment: Segment) -> np.ndarray:
        """Fetch inference data, sort, and extract feature columns as numpy."""
        df: pl.DataFrame = dataset.fetch_infer(segment)
        df = df.sort(["datetime", "vt_symbol"])
        return df.select(df.columns[2: -1]).to_numpy()

    def detail(self) -> Any:
        """
        Output detailed information about the model
        """
        return
