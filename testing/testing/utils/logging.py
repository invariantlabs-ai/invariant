"""Defines logging related utilities."""

import logging
from random import SystemRandom


class ProbabilityFilter(logging.Filter):
    """Filter that randomly filters log records based on a probability."""

    def __init__(self, probability: float):
        self.probability = probability
        self.cryptogen = SystemRandom()
        super().__init__()

    def filter(self, _: logging.LogRecord) -> bool:
        return self.cryptogen.random() <= self.probability
