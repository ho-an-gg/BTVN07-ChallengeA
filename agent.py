"""LangChain agent của stage 04: read_file, write_file, bash + skill catalog trong system prompt."""

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

import paths
from config import MODEL_CALL_LIMIT, TOOL_CALL_LIMIT, Settings
from observer import ObserverMiddleware
from prompts import build_system_prompt
from skill_catalog import Catalog, render_catalog, scan_skills
from tools import bash, read_file, write_file
from memory import render_memory, update_project_memory

TOOLS = [read_file, write_file, bash, update_project_memory]


def build_model(settings: Settings):
    if settings.provider == "google":
        # Gemini's native adapter preserves provider thought signatures across tool turns.
        return ChatGoogleGenerativeAI(model=settings.model_name, api_key=settings.api_key)
    kwargs = {"model": settings.model_name, "api_key": settings.api_key}
    if settings.base_url:
        kwargs["base_url"] = settings.base_url
    return ChatOpenAI(**kwargs)


def load_catalog() -> Catalog:
    return scan_skills(paths.WORKSPACE_DIR)


def system_prompt() -> str:
    return build_system_prompt(render_catalog(load_catalog()), render_memory())


def capabilities() -> dict:
    catalog = load_catalog()
    return {"tools": [t.name for t in TOOLS], "skills": catalog.metadata(), "skill_diagnostics": catalog.diagnostics}


def build_agent(model):
    return create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=system_prompt(),
        middleware=[
            ModelCallLimitMiddleware(run_limit=MODEL_CALL_LIMIT, exit_behavior="end"),
            ToolCallLimitMiddleware(run_limit=TOOL_CALL_LIMIT),
            ObserverMiddleware(),  # cuối danh sách = sát model/tool invocation nhất
        ],
    )
