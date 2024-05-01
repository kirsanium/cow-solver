"""Representation of a limit order."""
from __future__ import annotations

import json
import logging
from decimal import Decimal
from enum import Enum
from typing import Optional, Union
from dataclasses import dataclass, field
from src.models.exchange_rate import ExchangeRate as XRate
from src.models.token import Token, TokenBalance
from src.models.types import NumericType
from src.util.constants import Constants
from src.util.numbers import decimal_to_str


class OrderMatchType(Enum):
    """Enum for different Order Matching"""

    LHS_FILLED = "LhsFilled"
    RHS_FILLED = "RhsFilled"
    BOTH_FILLED = "BothFilled"


class OrderKind(str, Enum):
    """Order kind."""
    SELL = 'sell'
    BUY = 'buy'


class OrderClass(str, Enum):
    """Order class."""
    market = 'market'
    limit = 'limit'
    liquidity = 'liquidity'


@dataclass
class Quote:
    sell_amount: Decimal
    buy_amount: Decimal

    @classmethod
    def from_dict(cls, data: dict) -> Quote:
        required_attributes = [
            "sell_amount",
            "buy_amount",
        ]

        for attr in required_attributes:
            if attr not in data:
                raise ValueError(f"Missing field '{attr}' in order!")
        
        return Quote(data['sell_amount'], data['buy_amount'])

    def to_dict(self) -> dict:
        return {
            'sell_amount': decimal_to_str(self.sell_amount),
            'buy_amount': decimal_to_str(self.buy_amount),
        }



class FeePolicyKind(str, Enum):
    """ Fee policy kind """

    surplus = 'surplus'
    priceImprovement = 'priceImprovement'
    volume = 'volume'


