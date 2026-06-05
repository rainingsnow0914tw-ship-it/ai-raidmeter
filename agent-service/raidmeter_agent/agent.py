"""AI RaidMeter ADK agent.

Where the three required pillars meet:
  - Gemini 3.1 Pro on Vertex  (the model)
  - Google Cloud Agent Builder / ADK  (the agent framework)
  - Arize Phoenix MCP server  (the Partner MCP server)

A Gemini-driven agent that reads REAL LLM traces from Arize Phoenix
through the Phoenix MCP server and reasons, in plain language, about
token/latency efficiency and the seven AI-coding "sins". Config-driven:
model / Phoenix endpoint / key all come from env (the same secret file).
"""
import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

MODEL = os.environ.get("RAIDMETER_MODEL", "gemini-3.1-pro-preview")
PHOENIX_ENDPOINT = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "")
PHOENIX_KEY = os.environ.get("PHOENIX_API_KEY", "")

INSTRUCTION = (
    "You are AI RaidMeter, a green-coding coach for AI-assisted engineering. "
    "You have tools connected to an Arize Phoenix instance via MCP. Use them "
    "to list projects, fetch recent traces, and inspect spans (token counts, "
    "latency, model). When the user asks about a project or a session, pull "
    "the real traces and reason about efficiency and the seven anti-patterns: "
    "full-file devotion, local loop, blind retry, context hoarding, sticky "
    "command. Judge like a clinician: multi-criteria, never a single-signal "
    "verdict, and compare a developer only with their own past baseline. "
    "Be concrete: cite the real token/latency numbers you read from Phoenix. "
    "IMPORTANT - stay within context limits: focus on the ai-raidmeter project unless the user explicitly asks about another. When inspecting traces, fetch only summaries or at most 3 traces, and NEVER pull the full span or message contents of many traces at once -- it overflows the model context. For large projects, report counts and top items instead of dumping raw spans. "
    "BE FAST - latency is the user experience: answer in at most 3 tool calls total, then give your final report. Do NOT exhaustively inspect every span, annotation, or trace -- get the key data in 2-3 calls and conclude immediately."
)

root_agent = LlmAgent(
    model=MODEL,
    name="raidmeter_agent",
    instruction=INSTRUCTION,
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="npx",
                    args=[
                        "-y",
                        "@arizeai/phoenix-mcp",
                        "--baseUrl",
                        PHOENIX_ENDPOINT,
                        "--apiKey",
                        PHOENIX_KEY,
                    ],
                ),
            ),
        )
    ],
)
