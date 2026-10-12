"""Run translation prompts locally with selection and resume support."""
import os
import sys
import time
from pathlib import Path
from typing import Any
import argparse
import requests
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from lexconflict import run_ollama as local_backend
from lexconflict.local_run import run_prompts
RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}

def get_ollama_url() -> str:
    port = os.environ.get("OLLAMA_PORT", "11434")
    return f"http://127.0.0.1:{port}/api/generate"

def parse_think(value: str, model: str) -> bool | None:
    value = value.lower()
    model_family = model.split(":", maxsplit=1)[0].lower()

    if value == "auto":
        return False if model_family == "qwen3" else None

    if value in {"unset", "none"}:
        return None

    if value == "true":
        return True

    if value == "false":
        return False

    raise ValueError(f"Unexpected think value: {value}")

def call_ollama(
    prompt: str,
    model: str,
    temperature: float,
    seed: int,
    num_ctx: int,
    num_predict: int,
    think: str,
    timeout: int,
) -> dict:
    options = {
        "temperature": temperature,
        "seed": seed,
        "num_ctx": num_ctx,
        "num_predict": num_predict,
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": options,
    }

    think_value = parse_think(think, model)
    if think_value is not None:
        payload["think"] = think_value

    response = requests.post(get_ollama_url(), json=payload, timeout=timeout)

    if response.status_code != 200:
        raise RuntimeError(
            f"Ollama request failed with HTTP {response.status_code}"
        )

    response_json = response.json()
    response_text = response_json.get("response", "")
    thinking_text = response_json.get("thinking") or ""

    return {
        "response": str(response_text),
        "thinking": str(thinking_text).strip(),
        "think_resolved": "unset" if think_value is None else str(think_value).lower(),
        "done_reason": response_json.get("done_reason", ""),
        "prompt_eval_count": response_json.get("prompt_eval_count", ""),
        "eval_count": response_json.get("eval_count", ""),
    }

def main(argv=None):
    args = local_backend.parse_args(argv)
    resolved = parse_think(args.think, args.model)
    parameters = dict(provider='ollama', temperature=args.temperature, seed=args.seed,
                      num_ctx=args.num_ctx, num_predict=args.num_predict, think=args.think,
                      think_resolved='unset' if resolved is None else str(resolved).lower())
    defaults = dict(response='', thinking='', contains_think_tag=False,
                    ollama_done_reason='', prompt_eval_count='', eval_count='')
    def request(prompt):
        result = call_ollama(prompt, args.model, args.temperature, args.seed,
                             args.num_ctx, args.num_predict, args.think, args.timeout)
        result['ollama_done_reason'] = result.pop('done_reason')
        result['contains_think_tag'] = '<think>' in result['response'].lower()
        return result
    return run_prompts(args, request, defaults, parameters)

if __name__ == '__main__':
    raise SystemExit(main())
