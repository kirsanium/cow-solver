"""
This file defines problem, solution, and solver parameters schemas,
using pydantic that is then used to validate IO and autogenerate
documentation.
"""

from typing import Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
import json
import abc

# Example instance to use in the autogenerated API documentation.

with open('data/example.json') as example:
    example_request = json.load(example)


def to_camelcase(string: str) -> str:
    res = ''.join(word.capitalize() for word in string.split('_'))
    return res[0].lower() + res[1:]


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camelcase,
        arbitrary_types_allowed=True
    )


# The following classes model the contents of a PROBLEM instance.
# They are used for input validation and documentation.


"""Ethereum public address (as a string)."""
Address = str


"""Big integer (as a string)."""
BigInt = str


"""Token unique identifier."""
TokenId = Address


"""Token amount."""
TokenAmount = BigInt


"""Order unique identifier."""
OrderId = str


"""Decimal number (as a string)."""
Decimal = str


"""256 bit unsigned integer in decimal notation. (as a string)."""
U256 = str


"""128 bit unsigned integer in decimal notation. (as a string)."""
U128 = str


"""128 bit signed integer in decimal notation. (as a string)."""
I128 = str


class TokenInfoModel(BaseSchema):
    """Token-specific data."""

    decimals: Optional[int] = Field(None, description="Number of decimals.")
    symbol: Optional[str] = Field(None, description="The ERC20.symbol value for this token.")
    reference_price: Optional[int] = Field(
        0,
        description="The reference price of this token for the auction used for scoring. "
        "This price is only included for tokens for which there are CoW Protocol orders.",
    )
    available_balance: TokenAmount = Field(0, description="The balance held by the Settlement contract "
                                               "that is available during a settlement.")
    trusted: bool = Field(description="A flag which indicates that solvers are allowed to perform gas cost "
        "optimizations for this token by not routing the trades via an AMM, "
        "and instead use its available balances, as specified by CIP-2."
    )


class OrderClass(str, Enum):
    """Order class."""

    MARKET = 'market'
    LIMIT = 'limit'
    LIQUIDITY= 'liquidity'


class OrderKind(str, Enum):
    """Order kind."""

    SELL = 'sell'
    BUY = 'buy'


class Quote(BaseSchema):
    sell_amount: TokenAmount = Field(0, description="Amount of an ERC20 token. 256 bit unsigned integer in decimal notation.")
    buy_amount: TokenAmount = Field(0, description="Amount of an ERC20 token. 256 bit unsigned integer in decimal notation.")


class FeePolicyKind(str, Enum):
    """ Fee policy kind """

    SURPLUS = 'surplus'
    PRICE_IMPROVEMENT = 'priceImprovement'
    VOLUME = 'volume'


class FeePolicy(BaseSchema):
    """ A fee policy that applies to an order. """

    kind: FeePolicyKind = Field(description="Fee policy kind.")
    factor: Optional[float] = Field(0.0, description="The fraction of the order's volume that the protocol will request from the solver after settling the order.")
    max_volume_factor: Optional[float] = Field(100, description="Never charge more than that percentage of the order volume.")
    quote: Optional[Quote] = Field(None)


class OrderModel(BaseSchema):
    """Order data."""

    uid: OrderId
    sell_token: TokenId = Field(..., description="Token to be sold.")
    buy_token: TokenId = Field(..., description="Token to be bought.")
    sell_amount: TokenAmount = Field(
        ...,
        description="If is_sell_order=true indicates the maximum amount to sell, "
        "otherwise the maximum amount to sell in order to buy buy_amount.",
    )
    buy_amount: TokenAmount = Field(
        ...,
        description="If is_sell_order=False indicates the maximum amount to buy, "
        "otherwise the minimum amount to buy in order to sell sell_amount.",
    )
    kind: OrderKind = Field(..., description='Order kind: sell or buy.')
    partially_fillable: bool = Field(
        ...,
        description="If the order can sell/buy less than its maximum sell/buy amount.",
    )
    class_: OrderClass = Field(
        ...,
        alias='class',
        description="How the CoW Protocol order was classified: market, limit, liquidity.",
    )
    fee_policies: Optional[list[FeePolicy]] = Field(
        default_factory=list,
        description='A fee policies that apply to an order.'
    )
    

class LiquidityKindEnum(str, Enum):
    """Liquidity kind."""

    CONSTANT_PRODUCT = "constantProduct"
    WEIGHTED_PRODUCT = "weightedProduct"
    STABLE = "stable"
    CONCENTRATED = "concentratedLiquidity"
    LIMIT_ORDER = "limitOrder"


