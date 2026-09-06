from types import SimpleNamespace as NS
from unittest.mock import AsyncMock
import pytest
from app.config import Settings
from app.services.llm import Provider
from app.services.rag import RAG, chunks
from app.services.orchestrator import Orchestrator


async def test_tenant_isolation():
    rag = RAG(Settings(_env_file=None), None)
    await rag.ingest("a", "file", "confidential zebra")
    assert await rag.retrieve("a", "zebra")
    assert not await rag.retrieve("b", "zebra")


def test_chunk_overlap():
    text = "x" * 2500
    parts = chunks(text)
    assert len(parts) == 3 and parts[0][-150:] == parts[1][:150]


async def test_responses_tool_roundtrip():
    client = NS(
        responses=NS(
            create=AsyncMock(
                side_effect=[
                    NS(
                        output=[
                            NS(
                                type="function_call",
                                name="get_service_status",
                                arguments="{}",
                                call_id="call_1",
                            )
                        ]
                    ),
                    NS(output=[], output_text="operational"),
                ]
            )
        )
    )
    tool = AsyncMock(return_value={"status": "operational"})
    provider = Provider(Settings(_env_file=None), client)
    answer, route = await provider.generate("status", [], tool)
    assert (answer, route) == ("operational", "tool")
    tool.assert_awaited_once()
    assert client.responses.create.call_args.kwargs["store"] is False
    assert client.responses.create.call_args.kwargs["input"][-1]["call_id"] == "call_1"


async def test_unknown_tool_rejected():
    client = NS(
        responses=NS(
            create=AsyncMock(
                return_value=NS(output=[NS(type="function_call", name="shell", arguments="{}")])
            )
        )
    )
    with pytest.raises(ValueError):
        await Provider(Settings(_env_file=None), client).generate("hello", [], AsyncMock())


async def test_output_guardrail():
    provider = NS(generate=AsyncMock(return_value=("sk-abcdefghijklmnop", "llm")))
    rag = NS(retrieve=AsyncMock(return_value=[]))
    result = await Orchestrator(provider, rag, AsyncMock()).run("hello")
    assert result.blocked and not result.citations and "sk-" not in result.answer


async def test_embedding_dimensions():
    client = NS(
        embeddings=NS(create=AsyncMock(return_value=NS(data=[NS(index=0, embedding=[1.0])])))
    )
    await Provider(Settings(_env_file=None), client).embed(["text"])
    assert client.embeddings.create.call_args.kwargs["dimensions"] == 1536
