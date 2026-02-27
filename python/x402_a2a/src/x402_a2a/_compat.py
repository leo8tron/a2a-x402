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

from typing import Any, Optional, Union

from pydantic import BaseModel, Field

from bankofai.x402.tokens.registry import TokenRegistry

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
# Compatibility types
#
# These types model the payload/domain shapes used by x402 "exact" / "exact_permit"
# flows. They may not be exported by bankofai.x402 directly, but they are used by
# this package (and examples) for consistent parsing/typing of nested payloads.
# =============================================================================


class EIP3009Authorization(BaseModel):
    """EIP-3009 authorization data structure used by exact-style payloads."""

    from_: str = Field("", alias="from")
    to: str = ""
    value: str = "0"
    valid_after: str = Field("0", alias="validAfter")
    valid_before: str = Field("0", alias="validBefore")
    nonce: str = "0x"

    class Config:
        populate_by_name = True


class EIP712Domain(BaseModel):
    """EIP-712 domain data structure."""

    name: Optional[str] = None
    version: Optional[str] = None
    chain_id: Optional[int] = Field(None, alias="chainId")
    verifying_contract: Optional[str] = Field(None, alias="verifyingContract")

    class Config:
        populate_by_name = True


class ExactPaymentPayload(BaseModel):
    """Exact payment scheme payload structure."""

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


# Price type alias (matches original x402.types.Price)
Price = Union[str, int, float, TokenAmount]

# x402 protocol version constant
x402_VERSION = 1


def process_price_to_atomic_amount(
    price: Price,
    network: str,
) -> tuple[str, str, Optional[Any]]:
    """Convert a human-readable price to atomic amount for on-chain use.

    This function intentionally avoids maintaining any local token registry or
    network whitelist. All string price parsing is delegated to
    `bankofai.x402.tokens.registry.TokenRegistry`.

    Args:
        price: Human-readable price (e.g., "0.1 USDT") or TokenAmount.
        network: Blockchain network identifier string (passed through to TokenRegistry).

    Returns:
        Tuple of (atomic_amount_str, asset_address, eip712_domain_or_none)
    """

    # Preferred path: all string prices go through TokenRegistry
    if isinstance(price, str):
        registry_network = {
            "tron": "tron:mainnet",
            "tron-nile": "tron:nile",
            "tron-shasta": "tron:shasta",
        }.get(network, network)

        asset_info = TokenRegistry.parse_price(price, registry_network)
        return str(asset_info["amount"]), str(asset_info["asset"]), None

    # TokenAmount path: caller must provide explicit asset address
    if isinstance(price, TokenAmount):
        if not price.asset or not price.asset.address:
            raise ValueError("TokenAmount.asset.address is required.")
        return str(price.amount), str(price.asset.address), None

    raise ValueError(
        "Unsupported price type. Provide a string price (e.g. '0.1 USDT') with TokenRegistry available, "
        "or pass a TokenAmount with an explicit asset address."
    )


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
    "Price",
    # Constants & functions
    "x402_VERSION",
    "process_price_to_atomic_amount",
]
