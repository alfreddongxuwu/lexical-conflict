"""CPU end-to-end coding, scoring and reporting with constructed responses."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import csv
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from make_conventional_prompts import ConventionalBaseline

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class ConventionalPipelineTests(unittest.TestCase):
    def run_script(self, name, *args, fails=None):
        result = subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)],
                                capture_output=True, text=True)
        if fails:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn(fails, result.stderr)
        else:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_raw_text_labels_nulls_reports_and_no_overwrite(self):
        # Constructed responses; the inventory supplies real accepted-form identities.
        normal = dict(prompt_id='normal_x', baseline_type='normal_lexical', source_item_id='fruit_001',
            source_word_zh='苹果', standard_en='apple', source_category='fruit', context_category='fruit',
            source_freq_band='high', source_sentence_zh='这些苹果已经熟到可以吃了。',
            literal_expected_en='These apple are ripe enough to eat.',
            prompt='Task: Translate Mandarin to English.\nTranslate: 这些苹果已经熟到可以吃了。')
        frames = [dict(frame_id=f'F{i}', frame_name=f'frame{i}',
                       frame_text_template=f'Frame {i}: {{source_word_zh}} means {{prompted_en}}.') for i in range(1, 6)]
        design = ConventionalBaseline([normal], frames)
        settings = dict(status='ok', model='model', model_id='model', temperature='0.0', seed='2026',
                        num_ctx='4096', num_predict='128', think='auto', think_resolved='unset')
        baseline = [{**normal, **settings, 'response': 'These apples are ripe enough to eat.'}]
        new = [{**r, **settings, 'response': '  These apples are ripe enough to eat.  '} for r in design.build()]
        new[-1]['response'] = ''
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for group, records in [('baseline', baseline), ('conventional_meaning', new)]:
                raw = root / group / 'raw.csv'
                coded = root / group / 'responses_baseline_autocoded.csv'
                write(raw, records)
                before = raw.read_bytes()
                self.run_script('code_english_baseline.py', raw, coded)
                self.assertEqual(raw.read_bytes(), before)
                self.run_script('score_translations.py', coded, root / 'scores' / group / 'model', '--no-comet')
                self.run_script('code_english_baseline.py', raw, coded, fails='Output already exists')
            self.run_script('compare_translation_scores.py', root / 'scores', root / 'reports')
            html = (root / 'reports/paired_quality_comparisons.html').read_text()
            self.assertIn('expected_word', html)
            self.assertIn('conventional_meaning/F2', html)
            self.assertIn('settings_matched', html)
            self.run_script('compare_translation_scores.py', root / 'scores', root / 'reports', fails='Output already exists')
            scored = root / 'scores/conventional_meaning/model/literal_expected_en.csv'
            with scored.open(encoding='utf-8-sig', newline='') as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]['response'], new[0]['response'])
            self.assertEqual(rows[-1]['baseline_label'], 'FAILED')
            self.assertEqual([rows[-1][k] for k in ['bleu', 'chrf', 'comet']], ['', '', ''])


if __name__ == '__main__':
    unittest.main()
