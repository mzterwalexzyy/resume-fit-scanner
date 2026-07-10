"""
Calls the REAL deployed MCP endpoint over the public internet (not
localhost) as a proper MCP client, and pretty-prints the result. Meant to
be run on-camera to prove the ASP is actually live at its registered
endpoint, not just running locally.

Run with:  py demo/live_check.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from tests.samples import PAIRS

ENDPOINT = "https://resume-fit.145-241-206-88.sslip.io/mcp"


async def main():
    print(f"Connecting to LIVE endpoint: {ENDPOINT}\n")

    resume_text, jd_text = PAIRS["strong_match"]

    async with streamablehttp_client(ENDPOINT) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print(f"Tools available on the live server: {[t.name for t in tools.tools]}\n")

            print("Calling analyze_resume_fit with a real resume + job description...\n")
            result = await session.call_tool("analyze_resume_fit", {
                "resume_text": resume_text,
                "job_description_text": jd_text,
            })
            parsed = json.loads(result.content[0].text)
            print(json.dumps(parsed, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
