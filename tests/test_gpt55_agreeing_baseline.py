"""Local baseline selection and saved-response completeness checks."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import csv,os,subprocess,sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from check_gpt55_agreeing_baseline import check
SUBMIT=Path(__file__).resolve().parents[1]/'run/submit_gpt55_agreeing_baseline.sh'

class BaselineSubmissionTests(unittest.TestCase):
    def test_dry_run_selects_first_and_remaining_without_credentials(self):
        with TemporaryDirectory() as directory:
            output=Path(directory)/'run'
            env=dict(os.environ,PYTHON_BIN=sys.executable,GPT_BASELINE_RUN=str(output))
            env.pop('OPENAI_API_KEY',None)
            for stage,count in [('first',75),('rest',675)]:
                result=subprocess.run(['bash',str(SUBMIT),stage,'--dry-run'],env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn(f'"selected_prompts": {count}',result.stdout)
            self.assertFalse(output.exists())

    def test_remaining_run_rejects_missing_first_responses(self):
        with TemporaryDirectory() as directory:
            env=dict(os.environ,PYTHON_BIN=sys.executable,GPT_BASELINE_RUN=str(Path(directory)/'run'))
            env.pop('OPENAI_API_KEY',None)
            result=subprocess.run(['bash',str(SUBMIT),'rest'],env=env,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Check failed:',result.stderr)

class BaselineCompletenessTests(unittest.TestCase):
    def fixture(self,root):
        prompts=[dict(prompt_id=str(i),frame_id=f'F{i%5+1}',prompt=f'prompt {i}',source_item_id=str(i//5)) for i in range(750)]
        rows=[dict(**p,model='gpt-5.5',reasoning_effort='none',max_output_tokens='128',status='ok',openai_status='completed',response='translation') for p in prompts[:75]]
        source=root/'prompts.csv';run=root/'run';run.mkdir()
        self.write(source,prompts);self.write(run/'responses_merged.csv',rows)
        return source,run,rows
    def write(self,path,rows):
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    def test_complete_first_and_duplicate_rejected(self):
        with TemporaryDirectory() as directory:
            source,run,rows=self.fixture(Path(directory));check('first',run,source)
            rows[1]['prompt_id']=rows[0]['prompt_id'];self.write(run/'responses_merged.csv',rows)
            with self.assertRaisesRegex(ValueError,'Duplicate'):check('first',run,source)
    def test_incomplete_response_rejected(self):
        with TemporaryDirectory() as directory:
            source,run,rows=self.fixture(Path(directory));rows[0]['openai_status']='incomplete';self.write(run/'responses_merged.csv',rows)
            with self.assertRaisesRegex(ValueError,'Incomplete'):check('first',run,source)
    def test_changed_prompt_rejected(self):
        with TemporaryDirectory() as directory:
            source,run,rows=self.fixture(Path(directory));rows[0]['prompt']='changed';self.write(run/'responses_merged.csv',rows)
            with self.assertRaisesRegex(ValueError,'Changed prompt'):check('first',run,source)

if __name__=='__main__':unittest.main()
