"""
Integration point for OKX.AI's pay-per-call billing step.

The HTTP 402 challenge itself is now implemented -- see
mcp_server/x402_middleware.py, added after OKX's ASP review flagged the
endpoint was returning 406 instead of the required 402 for an
unauthenticated call. That middleware runs at the HTTP layer, before this
tool function's body ever executes: by the time verify_payment() runs
below, a request has either presented some Authorization/X-PAYMENT header,
or it never got past the middleware's 402 challenge at all.

What's still NOT implemented, deliberately: cryptographic verification of
the payment proof, and on-chain settlement. Building that means this server
holding gas funds and broadcasting transactions on its own -- real
financial-transaction code that deserves its own deliberate scope, not a
silent add-on. verify_payment() stays a no-op (trusting that the middleware
already required a payment-shaped header to reach this point) until that
integration is wired up.
"""


def verify_payment(request_context: dict | None = None) -> bool:
    """TODO(OKX.AI x402 integration): cryptographically verify the payment
    proof (EIP-3009 signature) and settle on-chain. Currently a no-op --
    the x402 challenge/response shape is already enforced upstream by
    mcp_server/x402_middleware.py; this only decides whether to *additionally*
    trust the proof's contents, which it does not yet do.
    """
    return True
