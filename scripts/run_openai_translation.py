"""Run translation prompts locally with selection and resume support."""
import os
import sys
import time
from pathlib import Path
from typing import Any
import argparse
import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from lexconflict import run_openai as local_backend
from lexconflict.local_run import run_prompts
RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}

def get_base_url() -> str:
    return os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")

def get_headers() -> dict[str, str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    organization = os.environ.get("OPENAI_ORG_ID") or os.environ.get("OPENAI_ORGANIZATION")
    project = os.environ.get("OPENAI_PROJECT_ID") or os.environ.get("OPENAI_PROJECT")
    if organization:
        headers["OpenAI-Organization"] = organization
    if project:
        headers["OpenAI-Project"] = project
    return headers

def nested(data: dict[str, Any], keys: list[str], default: Any = "") -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value

def extract_text(data: dict[str, Any]) -> str:
    if isinstance(data.get("output_text"), str):
        return data["output_text"]

    pieces: list[str] = []
    for item in data.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if isinstance(content, dict) and isinstance(content.get("text"), str):
                pieces.append(content["text"])
            elif isinstance(content, str):
                pieces.append(content)
    return "\n".join(pieces)

def build_payload(args: argparse.Namespace, prompt: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": args.model,
        "input": prompt,
        "max_output_tokens": args.max_output_tokens,
        "store": args.store == "true",
    }
    if args.reasoning_effort != "unset":
        payload["reasoning"] = {"effort": args.reasoning_effort}
    if args.text_verbosity != "unset":
        payload["text"] = {"verbosity": args.text_verbosity}
    if args.temperature is not None:
        payload["temperature"] = args.temperature
    return payload

def retry_delay(response: requests.Response, attempt: int, initial_sleep: float) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return initial_sleep * (2**attempt)

def call_openai(session: requests.Session, args: argparse.Namespace, prompt: str) -> dict[str, Any]:
    payload = build_payload(args, prompt)
    url = f"{get_base_url()}/responses"
    headers = get_headers()
    last_error = ""

    for attempt in range(args.max_retries + 1):
        response = session.post(url, headers=headers, json=payload, timeout=args.timeout)
        if response.status_code < 400:
            data = response.json()
            usage = data.get("usage") or {}
            return {
                "response": extract_text(data),
                "openai_response_id": data.get("id", ""),
                "openai_status": data.get("status", ""),
                "openai_incomplete_reason": nested(data, ["incomplete_details", "reason"]),
                "input_tokens": usage.get("input_tokens", ""),
                "output_tokens": usage.get("output_tokens", ""),
                "total_tokens": usage.get("total_tokens", ""),
                "reasoning_tokens": nested(usage, ["output_tokens_details", "reasoning_tokens"]),
            }

        last_error = f"OpenAI request failed with HTTP {response.status_code}"
        if response.status_code not in RETRYABLE_STATUS_CODES or attempt == args.max_retries:
            break

        seconds = retry_delay(response, attempt, args.retry_initial_sleep)
        print(
            f"Retryable OpenAI status {response.status_code}; sleeping {seconds:.1f}s "
            f"before retry {attempt + 1}/{args.max_retries}.",
            flush=True,
        )
        time.sleep(seconds)

    raise RuntimeError(last_error)

def main(argv=None):
    args = local_backend.parse_args(argv)
    parameters = {
        'provider': 'openai', 'max_output_tokens': args.max_output_tokens,
        'reasoning_effort': args.reasoning_effort, 'text_verbosity': args.text_verbosity,
        'temperature': args.temperature, 'store': args.store,
    }
    defaults = dict(response='', openai_status='', openai_incomplete_reason='',
                    input_tokens='', output_tokens='', total_tokens='', reasoning_tokens='')
    def request(prompt):
        result = call_openai(session, args, prompt)
        result.pop('openai_response_id', None)
        return result
    with requests.Session() as session:
        return run_prompts(args, request, defaults, parameters)

if __name__ == '__main__':
    raise SystemExit(main())
