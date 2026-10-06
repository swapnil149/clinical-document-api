from anthropic import Anthropic
from pydantic import BaseModel

from app.tools import get_document, search_documents


client = Anthropic()


class AgentResponse(BaseModel):
    document_id: int
    patient_id: str
    document_type: str
    answer: str


def run_agent(user_message: str) -> AgentResponse:

    runner = client.beta.messages.tool_runner(
        model="claude-haiku-4-5",
        max_tokens=500,
        tools=[get_document, search_documents],
        output_format=AgentResponse,

        system="""
You are an assistant for synthetic clinical documents.

Use only information explicitly provided by the available tools when answering
questions about clinical documents.

Do not infer, add, or introduce medical facts that are not present in the
tool results.

If the available information is insufficient to answer a question, say that
the available information does not provide enough information.
""",

        messages=[
            {
                "role": "user",
                "content": user_message
            }
        ],
    )

    final_message = runner.until_done()

    return final_message.parsed_output