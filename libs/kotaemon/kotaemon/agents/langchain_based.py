from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from kotaemon.llms import LLM, ChatLLM

from .base import BaseAgent
from .io import AgentOutput, AgentType
from .tools import BaseTool


class LangchainAgent(BaseAgent):
    """Wrapper for LangChain/LangGraph ReAct agent."""

    name: str = "LangchainAgent"
    agent_type: AgentType
    description: str = "LangchainAgent for answering multi-step reasoning questions"

    # create_react_agent returns CompiledStateGraph, not AgentExecutor
    _graph: Any = None  # CompiledStateGraph

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.agent_type not in (
            AgentType.openai,
            AgentType.openai_multi,
            AgentType.react,
            AgentType.self_ask,
        ):
            raise NotImplementedError(
                f"AgentType {self.agent_type} not supported by Langchain wrapper"
            )
        self.update_agent_tools()

    def update_agent_tools(self):
        assert isinstance(self.llm, (ChatLLM, LLM))
        langchain_plugins = [tool.to_langchain_format() for tool in self.plugins]

        # Fix for search_doc tool name: use "Intermediate Answer" for self-ask agent
        found_search_tool = False
        if self.agent_type == AgentType.self_ask:
            for plugin in langchain_plugins:
                if plugin.name == "search_doc":
                    plugin.name = "Intermediate Answer"
                    langchain_plugins = [plugin]
                    found_search_tool = True
                    break

        if (
            self.agent_type != AgentType.self_ask or found_search_tool
        ) and langchain_plugins:
            self._graph = create_react_agent(
                model=self.llm.to_langchain_format(),
                tools=langchain_plugins,
                prompt="You are a helpful assistant for answering multi-step reasoning questions.",
            )
        else:
            self._graph = None

    def add_tools(self, tools: list[BaseTool]) -> None:
        super().add_tools(tools)
        self.update_agent_tools()

    def run(self, instruction: str) -> AgentOutput:
        assert (
            self._graph is not None
        ), "Langchain agent graph is not correctly initialized"

        inputs = {"messages": [HumanMessage(content=instruction)]}
        state = self._graph.invoke(inputs)
        messages = state.get("messages", [])

        # Extract final answer from last AIMessage
        output = ""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and msg.content:
                output = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                break

        return AgentOutput(
            content=output,
            agent_type=self.agent_type,
            status="finished",
        )
