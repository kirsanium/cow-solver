"""
Model containing BatchAuction which is what solvers operate on.
"""

from __future__ import annotations
import decimal
import logging
from decimal import Decimal
from typing import Any
from src.models.order import Order
from src.models.token import (
    Token,
    TokenInfo,
    TokenDict,
    TokenSerializedType,
)
from src.models.types import NumericType
from src.models.uniswap import Uniswap
from datetime import datetime


class BatchAuction:
    """Class to represent a batch auction."""

    __DEFAULT_NAME = "batch_auction"

    def __init__(
        self,
        id: str,
        tokens: dict[Token, TokenInfo],
        orders: dict[str, Order],
        uniswaps: dict[str, Uniswap],
        effective_gas_price: Decimal,
        deadline: datetime,
        name: str = __DEFAULT_NAME,
    ):
        """Initialize.
        Args:
            tokens: dict of tokens participating.
            orders: dict of Order objects.
            uniswaps: dict of Uniswap objects.
            effective_gas_price: The current estimated gas price.
            deadline: datetime by which a solution is required.
            name: Name of the batch auction instance.
        """
        self.name = name
        self._id = id
        self._tokens = tokens
        self._orders = orders
        self._uniswaps = uniswaps
        self._effective_gas_price = effective_gas_price
        self._deadline = deadline


    @classmethod
    def from_dict(cls, data: dict, name: str = __DEFAULT_NAME) -> BatchAuction:
        """Read a batch auction instance from a python dictionary.

        Args:
            data: Python dict to be read.
            name: Instance name.

        Returns:
            The instance.

        """
        for key in ["tokens", "orders", "liquidity", "effective_gas_price", "deadline"]:
            if key not in data:
                raise ValueError(f"Mandatory field '{key}' missing in instance data!")

        tokens = load_tokens(data["tokens"])
        orders = load_orders(data["orders"])
        uniswaps = load_amms(data.get("liquidity", []))

        return cls(
            data['id'],
            tokens,
            orders,
            uniswaps,
            Decimal(data['effective_gas_price']),
            datetime.strptime(data['deadline'], '%Y-%m-%dT%H:%M:%S.%f%z'),
            name=name,
        )

    ####################
    #  ACCESS METHODS  #
    ####################

    @property
    def tokens(self) -> list[Token]:
        """Access to (sorted) token list."""
        return sorted(self._tokens.keys())

    @property
    def orders(self) -> list[Order]:
        """Access to order list."""
        return list(self._orders.values())

    @property
    def uniswaps(self) -> list[Uniswap]:
        """Access to uniswap list."""
        return list(self._uniswaps.values())

    def token_info(self, token: Token) -> TokenInfo:
        """Get the token info for a specific token."""
        assert isinstance(token, Token)

        if token not in self.tokens:
            raise ValueError(f"Token <{token}> not in batch auction!")

        return self._tokens[token]


    def solve(self) -> Any:
        for uniswap in self.uniswaps:
            ...
        return {
            "id": self._id,
            "prices": {},
            "trades": [],
            "interactions": [],
            "gas": 0
        }

    #################################
    #  SOLUTION PROCESSING METHODS  #
    #################################

    def __str__(self) -> str:
        """Print batch auction data.

        Returns:
            The string representation.

        """
        output_str = "BATCH AUCTION:"

        output_str += f"\n=== TOKENS ({len(self.tokens)}) ==="
        for token in self.tokens:
            output_str += f"\n-- {token}"

        output_str += f"\n=== ORDERS ({len(self.orders)}) ==="
        for order in self.orders:
            output_str += f"\n{order}"

        output_str += f"\n=== UNISWAPS ({len(self.uniswaps)}) ==="
        for uni in self.uniswaps:
            output_str += f"\n{uni}"

        return output_str

    def __repr__(self) -> str:
        """Print batch auction data."""
        return self.name


def load_prices(
    prices_serialized: dict[TokenSerializedType, NumericType]
) -> dict[Token, Decimal]:
    """Load token price information as dict of Token -> Decimal."""
    if not isinstance(prices_serialized, dict):
        raise ValueError(
            f"Prices must be given as dict, not {type(prices_serialized)}!"
        )
    return {Token(t): Decimal(p) for t, p in prices_serialized.items()}


def load_orders(orders_serialized: list[dict]) -> list[Order]:
    """Load list of orders.

    Args:
        orders_serialized: list of order data.

    Returns:
        A list of Order objects.
    """
    return [Order.from_dict(data) for data in orders_serialized]


def load_amms(amms_serialized: list[dict]) -> dict[str, Uniswap]:
    """Load list of AMMs.

    NOTE: Currently, the code only supports Uniswap-style AMMs, i.e.,
    constant-product pools with two tokens and equal weights.

    Args:
        amms_serialized: dict of pool_id -> AMM.

    Returns:
        A list of Uniswap objects.

    """
    amm_list: list[Uniswap] = []
    for amm_dict in amms_serialized:
        amm = Uniswap.from_dict(amm_dict['id'], amm_dict)
        if amm is not None:
            amm_list.append(amm)

    results: dict[str, Uniswap] = {}
    for uni in amm_list:
        if uni.pool_id in results:
            raise ValueError(f"Uniswap pool_id <{uni.pool_id}> already exists!")
        results[uni.pool_id] = uni

    return results


# TODO
def load_tokens(tokens_serialized: dict) -> TokenDict:
    """Store tokens as sorted dictionary from Token -> token info.

    Args:
        tokens_serialized: list or dict of tokens.

    Returns:
        A dict of Token -> token info.

    """
    tokens_dict = {}
    for token_str, token_info in sorted(tokens_serialized.items()):
        token = Token(token_str)
        if token_info is None:
            token_info = {}
        else:
            for k, val in token_info.items():
                if val is None:
                    continue
                try:
                    # Convert to str first to avoid float-precision artifacts:
                    # Decimal(0.1)   -> Decimal('0.10000000000000000555...')
                    # Decimal('0.1') -> Decimal(0.1)
                    val = Decimal(str(val))
                except decimal.InvalidOperation:
                    pass
                token_info[k] = val
        if token in tokens_dict:
            logging.warning(f"Token <{token}> already exists!")
        tokens_dict[token] = TokenInfo(token, **token_info)

    return tokens_dict