class PoolTokenInfo(BaseSchema):
    """Token info for liquidity schema"""

    balance: TokenAmount = Field(..., description="Balance.")
    scaling_factor: Optional[Decimal] = Field(None, description="Scaling factor.")
    weight: Optional[Decimal] = Field(None, description="Weight.")


class WeightedProductPoolVersion(str, Enum):
    V0 = 'v0'
    V3PLUS = 'v3Plus'


"""
A hex-encoded 32 byte string containing the pool address (0..20), 
the pool specialization (20..22) and the poolnonce (22..32).
"""
BalancerPoolId = str


class Liquidity(BaseSchema, abc.ABC):
    """
    On-chain liquidity that can be used in a solution.
    This liquidity is provided to facilitate onboarding new solvers.
    Additional liquidity that is not included in this set may still be used in solutions.
    """
    id: str = Field(description="An opaque ID used for uniquely identifying the liquidity within a single auction "
                    "(note that they are not guaranteed to be unique across auctions). "
                    "This ID is used in the solution for matching interactions with the executed liquidity.")
    address: Address = Field(description="The Ethereum public address of the liquidity. "
                             "The actual address that is specified is dependent on the kind of liquidity.")
    gas_estimate: BigInt = Field(description="A rough approximation of gas units required to use this liquidity on-chain.")
    kind: LiquidityKindEnum = Field(description="Liquidity kind.")



class ConstantProductPool(Liquidity):
    """
    A UniswapV2-like constant product liquidity pool for a token pair.
    """
    tokens: dict[TokenId, PoolTokenInfo] = Field(description='Tokens description')
    fee: Decimal = Field(description="An arbitrary-precision decimal value.")
    router: Address = Field(description="An Ethereum public address of the router.")


class WeightedProductPool(Liquidity):
    """
    A Balancer-like weighted product liquidity pool of N tokens.
    """
    tokens: dict[TokenId, PoolTokenInfo] = Field(description='Tokens description')
    fee: Decimal = Field(description="An arbitrary-precision decimal value.")
    version: Optional[WeightedProductPoolVersion] = Field(None)
    balancer_pool_id: BalancerPoolId


class StablePool(Liquidity):
    """
    A Curve-like stable pool of N tokens.
    """
    tokens: dict[TokenId, PoolTokenInfo] = Field(description='Tokens description')
    fee: Decimal = Field(description="An arbitrary-precision decimal value.")
    amplification_parameter: Decimal = Field(description="An arbitrary-precision decimal value.")
    balancer_pool_id: BalancerPoolId


"""Tick integer index as string"""
TickIndex = str


class ConcentratedLiquidityPool(Liquidity):
    """
    A UniswapV3-like concentrated liquidity pool of 2 tokens.
    """
    tokens: list[TokenId] = Field(description='Tokens description')
    sqrt_price: U256 = Field(description="Square root of price.")
    liquidity: U128
    tick: int
    liquidity_net: dict[TickIndex, I128] = Field(description="A map of tick indices to their liquidity values.")
    fee: Decimal = Field(description="An arbitrary-precision decimal value.")
    router: Address = Field(description="An Ethereum public address of the router.")


class ForeingLimitOrder(Liquidity):
    """
    A 0x-like limit order external to CoW Protocol.
    """
    maker_token: TokenId
    taker_token: TokenId
    maker_amount: TokenAmount
    taker_amount: TokenAmount
    taker_token_fee_amount: TokenAmount


class BatchAuctionModel(BaseSchema):
    """Batch auction (request) data."""

    id: int
    tokens: Dict[TokenId, TokenInfoModel] = Field(..., description="Tokens.")
    orders: list[OrderModel] = Field(..., description="Orders.")
    liquidity: list[Union[ConstantProductPool, WeightedProductPool, StablePool, ConcentratedLiquidityPool, ForeingLimitOrder]] = Field(..., description="Liquidity info.")
    effective_gas_price: BigInt = Field(description="The current estimated gas price that will be paid when "
                                        "executing a settlement. Additionally, this is the gas price that is "
                                        "multiplied with a settlement's gas estimate for solution scoring.")
    deadline: datetime = Field(description="The deadline by which a solution to the auction is required. "
                               "Requests that go beyond this deadline are expected to be cancelled by the caller.")

    class Config:
        """Includes example in generated openapi file"""

        json_schema_extra = {"example": example_request}


