from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from app.models import ChatResponse, Citation
from app.services.guardrails import check_input, check_output


class State(TypedDict, total=False):
    message: str
    tenant: str
    docs: list
    response: ChatResponse
    blocked: bool


class Orchestrator:
    def __init__(self, provider, rag, status_tool):
        self.provider, self.rag, self.status_tool = provider, rag, status_tool
        graph = StateGraph(State)
        graph.add_node("input_gate", self.input_gate)
        graph.add_node("retrieve", self.retrieve)
        graph.add_node("generate", self.generate)
        graph.add_node("output_gate", self.output_gate)
        graph.add_edge(START, "input_gate")
        graph.add_conditional_edges(
            "input_gate",
            lambda s: "blocked" if s["blocked"] else "allowed",
            {"blocked": END, "allowed": "retrieve"},
        )
        graph.add_edge("retrieve", "generate")
        graph.add_edge("generate", "output_gate")
        graph.add_edge("output_gate", END)
        self.graph = graph.compile()

    async def input_gate(self, state):
        gate = check_input(state["message"])
        return {
            "blocked": not gate.allowed,
            "response": ChatResponse(
                answer=gate.reason or "", route="guardrail", blocked=not gate.allowed
            ),
        }

    async def retrieve(self, state):
        return {"docs": await self.rag.retrieve(state["tenant"], state["message"])}

    async def generate(self, state):
        answer, route = await self.provider.generate(
            state["message"], state["docs"], self.status_tool
        )
        return {
            "response": ChatResponse(
                answer=answer,
                route=route,
                citations=[
                    Citation(source=d["source"], snippet=d["text"][:300], chunk_id=d["chunk_id"])
                    for d in state["docs"]
                ],
            )
        }

    async def output_gate(self, state):
        result = state["response"]
        if not check_output(result.answer + " ".join(c.snippet for c in result.citations)).allowed:
            result = ChatResponse(
                answer="Response blocked by safety checks.", route="output_guardrail", blocked=True
            )
        return {"response": result}

    async def run(self, message, tenant="demo"):
        return (
            await self.graph.ainvoke(
                {"message": message, "tenant": tenant}, config={"recursion_limit": 10}
            )
        )["response"]
