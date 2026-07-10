"""
Integration point for OKX.AI's pay-per-call (USDT / X Layer) billing step.

This is intentionally NOT implemented here -- per project scope, real
payment/billing logic is handled on the OKX.AI listing side. This stub
exists so the wrapper has one clearly marked place to hook in that check
later without touching core/ or the tool definition in server.py.

Today, verify_payment() always returns True (i.e. every call is allowed
through). Replace its body with a real check against whatever OKX.AI's ASP
runtime provides (e.g. a payment/session token passed in request metadata)
once that integration is defined.
"""


def verify_payment(request_context: dict | None = None) -> bool:
    """TODO(OKX.AI integration): verify the caller has paid for this call
    before analyze_resume_fit runs. Currently a no-op stub -- always allows
    the call through.
    """
    return True
