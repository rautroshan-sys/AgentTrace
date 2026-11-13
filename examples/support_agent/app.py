import asyncio

from agenttrace.models.trace import SpanKind
from agenttrace.sdk.decorator import observe
from agenttrace.sdk.context import trace_agent


@observe(kind=SpanKind.TOOL, name="get_order_status")
async def get_order_status(order_id: str):
    raise TimeoutError("order service unavailable")


@observe(kind=SpanKind.LLM, name="generate_response")
async def generate_response(message: str, order):
    return "Your order has shipped."


@trace_agent(name="support-agent")
async def handle_user_request(message: str):
    order = await get_order_status("ORD-123")
    return await generate_response(message, order)


if __name__ == "__main__":
    asyncio.run(handle_user_request("Where is my order?"))