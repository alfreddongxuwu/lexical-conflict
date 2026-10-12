import json
import os
from contextlib import contextmanager
from pathlib import Path
import pandas as pd
import requests
from .paths import project_path
from .result_validity import clean_value, row_is_valid


def add_run_arguments(parser):
    parser.add_argument("--prompts", default="data/processed/prompts.csv")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--prompt-ids-file")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=float, default=300)


def read_prompts(args):
    if (
        args.start < 0
        or (args.limit is not None and args.limit <= 0)
        or args.timeout <= 0
    ):
        raise ValueError(
            "start must be nonnegative; limit and timeout must be positive"
        )
    prompts = pd.read_csv(project_path(args.prompts), dtype=str, keep_default_na=False)
    if not {"prompt_id", "prompt"}.issubset(prompts.columns):
        raise ValueError("Prompt file requires prompt_id and prompt columns")
    if (
        prompts.prompt_id.duplicated().any()
        or prompts.prompt_id.str.strip().eq("").any()
        or prompts.prompt.str.strip().eq("").any()
    ):
        raise ValueError(
            "Prompt identifiers must be unique and nonempty; prompts must be nonempty"
        )
    selected = prompts
    if args.prompt_ids_file:
        ids = [
            line.strip()
            for line in project_path(args.prompt_ids_file)
            .read_text(encoding="utf-8-sig")
            .splitlines()
            if line.strip()
        ]
        if (
            len(set(ids)) != len(ids)
            or not ids
            or (not set(ids).issubset(set(prompts.prompt_id)))
        ):
            raise ValueError(
                "Requested prompt identifiers must be unique, nonempty and present in the prompt file"
            )
        selected = prompts[prompts.prompt_id.isin(ids)]
    selected = selected.iloc[
        args.start : None if args.limit is None else args.start + args.limit
    ]
    if selected.empty:
        raise ValueError("No prompts selected")
    return (prompts, selected)


@contextmanager
def run_lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / ".run.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise RuntimeError(
            "This output directory is locked by another run; inspect the run before removing .run.lock"
        ) from error
    try:
        os.close(descriptor)
        yield
    finally:
        lock.unlink()


def load_results(path, prompts, metadata):
    if not path.exists():
        return {}
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    if "prompt_id" not in frame or frame.prompt_id.duplicated().any():
        raise ValueError("Existing results require unique prompt_id values")
    if not set(frame.prompt_id).issubset(set(prompts.prompt_id)):
        raise ValueError("Existing results belong to a different prompt file")
    for key in ["model", "model_id", "experiment_id", "provider"]:
        if key not in frame or not frame[key].eq(str(metadata[key])).all():
            raise ValueError(
                f"Existing results have a different {key}; use a new output directory"
            )
    original = prompts.set_index("prompt_id")
    for row in frame.to_dict("records"):
        for column in prompts.columns:
            if column not in row or str(row[column]) != str(
                original.loc[row["prompt_id"], column]
                if column != "prompt_id"
                else row["prompt_id"]
            ):
                raise ValueError(
                    f"Prompt contents differ for {row['prompt_id']}; use a new output directory"
                )
    return {row["prompt_id"]: row for row in frame.to_dict("records")}


def save_results(path, records):
    temporary = path.with_name("." + path.name + ".tmp")
    try:
        pd.DataFrame(list(records.values())).to_csv(
            temporary, index=False, encoding="utf-8-sig"
        )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def run_prompts(args, request, defaults, parameters):
    prompts, selected = read_prompts(args)
    metadata = {
        "experiment_id": args.experiment_id,
        "model_id": args.model_id,
        "model": args.model,
        **parameters,
    }
    if args.dry_run:
        print(
            json.dumps(
                {
                    "selected_prompts": len(selected),
                    "total_prompts": len(prompts),
                    "settings": metadata,
                },
                indent=2,
            )
        )
        return 0
    directory = project_path(args.run_dir)
    path = directory / "responses_merged.csv"
    with run_lock(directory):
        records = load_results(path, prompts, metadata)
        for number, row in enumerate(selected.to_dict("records"), 1):
            identifier = row["prompt_id"]
            if identifier in records and row_is_valid(records[identifier]):
                continue
            result = {**row, **defaults, **metadata, "status": "error", "error": ""}
            try:
                result.update(request(row["prompt"]))
                result["status"] = "ok"
                if not row_is_valid(result):
                    result["status"] = "error"
                    reason = (
                        clean_value(result.get("openai_incomplete_reason"))
                        or clean_value(result.get("ollama_done_reason"))
                        or clean_value(result.get("openai_status"))
                    )
                    result["error"] = f"Incomplete or empty response: {reason}"
            except Exception as error:
                result["error"] = (
                    f"Request failed ({type(error).__name__})"
                    if isinstance(error, requests.RequestException)
                    else str(error)
                )
            records[identifier] = result
            save_results(path, records)
            print(
                f"{number}/{len(selected)} {identifier}: {result['status']}", flush=True
            )
        incomplete = sum(
            (not row_is_valid(records[identifier]) for identifier in selected.prompt_id)
        )
    print(
        f"Selected prompts: {len(selected)}; incomplete: {incomplete}; saved to {path}"
    )
    return 1 if incomplete else 0
