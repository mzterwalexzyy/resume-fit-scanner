"""
Regression test for mcp_server/x402_middleware.py, exercised directly
against the ASGI middleware (not the real MCP app) so this doesn't need a
full MCP protocol handshake to verify. Locks in the fix for OKX's ASP review
finding: an unauthenticated call must get HTTP 402, not fall through to
FastMCP's own 406, while initialize/tools-list/the free ping tool must stay
reachable so a real MCP client can still complete its handshake.

Run with:  py -m tests.test_x402_middleware     (from the project root)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from mcp_server.x402_middleware import GATED_TOOL_NAME, X402Middleware


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


async def _echo(request):
    return JSONResponse({"ok": True, "path": request.url.path})


def _make_client(mcp_path="/mcp"):
    app = Starlette(routes=[Route(mcp_path, _echo, methods=["GET", "POST"])])
    app.add_middleware(X402Middleware, mcp_path=mcp_path)
    return TestClient(app)


def main():
    client = _make_client()

    print("\n=== bare GET (naive compliance probe) ===")
    resp = client.get("/mcp")
    print("status:", resp.status_code)
    _assert(resp.status_code == 402, f"expected 402 for a bare unauthenticated GET, got {resp.status_code}")
    body = resp.json()
    _assert(body["x402Version"] == 1, "challenge body must carry x402Version")
    accepts = body["accepts"][0]
    _assert(accepts["scheme"] == "exact", "expected the 'exact' x402 scheme")
    _assert(accepts["network"] == "eip155:196", "expected X Layer (eip155:196)")
    # Regression check for an OKX review finding: `maxAmountRequired` is the
    # "upto" scheme's field (a variable cap); "exact" (a fixed price, which
    # is what this ASP actually charges) must use `amount` instead.
    _assert("amount" in accepts, "'exact' scheme must carry 'amount', not 'maxAmountRequired'")
    _assert("maxAmountRequired" not in accepts, "'maxAmountRequired' is only valid for scheme 'upto'")
    payment_header = resp.headers.get("payment-required")
    _assert(payment_header, "expected a PAYMENT-REQUIRED header alongside the 402")

    print("\n=== GET with Accept: text/event-stream (real MCP client's SSE channel) ===")
    resp = client.get("/mcp", headers={"accept": "text/event-stream"})
    print("status:", resp.status_code)
    _assert(resp.status_code != 402, "an SSE-accepting GET must never be gated")

    print("\n=== JSON-RPC initialize (must stay free) ===")
    resp = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    print("status:", resp.status_code)
    _assert(resp.status_code == 200, "initialize must never require payment")

    print("\n=== JSON-RPC tools/list (must stay free) ===")
    resp = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    print("status:", resp.status_code)
    _assert(resp.status_code == 200, "tools/list must never require payment")

    print("\n=== tools/call ping (the free health-check tool) ===")
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ping"}},
    )
    print("status:", resp.status_code)
    _assert(resp.status_code == 200, "the free ping tool must never require payment")

    print(f"\n=== tools/call {GATED_TOOL_NAME} without payment ===")
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": GATED_TOOL_NAME}},
    )
    print("status:", resp.status_code)
    _assert(resp.status_code == 402, f"{GATED_TOOL_NAME} must require payment when none is presented")

    print(f"\n=== tools/call {GATED_TOOL_NAME} replayed with PAYMENT-SIGNATURE (the correct x402 v2 replay header) ===")
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": GATED_TOOL_NAME}},
        headers={"payment-signature": "dummy-test-proof"},
    )
    print("status:", resp.status_code)
    _assert(resp.status_code == 200,
            "PAYMENT-SIGNATURE is the actual replay header for this challenge shape (per OKX's own docs) -- "
            "regression check for the bug their review reported: a correctly-signed replay was still getting re-challenged")

    print(f"\n=== tools/call {GATED_TOOL_NAME} WITH an Authorization header present (also accepted) ===")
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": GATED_TOOL_NAME}},
        headers={"authorization": "Payment dummy-test-proof"},
    )
    print("status:", resp.status_code)
    _assert(resp.status_code == 200, "a request carrying any payment header must be let through")

    print("\n=== malformed body (not valid JSON) ===")
    resp = client.post("/mcp", content=b"not json", headers={"content-type": "application/json"})
    print("status:", resp.status_code)
    _assert(resp.status_code == 402, "an unparseable body on the MCP path must default to requiring payment")

    print("\n=== a path other than the configured MCP endpoint is never gated ===")
    other_app = Starlette(routes=[Route("/other", _echo, methods=["GET"])])
    other_app.add_middleware(X402Middleware, mcp_path="/mcp")
    other_client = TestClient(other_app)
    resp = other_client.get("/other")
    print("status:", resp.status_code)
    _assert(resp.status_code == 200, "a path other than mcp_path must never be gated, even unauthenticated")

    print("\nAll x402 middleware assertions passed.")


if __name__ == "__main__":
    main()
