from __future__ import annotations

import base64
import os
from typing import TypeVar

from anthropic import Anthropic
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIConfigurationError(RuntimeError):
    pass


def configured() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def structured_response(instructions: str, user_input: str, schema: type[T],
                        pdf_bytes: bytes | None = None) -> T:
    if not configured():
        raise AIConfigurationError("ANTHROPIC_API_KEY not found. Set it in .env or your environment.")
    content: list[dict] = []
    if pdf_bytes:
        content.append({
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.standard_b64encode(pdf_bytes).decode("ascii"),
            },
        })
    content.append({"type": "text", "text": user_input})
    client = Anthropic()
    response = client.messages.parse(
        model=os.getenv("ANTHROPIC_MODEL", "claude-opus-5"),
        max_tokens=16000,
        system=instructions,
        messages=[{"role": "user", "content": content}],
        output_format=schema,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("The model declined this request. Adjust the input and try again.")
    if response.parsed_output is None:
        raise RuntimeError("The model did not return a parseable structured result.")
    return response.parsed_output
