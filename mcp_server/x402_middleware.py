"""
x402 payment-required challenge for the paid analyze_resume_fit tool call.

OKX's ASP review flagged that the endpoint returned HTTP 406 instead of 402
for an unauthenticated call -- their docs state paid A2MCP endpoints "must
support x402". Reproduced locally: a bare, unauthenticated GET to the
endpoint (no MCP session, no `Accept: text/event-stream`) fell through to
FastMCP's own protocol-negotiation error (406), which is almost certainly
what a compliance-check probe does -- not a full MCP client handshake. This
module fixes that: such a request now gets a properly-shaped HTTP 402
challenge instead.

Scope, deliberately: this issues the CHALLENGE only. It does not
cryptographically verify a payment signature and does not settle funds
on-chain -- any request carrying an Authorization or X-PAYMENT header is
let through unverified. Real verification/settlement remains the
integration point already marked in billing_stub.py ("leave a clearly
marked integration point, do not implement real payment/billing logic
yourself" was the original scope). Building full EIP-3009 signature
verification plus on-chain settlement would mean this server holding gas
funds and broadcasting transactions on its own -- financial-transaction
code that deserves its own deliberate scope, not a silent add-on here.

What stays free (never gated), so a real MCP client can still complete the
normal handshake and a caller can still discover what's available before
paying:
  - a GET carrying `Accept: text/event-stream` -- FastMCP's own SSE
    notification channel, not a tool call
  - JSON-RPC `initialize` / `notifications/initialized` / `tools/list`
  - `tools/call` for the free `ping` health-check tool
Everything else to the MCP path -- including a bare GET/POST with no
recognizable MCP shape, which is what a naive compliance probe sends, and
`tools/call` for `analyze_resume_fit` specifically -- requires payment.

Implemented as a raw ASGI middleware (not Starlette's BaseHTTPMiddleware):
BaseHTTPMiddleware's body-replay pattern (re-reading .body() then
reassigning request._receive) collides with its own internal receive-queue
bookkeeping on this Starlette version ("Unexpected message received").
Buffering and replaying the ASGI receive() messages by hand sidesteps that
entirely.
"""
import base64
import json

# Verified via `onchainos token search --chain xlayer --query USDT`:
# community-recognized USD-T0 on X Layer (chainIndex 196), 6 decimals.
X402_ASSET = "0x779ded0c9e1022225f8e0630b35a9b54be713736"
X402_NETWORK = "eip155:196"  # X Layer, CAIP-2
X402_PAY_TO = "0xccf6b0cf6920146570188c12437902bf318f4b32"  # this ASP's registered wallet
X402_AMOUNT_ATOMIC = "100000"  # 0.1 USDT at 6 decimals, matching the registered service fee
X402_MAX_TIMEOUT_SECONDS = 300

GATED_TOOL_NAME = "analyze_resume_fit"
FREE_TOOL_NAMES = {"ping"}
FREE_RPC_METHODS = {"initialize", "notifications/initialized", "tools/list"}


def build_challenge(resource_url: str) -> dict:
    return {
        "x402Version": 1,
        "resource": resource_url,
        "accepts": [
            {
                "scheme": "exact",
                "network": X402_NETWORK,
                "asset": X402_ASSET,
                "payTo": X402_PAY_TO,
                "maxAmountRequired": X402_AMOUNT_ATOMIC,
                "maxTimeoutSeconds": X402_MAX_TIMEOUT_SECONDS,
                "resource": resource_url,
                "description": "Resume/Job-Fit Scanner: analyze_resume_fit (pay-per-call)",
                "mimeType": "application/json",
                "extra": {"name": "USD₮0", "version": "2"},
            }
        ],
    }


def _get_header(headers, name: bytes) -> str:
    for k, v in headers:
        if k.lower() == name:
            return v.decode("latin-1")
    return ""


def _resource_url(scope) -> str:
    scheme = scope.get("scheme", "http")
    host_header = _get_header(scope["headers"], b"host")
    if host_header:
        base = f"{scheme}://{host_header}"
    else:
        host, port = scope.get("server", ("localhost", 80))
        base = f"{scheme}://{host}:{port}"
    path = scope.get("path", "/")
    query = scope.get("query_string", b"").decode("latin-1")
    return f"{base}{path}" + (f"?{query}" if query else "")


async def _send_challenge(scope, send) -> None:
    challenge = build_challenge(_resource_url(scope))
    body_bytes = json.dumps(challenge).encode("utf-8")
    encoded = base64.b64encode(body_bytes).decode("ascii")
    await send({
        "type": "http.response.start",
        "status": 402,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body_bytes)).encode("ascii")),
            (b"payment-required", encoded.encode("ascii")),
        ],
    })
    await send({"type": "http.response.body", "body": body_bytes})


class X402Middleware:
    """Raw ASGI middleware -- see module docstring for why not BaseHTTPMiddleware."""

    def __init__(self, app, mcp_path: str):
        self.app = app
        self.mcp_path = mcp_path

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") != self.mcp_path:
            await self.app(scope, receive, send)
            return

        headers = scope["headers"]
        if _get_header(headers, b"authorization") or _get_header(headers, b"x-payment"):
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")

        if method == "GET":
            if "text/event-stream" in _get_header(headers, b"accept"):
                await self.app(scope, receive, send)  # real MCP client's SSE channel
            else:
                await _send_challenge(scope, send)  # bare probe, no MCP session
            return

        if method != "POST":
            await _send_challenge(scope, send)
            return

        # Buffer the full body ourselves so we can inspect it, then replay
        # the exact same ASGI messages to the downstream app.
        messages = []
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            messages.append(message)
            body += message.get("body", b"")
            more_body = message.get("more_body", False)

        try:
            payload = json.loads(body) if body else None
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None

        gate = True
        if payload is not None:
            rpc_method = payload.get("method")
            if rpc_method in FREE_RPC_METHODS:
                gate = False
            elif rpc_method == "tools/call":
                tool_name = (payload.get("params") or {}).get("name")
                gate = tool_name == GATED_TOOL_NAME
                # Any other tool name (including unrecognized ones) is let
                # through -- FREE_TOOL_NAMES or an unknown name that MCP
                # itself should report as an error, not us guessing.
            else:
                gate = True

        if gate:
            await _send_challenge(scope, send)
            return

        # Replay the buffered messages first, then fall through to the
        # REAL underlying receive() for anything after -- streamable-http
        # holds the connection open for a streaming session, so faking a
        # disconnect once the buffer is drained (rather than passing
        # through genuine subsequent events) breaks the session mid-flight.
        idx = 0

        async def replay_receive():
            nonlocal idx
            if idx < len(messages):
                m = messages[idx]
                idx += 1
                return m
            return await receive()

        await self.app(scope, replay_receive, send)
