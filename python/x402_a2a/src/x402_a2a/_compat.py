# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Compatibility layer bridging bankofai-x402 (Tron) SDK to the x402 API expected by x402_a2a.

This module re-exports types from bankofai.x402 and provides stub definitions
for types that only exist in the original Coinbase x402 SDK (e.g., EVM-specific types).
"""

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field

# =============================================================================
# Re-exports from bankofai.x402 (types that exist in both SDKs)
# =============================================================================
from bankofai.x402.types import (
    PaymentRequirements,
    PaymentPayload,
    SettleResponse,
    VerifyResponse,
)
from bankofai.x402.types import PaymentRequired as x402PaymentRequiredResponse
from bankofai.x402.facilitator import FacilitatorClient

# =============================================================================
# Stub types: these exist in the original Coinbase x402 SDK but not in bankofai-x402.
# They are defined here so existing code continues to compile.
# =============================================================================


class EIP3009Authorization(BaseModel):
    """EIP-3009 authorization data (EVM-specific, stub for Tron compatibility)."""

    from_: str = Field("", alias="from")
    to: str = ""
    value: str = "0"
    valid_after: str = Field("0", alias="validAfter")
    valid_before: str = Field("0", alias="validBefore")
    nonce: str = "0x"

    class Config:
        populate_by_name = True


class EIP712Domain(BaseModel):
    """EIP-712 domain data (EVM-specific, stub for Tron compatibility)."""

    name: Optional[str] = None
    version: Optional[str] = None
    chain_id: Optional[int] = Field(None, alias="chainId")
    verifying_contract: Optional[str] = Field(None, alias="verifyingContract")

    class Config:
        populate_by_name = True


class ExactPaymentPayload(BaseModel):
    """Exact payment scheme payload (EVM-specific, stub for Tron compatibility)."""

    signature: str = ""
    authorization: Optional[EIP3009Authorization] = None

    class Config:
        populate_by_name = True


class TokenAsset(BaseModel):
    """Token asset information."""

    address: str = ""
    name: str = ""
    symbol: str = ""
    decimals: int = 6


class TokenAmount(BaseModel):
    """Token amount with asset information."""

    amount: Union[str, int] = "0"
    asset: Optional[TokenAsset] = None


class FacilitatorConfig(BaseModel):
    """Configuration for facilitator connection."""

    url: str = ""
    headers: Optional[dict[str, str]] = None


# SupportedNetworks as a type alias (Literal of known networks)
SupportedNetworks = Literal["base", "base-sepolia", "tron", "tron-nile", "tron-shasta"]

# Price type alias (matches original x402.types.Price)
Price = Union[str, int, float, TokenAmount]

# x402 protocol version constant
x402_VERSION = 1


def process_price_to_atomic_amount(
    price: Price,
    network: str,
) -> tuple[str, str, Optional[Any]]:
    """Convert a human-readable price to atomic amount for on-chain use.

    This is a compatibility stub. For Tron networks, you should configure
    the amount and asset address directly in PaymentRequirements.

    Args:
        price: Human-readable price (e.g., "$1.00", 1.00)
        network: Blockchain network identifier

    Returns:
        Tuple of (atomic_amount_str, asset_address, eip712_domain_or_none)
    """
    # Default USDT/USDC addresses per network
    default_assets = {
        "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bda02913",  # USDC on Base
        "base-sepolia": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",  # USDC on Base Sepolia
        "tron": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",  # USDT on Tron Mainnet
        "tron-nile": "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj",  # USDT on Tron Nile
        "tron-shasta": "TG3XXyExBkFU9nQGAEmeyA6sAP2W9Ehr4u",  # USDT on Tron Shasta
    }

    asset_address = default_assets.get(network, default_assets.get("tron", ""))

    # Convert price to atomic amount (assuming 6 decimals for USDT/USDC)
    decimals = 6
    if isinstance(price, str):
        if price.startswith("$"):
            price = price[1:]
        amount_float = float(price)
    elif isinstance(price, (int, float)):
        amount_float = float(price)
    elif isinstance(price, TokenAmount):
        # TokenAmount already has the right format
        return str(price.amount), price.asset.address if price.asset else asset_address, None
    else:
        amount_float = float(str(price))

    atomic_amount = int(amount_float * (10**decimals))

    # For Tron networks, no EIP-712 domain needed
    eip712_domain = None
    if network.startswith("base"):
        eip712_domain = EIP712Domain(name="USD Coin", version="2")

    return str(atomic_amount), asset_address, eip712_domain


# =============================================================================
# Re-export everything for convenient importing
# =============================================================================
__all__ = [
    # From bankofai.x402
    "PaymentRequirements",
    "PaymentPayload",
    "SettleResponse",
    "VerifyResponse",
    "x402PaymentRequiredResponse",
    "FacilitatorClient",
    # Stub types
    "EIP3009Authorization",
    "EIP712Domain",
    "ExactPaymentPayload",
    "TokenAsset",
    "TokenAmount",
    "FacilitatorConfig",
    "SupportedNetworks",
    "Price",
    # Constants & functions
    "x402_VERSION",
    "process_price_to_atomic_amount",
]
