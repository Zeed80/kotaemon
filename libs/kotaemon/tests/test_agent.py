from unittest.mock import patch

import pytest
from openai.types.chat.chat_completion import ChatCompletion

from kotaemon.agents import (
    AgentType,
    BaseTool,
    GoogleSearchTool,
    LangchainAgent,
    LLMTool,
    ReactAgent,
    RewooAgent,
    WikipediaTool,
)
from kotaemon.llms import AzureChatOpenAI, LCAzureChatOpenAI

from .conftest import skip_openai_lc_wrapper_test, skip_when_ddgs_not_installed

FINAL_RESPONSE_TEXT = "Final Answer: Hello Cinnamon AI!"
REWOO_VALID_PLAN = (
    "#Plan1: Search for Cinnamon AI company on Google\n"
    "#E1: google_search[Cinnamon AI company]\n"
    "#Plan2: Search for Cinnamon on Wikipedia\n"
    "#E2: wikipedia[Cinnamon]\n"
)
REWOO_INVALID_PLAN = (
    "#E1: google_search[Cinnamon AI company]\n"
    "#Plan2: Search for Cinnamon on Wikipedia\n"
    "#E2: wikipedia[Cinnamon]\n"
)


def generate_chat_completion_obj(text):
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-7qyuw6Q1CFCpcKsMdFkmUPUa7JP2x",
            "object": "chat.completion",
            "created": 1692338378,
            "model": "gpt-35-turbo",
            "system_fingerprint": None,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": text,
                        "function_call": None,
                        "tool_calls": None,
                    },
                    "logprobs": None,
                }
            ],
            "usage": {"completion_tokens": 9, "prompt_tokens": 10, "total_tokens": 19},
        }
    )


class _RawResponseLike:
    """Mock for openai with_raw_response.create() return value — has .parse()."""

    def __init__(self, completion: ChatCompletion):
        self._completion = completion

    def parse(self) -> ChatCompletion:
        return self._completion


def _wrap_for_langchain(completion: ChatCompletion) -> _RawResponseLike:
    return _RawResponseLike(completion)


_openai_chat_completion_responses_rewoo = [
    generate_chat_completion_obj(text=text)
    for text in [REWOO_VALID_PLAN, FINAL_RESPONSE_TEXT]
]

_openai_chat_completion_responses_rewoo_error = [
    generate_chat_completion_obj(text=text)
    for text in [REWOO_INVALID_PLAN, FINAL_RESPONSE_TEXT]
]

_openai_chat_completion_responses_react = [
    generate_chat_completion_obj(text=text)
    for text in [
        (
            "I don't have prior knowledge about Cinnamon AI company, "
            "so I should gather information about it.\n"
            "Action: wikipedia\n"
            "Action Input: Cinnamon AI company\n"
        ),
        (
            "The information retrieved from Wikipedia is not "
            "about Cinnamon AI company, but about Blue Prism, "
            "a British multinational software corporation. "
            "I need to try another source to gather information "
            "about Cinnamon AI company.\n"
            "Action: google_search\n"
            "Action Input: Cinnamon AI company\n"
        ),
        FINAL_RESPONSE_TEXT,
    ]
]

_openai_chat_completion_responses_react_langchain_tool = [
    generate_chat_completion_obj(text=text)
    for text in [
        (
            "I don't have prior knowledge about Cinnamon AI company, "
            "so I should gather information about it.\n"
            "Action: wikipedia\n"
            "Action Input: Cinnamon AI company\n"
        ),
        # (
        #     "The information retrieved from Wikipedia is not "
        #     "about Cinnamon AI company, but about Blue Prism, "
        #     "a British multinational software corporation. "
        #     "I need to try another source to gather information "
        #     "about Cinnamon AI company.\n"
        #     "Action: duckduckgo_search\n"
        #     "Action Input: Cinnamon AI company\n"
        # ),
        FINAL_RESPONSE_TEXT,
    ]
]


