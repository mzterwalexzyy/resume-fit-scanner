"""
Integration point for OKX.AI's pay-per-call billing step.

This is intentionally NOT implemented here -- per project scope, real
payment/billing logic is handled on the OKX.AI listing side. This stub
exists so the wrapper has one clearly marked place to hook in that check
later without touching core/ or the tool definition in server.py.

Confirmed via OKX's own onchainos-skills docs (not guessed): paid A2MCP
endpoints are expected to speak x402 -- a payment-required HTTP
challenge/response scheme -- with OKX recommending their Payment SDK
(okx-agent-payments-protocol) for it. That's a real, specific target for
this stub, not the generic "USDT on X Layer" placeholder this originally
assumed.

Today, verify_payment() always returns True (i.e. every call is allowed
through). Replace its body with a real x402 challenge/verify step once
that integration is wired up.
"""


def verify_payment(request_context: dict | None = None) -> bool:
    """TODO(OKX.AI x402 integration): verify the caller has paid for this
    call (x402 challenge/response) before analyze_resume_fit runs. Currently
    a no-op stub -- always allows the call through.
    """
    return True
