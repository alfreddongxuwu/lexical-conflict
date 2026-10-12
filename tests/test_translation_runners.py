"""Verbatim translation output and local generation without a scheduler."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import contextlib,csv,io,os,subprocess,sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import run_ollama_translation as ollama
from run_openai_translation import extract_text

class RunnerTests(unittest.TestCase):
    def test_openai_text_preserved(self):
        self.assertEqual(extract_text({'output_text':'  蝴蝶\n'}),'  蝴蝶\n')
        self.assertEqual(extract_text({'output':[{'type':'message','content':[{'type':'output_text','text':'  蝴蝶\n'}]}]}),'  蝴蝶\n')

    def test_ollama_text_and_prompt_preserved(self):
        with patch('run_ollama_translation.requests.post') as post:
            post.return_value.status_code=200
            post.return_value.json.return_value={'response':'  蝴蝶\n','done_reason':'stop'}
            result=ollama.call_ollama('Translate exactly.','qwen3:8b',0,2026,4096,128,'auto',30)
            self.assertEqual(result['response'],'  蝴蝶\n')
            self.assertEqual(post.call_args.kwargs['json']['prompt'],'Translate exactly.')
            self.assertIs(post.call_args.kwargs['json']['think'],False)

    def test_local_dry_run_makes_no_requests_or_outputs(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);prompts=root/'prompts.csv'
            prompts.write_text('prompt_id,prompt\np1,Translate.\n')
            args=['--prompts',str(prompts),'--run-dir',str(root/'output'),'--model','qwen3:8b','--model-id','qwen3_8b','--experiment-id','position_BE','--dry-run']
            with patch.object(ollama,'call_ollama') as request,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ollama.main(args),0)
            request.assert_not_called();self.assertFalse((root/'output').exists())

    def test_local_run_preserves_raw_response_and_resumes(self):
        with TemporaryDirectory() as directory:
            root=Path(directory);prompts=root/'prompts.csv'
            prompts.write_text('prompt_id,prompt\np1,Translate.\n')
            args=['--prompts',str(prompts),'--run-dir',str(root/'output'),'--model','qwen3:8b','--model-id','qwen3_8b','--experiment-id','position_BE']
            result=dict(response='  apple\n',thinking='',think_resolved='false',done_reason='stop',prompt_eval_count=3,eval_count=1)
            with patch.object(ollama,'call_ollama',return_value=result.copy()) as request,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ollama.main(args),0)
                self.assertEqual(request.call_count,1)
            with (root/'output/responses_merged.csv').open(encoding='utf-8-sig',newline='') as f:
                rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]['response'],'  apple\n')
            self.assertNotIn('job_id',rows[0])
            with patch.object(ollama,'call_ollama') as request,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ollama.main(args),0)
            request.assert_not_called()

if __name__=='__main__':unittest.main()
