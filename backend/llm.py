import json
import os
from typing import Type, TypeVar

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

load_dotenv()

T = TypeVar("T", bound=BaseModel)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Build the OpenAI client lazily.

    Recent OpenAI SDKs raise on construction when no key is set, so creating the
    client at import time would make this module unimportable without a key.
    Building it on first use keeps the module importable for tests and lets the
    key be required only when a call is actually made.
    """
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def call_llm(
    messages: list[dict],
    model: str = "gpt-4o",
    temperature: float = 0,
) -> str:
    """Call the OpenAI API and return the response content."""
    response = _get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content


def call_llm_json(
    messages: list[dict],
    schema: Type[T],
    model: str = "gpt-4o",
    temperature: float = 0,
    max_retries: int = 1,
) -> T:
    """Call the LLM in JSON mode and validate the response against a Pydantic schema.

    On a parse or validation error we feed the error back to the model and retry,
    so a single malformed response does not crash an agent. Raises the last error
    if all attempts fail; the orchestrator turns that into a graceful report error.
    """
    # OpenAI's json_object mode requires the word "json" somewhere in the prompt.
    convo = [
        {
            "role": "system",
            "content": "You must respond with a single valid JSON object and nothing else.",
        },
        *messages,
    ]

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        response = _get_client().chat.completions.create(
            model=model,
            messages=convo,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        try:
            data = json.loads(content)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as err:
            last_error = err
            # Show the model exactly what was wrong and ask it to fix the JSON.
            convo += [
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": (
                        f"That was not valid for the required schema. Error:\n{err}\n"
                        "Return a corrected JSON object that satisfies the schema."
                    ),
                },
            ]

    raise RuntimeError(f"Failed to get valid JSON after {max_retries + 1} attempts: {last_error}")
