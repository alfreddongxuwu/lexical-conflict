import argparse
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import sys
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lexconflict import run_ollama, run_openai
from lexconflict.local_run import run_lock


class LocalRunTests(unittest.TestCase):

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.prompts = self.root / "prompts.csv"
        self.output = self.root / "run"
        pd.DataFrame(
            {"prompt_id": ["p1", "p2", "p3"], "prompt": ["one", "two", "three"]}
        ).to_csv(self.prompts, index=False)
        self.arguments = [
            "--prompts",
            str(self.prompts),
            "--run-dir",
            str(self.output),
            "--model-id",
            "qwen3_8b",
            "--experiment-id",
            "main",
        ]

    def invoke(self, function, arguments):
        with redirect_stdout(io.StringIO()):
            return function(arguments)

    def ollama_result(self, complete=True):
        return {
            "response": "apple",
            "thinking": "",
            "think_resolved": "false",
            "done_reason": "stop" if complete else "length",
            "prompt_eval_count": 10,
            "eval_count": 1,
        }

    def test_full_run_is_local_and_unique(self):
        with patch.object(
            run_ollama, "call_ollama", return_value=self.ollama_result()
        ) as request:
            self.assertEqual(
                self.invoke(run_ollama.main, self.arguments + ["--model", "qwen3:8b"]),
                0,
            )
        frame = pd.read_csv(self.output / "responses_merged.csv")
        self.assertEqual(request.call_count, 3)
        self.assertEqual(frame.prompt_id.tolist(), ["p1", "p2", "p3"])
        self.assertTrue(frame.status.eq("ok").all())
        self.assertTrue(frame.num_predict.eq(128).all())
        self.assertEqual(set(frame.provider), {"ollama"})
        self.assertFalse((self.output / ".run.lock").exists())

    def test_resume_retries_only_incomplete_response(self):
        arguments = self.arguments + ["--model", "qwen3:8b"]
        with patch.object(
            run_ollama,
            "call_ollama",
            side_effect=[
                self.ollama_result(),
                self.ollama_result(False),
                self.ollama_result(),
            ],
        ):
            self.assertEqual(self.invoke(run_ollama.main, arguments), 1)
        with patch.object(
            run_ollama, "call_ollama", return_value=self.ollama_result()
        ) as request:
            self.assertEqual(
                self.invoke(run_ollama.main, arguments + ["--num-predict", "1048"]), 0
            )
            self.assertEqual(request.call_count, 1)
        frame = pd.read_csv(self.output / "responses_merged.csv")
        self.assertEqual(len(frame), 3)
        self.assertFalse(frame.prompt_id.duplicated().any())
        self.assertEqual(frame.num_predict.tolist(), [128, 1048, 128])
        with patch.object(run_ollama, "call_ollama") as request:
            self.assertEqual(self.invoke(run_ollama.main, arguments), 0)
            request.assert_not_called()

    def test_changed_prompt_is_rejected_before_request(self):
        arguments = self.arguments + ["--model", "qwen3:8b", "--limit", "1"]
        with patch.object(run_ollama, "call_ollama", return_value=self.ollama_result()):
            self.invoke(run_ollama.main, arguments)
        frame = pd.read_csv(self.prompts)
        frame.loc[0, "prompt"] = "changed"
        frame.to_csv(self.prompts, index=False)
        with patch.object(run_ollama, "call_ollama") as request, self.assertRaisesRegex(
            ValueError, "Prompt contents differ"
        ):
            self.invoke(run_ollama.main, arguments)
        request.assert_not_called()
        self.assertFalse((self.output / ".run.lock").exists())

    def test_changed_model_is_rejected(self):
        with patch.object(run_ollama, "call_ollama", return_value=self.ollama_result()):
            self.invoke(
                run_ollama.main,
                self.arguments + ["--model", "qwen3:8b", "--limit", "1"],
            )
        with self.assertRaisesRegex(ValueError, "different model"):
            self.invoke(run_ollama.main, self.arguments + ["--model", "qwen3:32b"])

    def test_dry_run_needs_no_provider_and_writes_nothing(self):
        with patch.object(run_openai, "call_openai") as request:
            self.assertEqual(
                self.invoke(
                    run_openai.main,
                    self.arguments + ["--dry-run", "--start", "1", "--limit", "1"],
                ),
                0,
            )
            request.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_selection_and_identifier_validation(self):
        ids = self.root / "ids.txt"
        ids.write_text("p3\n")
        with patch.object(
            run_ollama, "call_ollama", return_value=self.ollama_result()
        ) as request:
            self.invoke(
                run_ollama.main,
                self.arguments + ["--model", "qwen3:8b", "--prompt-ids-file", str(ids)],
            )
        self.assertEqual(request.call_count, 1)
        self.assertEqual(
            pd.read_csv(self.output / "responses_merged.csv").prompt_id.tolist(), ["p3"]
        )
        ids.write_text("missing\n")
        with self.assertRaises(ValueError):
            self.invoke(
                run_ollama.main,
                self.arguments
                + ["--model", "qwen3:8b", "--prompt-ids-file", str(ids), "--dry-run"],
            )

    def test_invalid_bounds_and_duplicates_are_rejected(self):
        for extra in [["--start", "-1"], ["--limit", "0"], ["--start", "99"]]:
            with self.assertRaises(ValueError):
                self.invoke(
                    run_ollama.main,
                    self.arguments + ["--model", "qwen3:8b", "--dry-run"] + extra,
                )
        pd.DataFrame({"prompt_id": ["p1", "p1"], "prompt": ["a", "b"]}).to_csv(
            self.prompts, index=False
        )
        with self.assertRaisesRegex(ValueError, "unique"):
            self.invoke(
                run_ollama.main, self.arguments + ["--model", "qwen3:8b", "--dry-run"]
            )

    def test_run_lock_preserves_existing_owner(self):
        with run_lock(self.output):
            with self.assertRaises(RuntimeError):
                with run_lock(self.output):
                    pass
            self.assertTrue((self.output / ".run.lock").exists())
        self.assertFalse((self.output / ".run.lock").exists())

    def test_request_exception_details_are_not_saved(self):
        error = run_ollama.requests.ConnectionError("sensitive-request-detail")
        with patch.object(run_ollama, "call_ollama", side_effect=error):
            self.assertEqual(
                self.invoke(
                    run_ollama.main,
                    self.arguments + ["--model", "qwen3:8b", "--limit", "1"],
                ),
                1,
            )
        text = (self.output / "responses_merged.csv").read_text()
        self.assertNotIn("sensitive-request-detail", text)
        self.assertIn("ConnectionError", text)

    def test_openai_payload_matches_standard_configuration(self):
        args = run_openai.parse_args(self.arguments)
        payload = run_openai.build_payload(args, "translate")
        self.assertEqual(payload["max_output_tokens"], 128)
        self.assertEqual(payload["reasoning"], {"effort": "none"})
        self.assertEqual(payload["text"], {"verbosity": "low"})
        self.assertFalse(payload["store"])
        self.assertNotIn("temperature", payload)

    def test_openai_incomplete_then_recovery(self):
        incomplete = {
            "response": "",
            "openai_status": "incomplete",
            "openai_incomplete_reason": "max_output_tokens",
        }
        complete = {
            "response": "apple",
            "openai_status": "completed",
            "openai_incomplete_reason": "",
        }
        with patch.object(run_openai, "call_openai", return_value=incomplete):
            self.assertEqual(
                self.invoke(run_openai.main, self.arguments + ["--limit", "1"]), 1
            )
        with patch.object(run_openai, "call_openai", return_value=complete):
            self.assertEqual(
                self.invoke(
                    run_openai.main,
                    self.arguments + ["--limit", "1", "--max-output-tokens", "1048"],
                ),
                0,
            )
        frame = pd.read_csv(self.output / "responses_merged.csv")
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.iloc[0].max_output_tokens, 1048)
        self.assertNotIn("openai_response_id", frame.columns)

    def test_ollama_http_payload(self):
        response = Mock(status_code=200)
        response.json.return_value = {"response": "apple", "done_reason": "stop"}
        with patch.object(
            run_ollama.requests, "post", return_value=response
        ) as request:
            run_ollama.call_ollama(
                "translate", "qwen3:8b", 0, 2026, 4096, 128, "auto", 300
            )
        payload = request.call_args.kwargs["json"]
        self.assertFalse(payload["think"])
        self.assertEqual(
            payload["options"],
            {"temperature": 0, "seed": 2026, "num_ctx": 4096, "num_predict": 128},
        )

    def test_openai_http_retry_and_text_extraction(self):
        args = run_openai.parse_args(self.arguments)
        retry = Mock(status_code=429, headers={"retry-after": "0"})
        success = Mock(status_code=200)
        success.json.return_value = {
            "id": "response-identifier",
            "status": "completed",
            "output": [{"content": [{"type": "output_text", "text": "apple"}]}],
        }
        session = Mock()
        session.post.side_effect = [retry, success]
        with patch.object(run_openai, "get_headers", return_value={}), patch.object(
            run_openai.time, "sleep"
        ):
            with redirect_stdout(io.StringIO()):
                result = run_openai.call_openai(session, args, "translate")
        self.assertEqual(session.post.call_count, 2)
        self.assertEqual(result["response"], "apple")
        self.assertNotIn("openai_response_id", result)


if __name__ == "__main__":
    unittest.main()
