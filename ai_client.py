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


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def structured_response(instructions: str, user_input: str, schema: type[T],
                        pdf_bytes: bytes | None = None, name: str | None = None) -> T:
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
    model = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")
    trace_name = name or f"structured:{schema.__name__}"

    if tracing_enabled():
        from langfuse import get_client

        langfuse = get_client()
        with langfuse.start_as_current_generation(
            name=trace_name,
            model=model,
            input={"system": instructions, "user": user_input, "has_pdf": bool(pdf_bytes)},
            metadata={"schema": schema.__name__},
        ) as generation:
            response = _call(model, instructions, content, schema)
            generation.update(
                output=(response.parsed_output.model_dump(mode="json")
                        if response.parsed_output is not None else {"stop_reason": response.stop_reason}),
                usage_details={
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens,
                },
            )
        langfuse.flush()
    else:
        response = _call(model, instructions, content, schema)

    if response.stop_reason == "refusal":
        raise RuntimeError("The model declined this request. Adjust the input and try again.")
    if response.parsed_output is None:
        raise RuntimeError("The model did not return a parseable structured result.")
    return response.parsed_output


def _call(model: str, instructions: str, content: list[dict], schema: type[T]):
    client = Anthropic()
    return client.messages.parse(
        model=model,
        max_tokens=16000,
        system=instructions,
        messages=[{"role": "user", "content": content}],
        output_format=schema,
    )