# The following classes model the contents of a SOLUTION instance.
# They are used for input validation and documentation.

class TradeKind(str, Enum):
    FULFILLMENT = 'fulfillment'
    JIT = 'jit'


class TradeBase(BaseSchema, abc.ABC):
    """CoW Protocol order trades included in the solution."""
    kind: TradeKind


class Fullfilment(TradeBase):
    order: OrderId = Field(..., description="A reference by UID of the order to execute in a solution. "
                           "The order must be included in the auction input.")
    fee: Optional[Decimal] = Field(None, description="The sell token amount that should be taken as a fee "
                                   "for this trade. This only gets returned for limit orders and only "
                                   "refers to the actual amount filled by the trade.")
    executed_amount: Optional[TokenAmount] = Field(None, description='The amount of the order that was executed. '
                                              'This is denoted in "sellToken" for sell orders, '
                                              'and "buyToken" for buy orders.')


class SellTokenBalanceEnum(str, Enum):
    ERC20 = 'erc20'
    INTERNAL = 'internal'
    EXTERNAL = 'external'


class BuyTokenBalanceEnum(str, Enum):
    ERC20 = 'erc20'
    INTERNAL = 'internal'


class SigningSchemeEnum(str, Enum):
    EIP712 = 'eip712'
    ETHSIGN = 'ethSign'
    PRESIGN = 'preSign'
    EIP1271 = 'eip1271'


class JitOrder(BaseSchema):
    sell_token: TokenId
    buy_token: TokenId
    receiver: Address
    sell_amount: TokenAmount
    buy_amount: TokenAmount
    valid_to: str
    fee_amount: TokenAmount
    kind: OrderKind
    partially_fillable: bool
    sell_token_balance: SellTokenBalanceEnum
    buy_token_balance: BuyTokenBalanceEnum
    signing_scheme: SigningSchemeEnum
    signature: str


class JitTrade(TradeBase):
    order: JitOrder = Field(description="The just-in-time liquidity order to execute in a solution.")
    fee: Optional[Decimal] = Field(None, description="The sell token amount that should be taken as a fee "
                                   "for this trade. This only gets returned for limit orders and only "
                                   "refers to the actual amount filled by the trade.")
    executed_amount: TokenAmount = Field(description='The amount of the order that was executed. '
                                              'This is denoted in "sellToken" for sell orders, '
                                              'and "buyToken" for buy orders.')


class InteractionKind(str, Enum):
    LIQUIDITY = 'liquidity'
    CUSTOM = 'custom'


class InteractionBase(BaseSchema, abc.ABC):
    """
    A base class for an interaction to execute as part of a settlement.
    """
    internalize: bool = Field(description="A flag indicating that the interaction should be 'internalized',"
                              " as specified by CIP-2.")
    kind: InteractionKind


class LiquidityInteraction(InteractionBase):
    """
    Interaction representing the execution of liquidity that was passed in with the auction.
    """
    id: int = Field(description="The ID of executed liquidity provided in the auction input.")
    input_token: TokenId
    output_token: TokenId
    input_amount: TokenAmount
    output_amount: TokenAmount


class Allowance(BaseSchema):
    """
    An ERC20 allowance from the settlement contract to some spender that is required for a custom interaction.
    """
    token: TokenId
    spender: Address
    amount: Optional[TokenAmount] = None


class Asset(BaseSchema):
    """
    A token address with an amount.
    """
    token: TokenId
    amount: TokenAmount


class CustomInteraction(InteractionBase):
    """	
    A searcher-specified custom interaction to be included in the final settlement.
    """
    target: Address
    value: TokenAmount
    calldata: str = Field(description="The EVM calldata bytes.")
    allowances: list[Allowance] = Field(default_factory=list, description="ERC20 allowances that are required for this custom interaction.")
    inputs: list[Asset]
    outputs: list[Asset]


class Solution(BaseSchema):
    """Settled batch auction data (solution)."""

    prices: Dict[TokenId, BigInt] = Field(
        ..., description="Settled price for each token."
    )
    trades: list[Union[Fullfilment, JitTrade]] = Field(
        ..., description="Trades to execute."
    )
    interactions: List[Union[LiquidityInteraction, CustomInteraction]] = Field(
        ...,
        description="List of interactions", default_factory=list
    )
    gas: Optional[int] = Field(None, description="How many units of gas this solution is estimated to cost.")


class SolutionModel(BaseSchema):
    solutions: list[Solution]
