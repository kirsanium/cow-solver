"""Location of all Enum types"""

from enum import Enum


class AMMKind(Enum):
    """Enum for different AMM kinds."""

    UNISWAP = "Uniswap"
    CONSTANT_PRODUCT = "constantProduct"
    WEIGHTED_PRODUCT = "weightedProduct"
    STABLE = "stable"
    CONCENTRATED = "concentratedLiquidity"
    LIMIT_ORDER = "limitOrder"

    def __str__(self) -> str:
        """Represent as string."""
        return self.value

    def __repr__(self) -> str:
        """Represent as string."""
        return str(self)


class Chain(Enum):
    """Enum for the blockchain of the batch auction."""

    MAINNET = "MAINNET"
    XDAI = "XDAI"
    UNKNOWN = "UNKNOWN"

    def __str__(self) -> str:
        """Represent as string."""
        return self.name

    def __repr__(self) -> str:
        """Represent as string."""
        return str(self)
