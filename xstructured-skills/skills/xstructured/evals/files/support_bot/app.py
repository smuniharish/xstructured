"""A support bot that answers customers and files tickets.

The ticket fields are currently pulled out of the reply with a regular
expression, which breaks whenever the model words things differently.
"""

import re

from langchain.chat_models import init_chat_model

model = init_chat_model("openai:gpt-5-mini")

PROMPT = (
    "You are a support agent. Answer the customer, then on the last line write "
    "PRIORITY: <low|high|critical> TEAM: <team name>.\n\nCustomer: {message}"
)


def answer(message: str) -> tuple[str, dict[str, str]]:
    reply = model.invoke(PROMPT.format(message=message)).text
    match = re.search(r"PRIORITY:\s*(\w+)\s+TEAM:\s*(.+)$", reply)
    ticket = (
        {"priority": match.group(1), "team": match.group(2)} if match else {}
    )
    return reply.rsplit("PRIORITY:", 1)[0].strip(), ticket
