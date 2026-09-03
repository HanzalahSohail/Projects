"""
Tool Registry & Execution Engine

Manages tool discovery, registration, validation, execution, retry, and timeout.
Each tool is defined with:
  - name, description
  - JSON schema for parameters (used by Azure OpenAI function calling)
  - An async execute() function
"""

import asyncio
import json
import time
import traceback
from typing import Any, Callable, Optional
from pydantic import BaseModel


class ToolResult(BaseModel):
    """Standardized result from tool execution."""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0


class Tool:
    """A single tool that the LLM can call."""

    def __init__(self, name: str, description: str, parameters: dict,
                 execute_fn: Callable, retries: int = 1, timeout: float = 30.0):
        self.name = name
        self.description = description
        self.parameters = parameters  # JSON Schema dict
        self.execute_fn = execute_fn
        self.retries = retries
        self.timeout = timeout

    def to_openai_schema(self) -> dict:
        """Convert to Azure OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Execute with retry and timeout."""
        last_error = None

        for attempt in range(1, self.retries + 1):
            start = time.time()
            try:
                result = await asyncio.wait_for(
                    self.execute_fn(**kwargs),
                    timeout=self.timeout
                )
                elapsed = round((time.time() - start) * 1000, 1)
                print(f"[TOOL] {self.name} succeeded in {elapsed}ms (attempt {attempt})")
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    result=result,
                    execution_time_ms=elapsed
                )
            except asyncio.TimeoutError:
                elapsed = round((time.time() - start) * 1000, 1)
                last_error = f"Timeout after {self.timeout}s"
                print(f"[TOOL] {self.name} timeout (attempt {attempt}/{self.retries})")
            except Exception as e:
                elapsed = round((time.time() - start) * 1000, 1)
                last_error = str(e)
                print(f"[TOOL] {self.name} error (attempt {attempt}/{self.retries}): {e}")
                traceback.print_exc()

        return ToolResult(
            tool_name=self.name,
            success=False,
            error=last_error,
            execution_time_ms=round((time.time() - start) * 1000, 1)
        )


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self._tools[tool.name] = tool
        print(f"[REGISTRY] Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_openai_tools(self) -> list[dict]:
        """Get all tools in Azure OpenAI function-calling format."""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, arguments: dict) -> ToolResult:
        """Look up and execute a tool by name."""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}"
            )
        return await tool.execute(**arguments)

    def get_tool_descriptions(self) -> str:
        """Human-readable list of tools for logging."""
        lines = []
        for name, tool in self._tools.items():
            lines.append(f"  - {name}: {tool.description}")
        return "\n".join(lines)


# Global registry instance
registry = ToolRegistry()