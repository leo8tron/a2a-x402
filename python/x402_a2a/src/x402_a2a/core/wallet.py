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
"""Payment signing and processing functions (Tron-compatible via bankofai-x402)."""

import logging
from typing import Optional

from bankofai.x402.clients import X402Client
from bankofai.x402.types import PaymentRequired as x402PaymentRequiredResponse

from ..types import (
    PaymentRequirements,
    PaymentPayload,
)


logger = logging.getLogger(__name__)


async def process_payment_required(
    payment_required: x402PaymentRequiredResponse,
    x402_client: X402Client,
    resource: str = "",
    max_value: Optional[int] = None,
) -> PaymentPayload:
    """Process full payment required response using X402Client.

    Args:
        payment_required: The payment required response from the merchant.
        x402_client: A configured X402Client instance with registered mechanisms.
        resource: The resource URL being purchased.
        max_value: Optional maximum value to pay (currently unused, kept for API compat).

    Returns:
        PaymentPayload ready to be sent to the merchant.
    """
    # Serialize extensions from PaymentRequired so the client mechanism
    # can extract paymentPermitContext (nonce, paymentId, validAfter/Before).
    extensions: dict | None = None
    if payment_required.extensions is not None:
        extensions = payment_required.extensions.model_dump(by_alias=True)

    return await x402_client.handle_payment(
        accepts=payment_required.accepts,
        resource=resource,
        extensions=extensions,
    )


async def process_payment(
    requirements: PaymentRequirements,
    x402_client: X402Client,
    resource: str = "",
) -> PaymentPayload:
    """Creates a PaymentPayload for a single PaymentRequirements using X402Client.

    Args:
        requirements: The selected payment requirements.
        x402_client: A configured X402Client instance with registered mechanisms.
        resource: The resource URL being purchased.

    Returns:
        PaymentPayload ready to be sent to the merchant.
    """
    return await x402_client.create_payment_payload(
        requirements=requirements,
        resource=resource,
    )


def get_transfer_with_auth_typed_data(**kwargs):
    """Creates EIP-712 typed data for EIP-3009 transferWithAuthorization.

    NOTE: This is an EVM-specific function and is not supported on Tron.
    It is kept here for API compatibility only.

    Raises:
        NotImplementedError: Always, as this is not applicable on Tron.
    """
    raise NotImplementedError(
        "get_transfer_with_auth_typed_data is EVM-specific and not supported on Tron. "
        "Use the X402Client with a Tron mechanism for payment signing."
    )