@dataclass
class FeePolicyBase:
    """ A fee policy that applies to an order. """

    kind: FeePolicyKind
    factor: Decimal

    def to_dict(self) -> dict:
        return {
            'kind': str(self.kind),
            'factor': decimal_to_str(self.factor)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> FeePolicyBase:
        kind = data['kind']
        quote = data.get('quote')
        match kind:
            case FeePolicyKind.surplus:
                return SurplusFee(
                    FeePolicyKind[kind],
                    Decimal(data['factor']),
                    Decimal(data['max_volume_factor'])
                )
            case PriceImprovement.priceImprovement:
                return SurplusFee(
                    FeePolicyKind[kind],
                    Decimal(data['factor']),
                    Decimal(data['max_volume_factor']),
                    None if not quote else Quote.from_dict(quote)
                )
            case FeePolicyKind.volume:
                return VolumeFee(
                    FeePolicyKind[kind],
                    Decimal(data['factor']),
                )

@dataclass
class VolumeFee(FeePolicyBase):
    ...


@dataclass
class SurplusFee(FeePolicyBase):
    max_volume_factor: Decimal

    def to_dict(self) -> dict:
        res = super().to_dict()
        res['max_volume_factor'] = decimal_to_str(self.max_volume_factor)
        return res


@dataclass
class PriceImprovement(FeePolicyBase):
    max_volume_factor: Decimal
    quote: Optional[Quote]

    def to_dict(self) -> dict:
        res = super().to_dict()
        res['max_volume_factor'] = decimal_to_str(self.max_volume_factor)
        if self.quote:
            res['quote'] = self.quote.to_dict()
        return res


FeePolicy = Union[VolumeFee, SurplusFee, PriceImprovement]


@dataclass
class Order:
    """Representation of a limit order.
    An order is specified with 3 bounds:
        * maximum amount of buy-token to be bought
        * maximum amount of sell-token to be sold
        * limit exchange rate of buy- vs. sell-token.

    Depending on which of the bounds are set,
    the order represents a classical limit {buy|sell} order,
    a cost-bounded {buy|sell} order or a {buy|sell} market order.
    """
    order_id: str
    buy_token: Token
    sell_token: Token
    buy_amount: Decimal
    sell_amount: Decimal
    kind: OrderKind
    partially_fillable: bool
    class_: OrderClass
    fee_policies: list[FeePolicy] = field(default_factory=list)
        

    def __post_init__(self):
        self.exec_buy_amount: Optional[TokenBalance] = None
        self.exec_sell_amount: Optional[TokenBalance] = None

        if self.buy_token == self.sell_token:
            raise ValueError("sell- and buy-token cannot be equal!")

        if not (self.buy_amount > 0 and self.sell_amount > 0):
            raise ValueError(
                f"buy {self.buy_amount} and sell {self.sell_amount} amounts must be positive!"
            )

    @classmethod
    def from_dict(cls, data: dict) -> Order:
        """
        Read Order object from order data dict.
        Args:
            order_id: ID of order
            data: Dict of order data.
        """

        required_attributes = [
            "uid",
            "sell_token",
            "buy_token",
            "sell_amount",
            "buy_amount",
            "kind",
            "partially_fillable",
            "class_",
        ]

        for attr in required_attributes:
            if attr not in data:
                raise ValueError(f"Missing field '{attr}' in order!")

        return Order(
            order_id=data["uid"],
            buy_token=Token(data["buy_token"]),
            sell_token=Token(data["sell_token"]),
            buy_amount=Decimal(data["buy_amount"]),
            sell_amount=Decimal(data["sell_amount"]),
            kind=OrderKind(data['kind']),
            partially_fillable=bool(data['partially_fillable']),
            class_=OrderClass(data['class_']),
            fee_policies=[
                FeePolicyBase.from_dict(obj) for obj in data['fee_policies']
            ] if 'fee_policies' in data else []
        )

    def as_dict(self) -> dict:
        """Return Order object as dictionary."""
        # Currently, only limit buy or sell orders be handled.
        return {
            "order_id": str(self.order_id),
            "sell_token": str(self.sell_token),
            "buy_token": str(self.buy_token),
            "sell_amount": decimal_to_str(self.sell_amount),
            "buy_amount": decimal_to_str(self.buy_amount),
            "kind": str(self.kind),
            "partially_fillable": self.partially_fillable,
            "class_": str(self.class_),
            "fee_policies": [fp.to_dict() for fp in self.fee_policies]
        }

    @property
    def max_limit(self) -> XRate:
        """Max limit of the order as an exchange rate"""
        return XRate(
            tb1=TokenBalance(self.sell_amount, self.sell_token),
            tb2=TokenBalance(self.buy_amount, self.buy_token),
        )

    @property
    def max_buy_amount(self) -> Optional[TokenBalance]:
        """None for sell-orders"""
        if self.kind == OrderKind.BUY:
            return TokenBalance.parse_amount(self.buy_amount, self.buy_token)
        return None

    @property
    def max_sell_amount(self) -> Optional[TokenBalance]:
        """None for buy-orders"""
        if self.kind == OrderKind.SELL:
            return TokenBalance.parse_amount(self.sell_amount, self.sell_token)
        return None

    @property
    def tokens(self) -> set[Token]:
        """Return the buy and sell tokens."""
        return {self.buy_token, self.sell_token}

    #####################
    #  UTILITY METHODS  #`
    #####################

    def overlaps(self, other: Order) -> bool:
        """
        Determine if one order can be matched with another.
        opposite {buy|sell} tokens and matching prices
        """
        token_conditions = [
            self.buy_token == other.sell_token,
            self.sell_token == other.buy_token,
        ]
        if not all(token_conditions):
            return False

        return (
            self.buy_amount * other.buy_amount <= other.sell_amount * self.sell_amount
        )

    def match_type(self, other: Order) -> Optional[OrderMatchType]:
        """Determine to what extent two orders match"""
        if not self.overlaps(other):
            return None

        if self.buy_amount < other.sell_amount and self.sell_amount < other.buy_amount:
            return OrderMatchType.LHS_FILLED

        if self.buy_amount > other.sell_amount and self.sell_amount > other.buy_amount:
            return OrderMatchType.RHS_FILLED

        return OrderMatchType.BOTH_FILLED

    def is_executable(self, xrate: XRate, xrate_tol: Decimal = Decimal("1e-6")) -> bool:
        """Determine if the order limit price satisfies a given market rate.

        Args:
            xrate: Exchange rate.
            xrate_tol: Accepted violation of the limit exchange rate constraint
                       per unit of buy token (default: 1e-6).
        Returns:
            True, if order can be executed; False otherwise.
        """
        buy_token, sell_token = self.buy_token, self.sell_token
        if xrate.tokens != {buy_token, sell_token}:
            raise ValueError(
                f"Exchange rate and order tokens do not "
                f"match: {xrate} vs. <{buy_token}> | <{sell_token}>!"
            )

        assert xrate_tol >= 0
        converted_buy = xrate.convert_unit(buy_token)
        converted_sell = self.max_limit.convert_unit(buy_token)
        return bool(converted_buy <= (converted_sell * (1 + xrate_tol)))

    def execute(
        self,
        buy_amount_value: NumericType,
        sell_amount_value: NumericType,
        buy_token_price: Union[float, Decimal] = 0,
        sell_token_price: Union[float, Decimal] = 0,
        amount_tol: Decimal = Decimal("1e-8"),
        xrate_tol: Decimal = Decimal("1e-6"),
    ) -> None:
        """Execute the order at given amounts.

        Args:
            buy_amount_value: Buy amount.
            sell_amount_value: Sell amount.
            buy_token_price: Buy-token price.
            sell_token_price: Sell-token price.
            amount_tol: Accepted violation of the limit buy/sell amount constraints.
            xrate_tol: Accepted violation of the limit exchange rate constraint
                       per unit of buy token (default: 1e-6).
        """
        assert buy_amount_value >= -amount_tol
        assert sell_amount_value >= -amount_tol
        assert buy_token_price >= 0
        assert sell_token_price >= 0

        buy_token, sell_token = self.buy_token, self.sell_token

        buy_amount = TokenBalance(buy_amount_value, buy_token)
        sell_amount = TokenBalance(sell_amount_value, sell_token)

        xmax = self.max_buy_amount
        ymax = self.max_sell_amount

        # (a) Check buyAmount: if too much above maxBuyAmount --> error!
        if xmax is not None:
            if buy_amount > xmax * (
                1 + amount_tol
            ) and buy_amount > xmax + TokenBalance(amount_tol, buy_token):
                raise ValueError(
                    f"Invalid execution request for "
                    f"order <{self.order_id}>: "
                    f"buy amount (exec) : {buy_amount.balance} "
                    f"buy amount (max)  : {xmax.balance}"
                )

            buy_amount = min(buy_amount, xmax)

        # (b) Check sellAmount: if too much above maxSellAmount --> error!
        if ymax is not None:
            if sell_amount > ymax * (
                1 + amount_tol
            ) and sell_amount > ymax + TokenBalance(amount_tol, sell_token):
                message = (
                    f"Invalid execution request for "
                    f"order <{self.order_id}>: "
                    f"sell (exec) : {sell_amount.balance} "
                    f"sell (max)  : {ymax.balance}"
                )
                logging.error(message)
                if Constants.RAISE_ON_MAX_SELL_AMOUNT_VIOLATION:
                    raise ValueError(message)
            sell_amount = min(sell_amount, ymax)

        # (c) if any amount is very small, set to zero.
        if any(
            [
                buy_amount <= TokenBalance(amount_tol, buy_token),
                sell_amount <= TokenBalance(amount_tol, sell_token),
            ]
        ):
            buy_amount = TokenBalance(0.0, buy_token)
            sell_amount = TokenBalance(0.0, sell_token)

        # Check limit price.
        if buy_amount > 0:
            assert sell_amount > 0
            xrate = XRate(buy_amount, sell_amount)
            if not self.is_executable(xrate, xrate_tol=xrate_tol):
                message = (
                    f"Invalid execution request for order <{self.order_id}>: "
                    f"buy amount (exec): {buy_amount.balance} "
                    f"sell amount (exec): {sell_amount.balance} "
                    f"xrate (exec): {xrate} "
                    f"limit (max): {self.max_limit}"
                )
                logging.error(message)
                if Constants.RAISE_ON_LIMIT_XRATE_VIOLATION:
                    raise ValueError(message)

        # Store execution information.
        self.exec_buy_amount = buy_amount
        self.exec_sell_amount = sell_amount

    def is_executed(self) -> bool:
        """Check if order has already been executed."""
        return self.exec_buy_amount is not None and self.exec_sell_amount is not None

    def __str__(self) -> str:
        """Represent as string."""
        return json.dumps(self.as_dict(), indent=2)

    def __repr__(self) -> str:
        """Represent as short string."""
        return f"Order: {self.order_id}"

    def __hash__(self) -> int:
        return hash(self.order_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Order):
            return NotImplemented
        if self.order_id != other.order_id:
            return False
        assert vars(self) == vars(other)
        return True

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Order):
            return NotImplemented

        return self.order_id < other.order_id