@pytest.fixture
def llm():
    return AzureChatOpenAI(
        api_key="dummy",
        api_version="2024-05-01-preview",
        azure_deployment="gpt-4o",
        azure_endpoint="https://test.openai.azure.com/",
    )


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=_openai_chat_completion_responses_rewoo_error,
)
def test_agent_fail(openai_completion, llm, mock_google_search):
    plugins = [
        GoogleSearchTool(),
        WikipediaTool(),
        LLMTool(llm=llm),
    ]

    agent = RewooAgent(planner_llm=llm, solver_llm=llm, plugins=plugins)

    response = agent("Tell me about Cinnamon AI company")
    openai_completion.assert_called()
    assert not response
    assert response.status == "failed"


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=_openai_chat_completion_responses_rewoo,
)
def test_rewoo_agent(openai_completion, llm, mock_google_search):
    plugins = [
        GoogleSearchTool(),
        WikipediaTool(),
        LLMTool(llm=llm),
    ]

    agent = RewooAgent(planner_llm=llm, solver_llm=llm, plugins=plugins)

    response = agent("Tell me about Cinnamon AI company")
    openai_completion.assert_called()
    assert response.text == FINAL_RESPONSE_TEXT


@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=_openai_chat_completion_responses_react,
)
def test_react_agent(openai_completion, llm, mock_google_search):
    plugins = [
        GoogleSearchTool(),
        WikipediaTool(),
        LLMTool(llm=llm),
    ]
    agent = ReactAgent(llm=llm, plugins=plugins, max_iterations=4)

    response = agent("Tell me about Cinnamon AI company")
    openai_completion.assert_called()
    assert response.text == FINAL_RESPONSE_TEXT


@skip_openai_lc_wrapper_test
@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=[
        _wrap_for_langchain(c) for c in _openai_chat_completion_responses_react
    ],
)
def test_react_agent_langchain(openai_completion, mock_google_search):
    from langgraph.prebuilt import create_react_agent

    llm = LCAzureChatOpenAI(
        api_key="dummy",
        api_version="2024-05-01-preview",
        deployment_name="gpt-4o",
        azure_endpoint="https://test.openai.azure.com/",
    )
    plugins = [
        GoogleSearchTool(),
        WikipediaTool(),
        LLMTool(llm=llm),
    ]
    langchain_plugins = [tool.to_langchain_format() for tool in plugins]
    graph = create_react_agent(
        model=llm.to_langchain_format(),
        tools=langchain_plugins,
        prompt="You are a helpful assistant.",
    )
    result = graph.invoke(
        {"messages": [{"role": "user", "content": "Tell me about Cinnamon AI company"}]}
    )
    openai_completion.assert_called()
    assert result and "messages" in result


@skip_openai_lc_wrapper_test
@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=[
        _wrap_for_langchain(c) for c in _openai_chat_completion_responses_react
    ],
)
def test_wrapper_agent_langchain(openai_completion, mock_google_search):
    llm = LCAzureChatOpenAI(
        api_key="dummy",
        api_version="2024-05-01-preview",
        deployment_name="gpt-4o",
        azure_endpoint="https://test.openai.azure.com/",
    )
    plugins = [
        GoogleSearchTool(),
        WikipediaTool(),
        LLMTool(llm=llm),
    ]
    agent = LangchainAgent(
        llm=llm,
        plugins=plugins,
        agent_type=AgentType.react,
    )
    response = agent("Tell me about Cinnamon AI company")
    openai_completion.assert_called()
    assert response


@skip_when_ddgs_not_installed
@patch(
    "openai.resources.chat.completions.Completions.create",
    side_effect=_openai_chat_completion_responses_react_langchain_tool,
)
def test_react_agent_with_langchain_tools(openai_completion, llm):
    from langchain_community.tools import DuckDuckGoSearchRun, WikipediaQueryRun
    from langchain_community.utilities import WikipediaAPIWrapper

    wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
    search = DuckDuckGoSearchRun()

    langchain_plugins = [wikipedia, search]
    plugins = [BaseTool.from_langchain_format(tool) for tool in langchain_plugins]
    agent = ReactAgent(llm=llm, plugins=plugins, max_iterations=4)

    response = agent("Tell me about Cinnamon AI company")
    openai_completion.assert_called()
    assert response.text == FINAL_RESPONSE_TEXT
