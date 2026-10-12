"""Report individual scores and paired quality comparisons separately.

Usage: analysis.venv/bin/python compare_translation_scores.py SCORES_ROOT OUTPUT_DIR
SCORES_ROOT contains <experiment>/<model>/literal_{pk,ck,expected}_{en,zh}.csv
from score_translations.py. Baseline scores are required for each included model.
Writes individual_scores.html and paired_quality_comparisons.html, without
overwriting existing reports. Means describe saved sentence scores, not corpus
BLEU/chrF. No statistical significance tests are performed.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from html import escape
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from paths import REPORT_THEME
from result_validity import row_is_valid

METRICS = ("bleu", "chrf", "comet")
POSITION_CELLS = ("position_B", "position_E", "position_BM", "position_BE", "position_ME",
                  "position_BME", "reiteration_2", "reiteration_3")
# conventional_meaning stays last: main() reads GROUPS[1:-1] as conflict experiments.
GROUPS = ("baseline", "main", "exp2", "may_mean", "reiteration", "thinking_on",
          *POSITION_CELLS, "conventional_meaning")
# Rule position x reiteration: same copy count, copies in different slots.
SAME_COUNT_PAIRS = (("reiteration_2", "position_BM"), ("reiteration_2", "position_BE"),
                    ("reiteration_2", "position_ME"), ("reiteration_3", "position_BME"))
MATCH = ("source_item_id", "target_item_id",
         "source_freq_band", "target_freq_band", "reference", "baseline_label")


@dataclass
class ScoredRun:
    experiment: str
    model: str
    reference: str
    rows: pd.DataFrame


def _direction(rows: pd.DataFrame) -> tuple[str, str]:
    sources = [name for name in ("source_sentence_zh", "source_sentence_en") if name in rows]
    if len(sources) != 1:
        raise ValueError("Expected exactly one source-language column")
    source = sources[0]
    direction = "English-Mandarin" if source.endswith("_en") else "Mandarin-English"
    if "direction" in rows and not rows.direction.eq(direction).all():
        raise ValueError("Direction differs from source-language column")
    return direction, source


def _read(path: Path, reference: str) -> pd.DataFrame:
    rows = pd.read_csv(path, dtype=str, keep_default_na=False)
    direction, source = _direction(rows)
    expected_suffix = "_zh" if direction == "English-Mandarin" else "_en"
    if not reference.endswith(expected_suffix):
        raise ValueError("Reference language differs from translation direction")
    rows["direction"] = direction
    required = {"prompt_id", source, "response", reference, *METRICS}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"Missing columns {sorted(missing)}: {path}")
    if rows.empty or rows.prompt_id.eq("").any() or rows.prompt_id.duplicated().any():
        raise ValueError(f"Empty input or empty/duplicate prompt IDs: {path}")
    rows["reference"] = rows[reference]
    if rows[[source, "reference"]].apply(lambda c: c.str.strip().eq("")).any().any():
        raise ValueError(f"Blank source or reference: {path}")
    rows["empty"] = rows.response.str.strip().eq("")
    rows["failed"] = ~rows.apply(row_is_valid, axis=1)
    for metric in METRICS:
        rows[metric] = pd.to_numeric(rows[metric].replace("", np.nan), errors="raise")
        if np.isinf(rows[metric]).any():
            raise ValueError(f"Infinite {metric}: {path}")
        if rows.loc[rows["empty"], metric].notna().any():
            raise ValueError(f"Empty hypothesis has a score: {path}")
    return rows


def _baseline_labels(rows: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    direction, source = _direction(rows)
    if _direction(baseline)[0] != direction:
        raise ValueError("Baseline direction differs from experimental direction")
    if "baseline_type" in rows and rows.baseline_type.eq("conventional_meaning").all():
        rows = rows.rename(columns={"baseline_label": "conventional_label"})
    keys = ["source_item_id", "context_category"]
    columns = keys + ["baseline_label", source, "reference"]
    result = rows.merge(baseline[columns], on=keys, how="left",
                        suffixes=("", "_baseline"), validate="many_to_one")
    if result.baseline_label.isna().any():
        raise ValueError("Missing baseline match")
    if result[source].ne(result[f"{source}_baseline"]).any():
        raise ValueError("Baseline source differs from experimental source")
    # Opposite references intentionally differ from the baseline reference.
    primary = "literal_pk_zh" if direction == "English-Mandarin" else "literal_pk_en"
    if primary in result and result[primary].ne(result.reference_baseline).any():
        raise ValueError("Primary reference differs from baseline reference")
    expected = "literal_expected_zh" if direction == "English-Mandarin" else "literal_expected_en"
    if expected in result and result[expected].ne(result.reference_baseline).any():
        raise ValueError("Conventional reference differs from baseline reference")
    return result


def _strata(rows: pd.DataFrame):
    yield "all", rows
    for label, subset in rows.groupby("baseline_label", sort=True):
        yield label, subset


def _individual(run: ScoredRun) -> list[dict]:
    records = []
    subsets = [("all", "all", run.rows)]
    subsets.extend((context, frame, subset) for (context, frame), subset
                   in run.rows.groupby(["context_type", "frame_id"], sort=True))
    for context, frame, subset in subsets:
        for label, rows in _strata(subset):
            metrics = list(METRICS)
            lexical = "conventional_label" if run.experiment == "conventional_meaning" else "baseline_label"
            if run.experiment in {"baseline", "conventional_meaning"}:
                rows = rows.copy()
                rows["expected_word"] = rows[lexical].map({"EXPECTED": 1.0, "OTHER": 0.0})
                metrics.append("expected_word")
            for metric in metrics:
                scores = rows[metric].dropna()
                records.append(dict(direction=_direction(rows)[0], experiment=run.experiment, model=run.model,
                    reference=run.reference, context=context, frame=frame,
                    baseline_label=label, metric=metric, rows=len(rows),
                    empty=int(rows["empty"].sum()), failed=int(rows.failed.sum()),
                    valid=len(rows) - int(rows.failed.sum()),
                    scored=len(scores), mean=scores.mean()))
    return records


def _paired(left: ScoredRun, right: ScoredRun, keys: list[str],
            left_name: str, right_name: str) -> list[dict]:
    if (left.model, left.reference) != (right.model, right.reference):
        raise ValueError("Pairing requires the same model and reference type")
    direction, source = _direction(left.rows)
    if _direction(right.rows)[0] != direction:
        raise ValueError("Pairing requires the same translation direction")
    joined = left.rows.merge(right.rows, on=keys, how="outer",
                             suffixes=("_left", "_right"),
                             validate="one_to_one", indicator=True)
    both = joined["_merge"].eq("both")
    for column in (*MATCH, source):
        if joined.loc[both, f"{column}_left"].ne(joined.loc[both, f"{column}_right"]).any():
            raise ValueError(f"Paired {column} mismatch: {left_name} / {right_name}")
    joined["baseline_label"] = joined.baseline_label_left.combine_first(joined.baseline_label_right)
    records = []
    group_keys = ["context_type"] + (["frame_id"] if "frame_id" in keys else [])
    for identity, subset in joined.groupby(group_keys, sort=True):
        identity = identity if isinstance(identity, tuple) else (identity,)
        for label, rows in _strata(subset):
            for metric in METRICS:
                available = rows[[f"{metric}_left", f"{metric}_right"]].dropna()
                delta = available[f"{metric}_right"] - available[f"{metric}_left"]
                records.append(dict(direction=direction, left=left_name, right=right_name, model=left.model,
                    reference=left.reference, context=identity[0],
                    frame=identity[1] if len(identity) == 2 else "paired frames",
                    baseline_label=label, metric=metric,
                    left_rows=int(rows["_merge"].ne("right_only").sum()),
                    right_rows=int(rows["_merge"].ne("left_only").sum()),
                    matched=int(rows["_merge"].eq("both").sum()),
                    scored_pairs=len(available),
                    left_only=int(rows["_merge"].eq("left_only").sum()),
                    right_only=int(rows["_merge"].eq("right_only").sum()),
                    left_empty=int(rows.empty_left.fillna(False).sum()),
                    right_empty=int(rows.empty_right.fillna(False).sum()),
                    left_failed=int(rows.failed_left.fillna(False).sum()),
                    right_failed=int(rows.failed_right.fillna(False).sum()),
                    left_missing_score=int((rows["_merge"].ne("right_only") & rows[f"{metric}_left"].isna()).sum()),
                    right_missing_score=int((rows["_merge"].ne("left_only") & rows[f"{metric}_right"].isna()).sum()),
                    left_mean=available[f"{metric}_left"].mean(),
                    right_mean=available[f"{metric}_right"].mean(),
                    mean_difference=delta.mean(),
                    higher=int((delta > 0).sum()), tied=int((delta == 0).sum()),
                    lower=int((delta < 0).sum())))
    return records



def _conventional_pairs(left: ScoredRun, right: ScoredRun,
                        left_name: str, right_name: str) -> list[dict]:
    """Pair one agreeing response per item with controls, preserving reused items."""
    if left.model != right.model or _direction(left.rows) != _direction(right.rows):
        raise ValueError("Conventional pairing requires the same model and direction")
    source = _direction(left.rows)[1]
    keys = ["source_item_id"]
    if right.rows.frame_id.nunique() != 1 or right.rows.source_item_id.duplicated().any():
        raise ValueError("Conventional comparison requires one frame at a time")
    if left.experiment in {"baseline", "conventional_meaning"} and left.rows.source_item_id.duplicated().any():
        raise ValueError("Duplicate control source item")
    if left.experiment in {"main", "exp2"}:
        if left.rows.duplicated(["mapping_id", "frame_id"]).any():
            raise ValueError("Duplicate conflict mapping-frame")
        if "literal_ck" in left.reference:
            raise ValueError("Conventional comparison requires the ordinary reference")
    joined = left.rows.merge(right.rows, on=keys, how="outer", suffixes=("_left", "_right"),
                             validate="many_to_one", indicator=True)
    both = joined["_merge"].eq("both")
    for column in (source, "reference", "source_freq_band", "context_category", "baseline_label"):
        if joined.loc[both, f"{column}_left"].ne(joined.loc[both, f"{column}_right"]).any():
            raise ValueError(f"Conventional paired {column} mismatch")
    if left.experiment in {"main", "exp2"} and joined.loc[both, "frame_id_left"].ne(joined.loc[both, "frame_id_right"]).any():
        raise ValueError("Conventional paired frame mismatch")
    joined["baseline_label"] = joined.baseline_label_left.combine_first(joined.baseline_label_right)
    settings = ("model", "temperature", "seed", "num_ctx", "num_predict", "think", "think_resolved")
    if "reasoning_effort_left" in joined:
        settings = ("model", "temperature", "reasoning_effort", "text_verbosity", "max_output_tokens")
    settings_known = all(f"{key}_{side}" in joined for key in settings for side in ("left", "right"))
    joined["settings_equal"] = both.copy()
    if settings_known:
        for key in settings:
            joined["settings_equal"] &= joined[f"{key}_left"].astype(str).str.lower().eq(joined[f"{key}_right"].astype(str).str.lower())
    else:
        joined["settings_equal"] = False
    # Lexical labels describe the same conventional form in both baseline arms.
    lexical = left.experiment in {"baseline", "conventional_meaning"}
    if lexical:
        for side, run in (("left", left), ("right", right)):
            label = "conventional_label" if run.experiment == "conventional_meaning" else "baseline_label"
            labels = joined[f"{label}_{side}"] if f"{label}_{side}" in joined else joined[label]
            joined[f"expected_word_{side}"] = labels.map({"EXPECTED": 1.0, "OTHER": 0.0})
    records = []
    for label, rows in _strata(joined):
        for metric in (*METRICS, *(("expected_word",) if lexical else ())):
            available = rows.dropna(subset=[f"{metric}_left", f"{metric}_right"]).copy()
            available["delta"] = available[f"{metric}_right"] - available[f"{metric}_left"]
            # Equal source-item weight even when conflict mappings reuse the baseline.
            item_means = available.groupby("source_item_id")[[f"{metric}_left", f"{metric}_right", "delta"]].mean()
            deltas = item_means.delta.to_numpy()
            low, high = np.nan, np.nan
            if lexical and len(deltas):
                rng = np.random.default_rng(2026)
                means = rng.choice(deltas, size=(2000, len(deltas)), replace=True).mean(axis=1)
                low, high = np.quantile(means, [.025, .975])
            records.append(dict(direction=_direction(right.rows)[0], left=left_name, right=right_name,
                model=right.model, reference="ordinary meaning", context="conventional context",
                frame=str(right.rows.frame_id.iloc[0]), baseline_label=label, metric=metric,
                left_rows=int(rows["_merge"].ne("right_only").sum()),
                right_rows=rows.loc[rows["_merge"].ne("left_only"), "source_item_id"].nunique(),
                matched=int(rows["_merge"].eq("both").sum()), scored_pairs=len(available),
                source_items=len(item_means), left_only=int(rows["_merge"].eq("left_only").sum()),
                right_only=int(rows["_merge"].eq("right_only").sum()),
                left_empty=int(rows.empty_left.fillna(False).sum()),
                right_empty=rows.loc[rows.empty_right.fillna(False).astype(bool), "source_item_id"].nunique(),
                left_failed=int(rows.failed_left.fillna(False).sum()),
                right_failed=rows.loc[rows.failed_right.fillna(False).astype(bool), "source_item_id"].nunique(),
                settings_matched=int(rows.settings_equal.sum()),
                settings_different=int((rows["_merge"].eq("both") & ~rows.settings_equal).sum()) if settings_known else 0,
                settings_unknown=int(rows["_merge"].eq("both").sum()) if not settings_known else 0,
                left_mean=item_means[f"{metric}_left"].mean(), right_mean=item_means[f"{metric}_right"].mean(),
                mean_difference=item_means.delta.mean(), ci_low=low, ci_high=high,
                higher=int((deltas > 0).sum()), tied=int((deltas == 0).sum()), lower=int((deltas < 0).sum())))
    return records

def _write(path: Path, title: str, description: str, records: list[dict]) -> None:
    frame = pd.DataFrame(records)
    if "reference" in frame:
        frame["reference"] = frame["reference"].replace({
            "literal_pk_en": "Conventional", "literal_expected_en": "Conventional",
            "literal_pk_zh": "Conventional", "literal_expected_zh": "Conventional",
            "literal_ck_en": "Use Lexicon", "literal_ck_zh": "Use Lexicon",
            "ordinary meaning": "Conventional",
        })
    if "mean_difference" in frame:
        first = ["direction", "left", "right", "model", "reference", "context", "frame",
                 "baseline_label", "metric", "mean_difference", "scored_pairs",
                 "left_mean", "right_mean", "higher", "tied", "lower"]
        first += [column for column in ("settings_different", "settings_unknown", "source_items", "ci_low", "ci_high") if column in frame]
        frame = frame[first + [column for column in frame if column not in first]]
    table = frame.to_html(index=False, na_rep="—", float_format=lambda v: f"{v:.6f}")
    with path.open("x", encoding="utf-8") as handle:
        handle.write(f"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>{escape(title)}</title><style>
body {{font:15px system-ui;margin:2rem;color:var(--report-ink,#202428)}} p {{max-width:90em;line-height:1.5}}
table {{border-collapse:collapse;font-size:13px}} th,td {{padding:.45rem;border-bottom:1px solid var(--report-border,#ddd);text-align:left}}
th {{position:sticky;top:0;background:var(--report-soft,#edf1f5)}} input {{padding:.5rem;width:32rem;max-width:90%}}
{REPORT_THEME.read_text(encoding="utf-8")}</style><h1>{escape(title)}</h1><p>{escape(description)}</p>
<p>Conventional translates the source word conventionally; Use Lexicon applies
the prompt's definition. Both preserve the remaining sentence, including intentional
nonsense. No-rule baselines and F1 require Conventional; F2–F5 require Use Lexicon
for asserted definitions. Tentative may_mean definitions retain both readings.
Paired differences hold the reference fixed and do not measure instruction adherence.
BLEU and chrF are divided by 100; COMET retains its native scale.
English targets use chrF++ and default BLEU tokenization; Mandarin targets use
character-only chrF and Chinese BLEU tokenization. Directions are reported separately.
Blank metrics are excluded from means. Failed means the saved response fails the existing
completion check (including empty responses); nonempty outputs remain scored as saved.
Baseline EXPECTED means the expected word was found, not a human quality judgment.
The all and baseline-label rows overlap; do not add their counts together.
No significance tests are included. Conventional-baseline contrasts give each source
item equal weight; higher/tied/lower counts there count source items. For comparisons
between baseline conditions, intervals resample source items 2,000 times (seed 2026).
Conflict contrasts have no intervals because targets are also reused. expected_word
is the accepted conventional-word rate among jointly valid responses, on a 0–1 scale.
Settings counts compare recorded generation arguments only, not weight identity or
unrecorded defaults. Different or unknown settings make a contrast descriptive only;
the report retains these rows rather than silently selecting a subset.</p>
<label>Filter rows <input id="filter" placeholder="Space-separated search terms"></label>
{table}<script>
document.querySelector('#filter').addEventListener('input', function() {{
 const terms=this.value.toLowerCase().trim().split(/\\s+/);
 document.querySelectorAll('tbody tr').forEach(row => {{
  const text=row.textContent.toLowerCase(); row.hidden=!terms.every(term=>text.includes(term));
 }});
}});</script></html>""")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scores_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    outputs = [args.output_dir / name for name in
               ("individual_scores.html", "paired_quality_comparisons.html")]
    for path in outputs:
        if path.exists():
            parser.error(f"Output already exists: {path}")
    unknown = {p.name for p in args.scores_root.iterdir() if p.is_dir()} - set(GROUPS) - {"backups"}
    if unknown:
        parser.error(f"Unknown experimental groups: {sorted(unknown)}")
    models = sorted({p.name for group in GROUPS for p in (args.scores_root / group).glob("*") if p.is_dir()})
    if not models:
        parser.error("No scored models found")
    individual, paired = [], []
    languages = {path.stem.removeprefix("literal_expected_")
                 for model in models
                 for path in (args.scores_root / "baseline" / model).glob("literal_expected_*.csv")}
    if len(languages) != 1 or not languages <= {"en", "zh"}:
        parser.error("Use a separate scores root for each direction, with matching baseline scores")
    language = languages.pop()
    for model in models:
        baseline_reference = f"literal_expected_{language}"
        baseline = _read(args.scores_root / "baseline" / model / f"{baseline_reference}.csv", baseline_reference)
        baseline["context_type"] = baseline.baseline_type
        baseline["frame_id"] = "none"
        individual.extend(_individual(ScoredRun("baseline", model, baseline_reference, baseline)))
        conventional = None
        conventional_path = args.scores_root / "conventional_meaning" / model / f"{baseline_reference}.csv"
        if conventional_path.exists():
            if language != "en":
                raise ValueError("Conventional baseline currently supports Mandarin-English only")
            rows = _baseline_labels(_read(conventional_path, baseline_reference), baseline)
            if not rows.baseline_type.eq("conventional_meaning").all() or "conventional_label" not in rows:
                raise ValueError("Expected autocoded conventional baseline rows")
            if rows.duplicated(["source_item_id", "frame_id"]).any():
                raise ValueError("Duplicate conventional word-frame")
            rows["context_type"] = "conventional_meaning"
            conventional = ScoredRun("conventional_meaning", model, baseline_reference, rows)
            individual.extend(_individual(conventional))
            for frame, subset in rows.groupby("frame_id"):
                right = ScoredRun(conventional.experiment, model, baseline_reference, subset)
                normal = baseline[baseline.baseline_type.eq("normal_lexical")]
                paired.extend(_conventional_pairs(ScoredRun("baseline", model, baseline_reference, normal),
                    right, "normal_lexical", f"conventional_meaning/{frame}"))
                if frame != "F2" and rows.frame_id.eq("F2").any():
                    paired.extend(_conventional_pairs(ScoredRun(conventional.experiment, model, baseline_reference,
                        rows[rows.frame_id.eq("F2")]), right, "conventional_meaning/F2", f"conventional_meaning/{frame}"))
        for reference in (f"literal_pk_{language}", f"literal_ck_{language}"):
            runs = {}
            for group in GROUPS[1:-1]:
                directory = args.scores_root / group / model
                if not directory.exists():
                    continue
                rows = _baseline_labels(_read(directory / f"{reference}.csv", reference), baseline)
                run = runs[group] = ScoredRun(group, model, reference, rows)
                individual.extend(_individual(run))
                if conventional is not None and group in {"main", "exp2"} and reference == "literal_pk_en":
                    controls = rows[rows.context_type.ne("CK_context")]
                    for frame, subset in conventional.rows.groupby("frame_id"):
                        paired.extend(_conventional_pairs(
                            ScoredRun(group, model, reference, controls[controls.frame_id.eq(frame)]),
                            ScoredRun(conventional.experiment, model, baseline_reference, subset),
                            f"{group}/{frame}", f"conventional_meaning/{frame}"))
                for a, b in combinations(sorted(rows.frame_id.unique()), 2):
                    left = ScoredRun(group, model, reference, rows[rows.frame_id.eq(a)])
                    right = ScoredRun(group, model, reference, rows[rows.frame_id.eq(b)])
                    paired.extend(_paired(left, right, ["mapping_id", "context_type"], f"{group}/{a}", f"{group}/{b}"))
            for group in ("may_mean", "reiteration", "thinking_on", *POSITION_CELLS):
                if group in runs:
                    if "main" not in runs:
                        raise ValueError(f"Missing main scores for follow-up: {group}/{model}")
                    paired.extend(_paired(runs["main"], runs[group],
                        ["mapping_id", "context_type", "frame_id"], "main", group))
            for left, right in SAME_COUNT_PAIRS:
                if left in runs and right in runs:
                    paired.extend(_paired(runs[left], runs[right],
                        ["mapping_id", "context_type", "frame_id"], left, right))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write(outputs[0], "Individual scores", "Means of saved sentence scores, separately by experimental group, model, reference, frame, context and baseline label. Overall rows average all frames and contexts within that group/model/reference.", individual)
    _write(outputs[1], "Paired quality comparisons", "Every difference is RIGHT minus LEFT. Existing frame/follow-up comparisons hold model, mapping, source and reference fixed. Frame comparisons hold context fixed; follow-up/main comparisons also hold frame fixed. Both means use exactly the scored pairs. Higher/tied/lower counts refer to saved rounded scores. Exp1 and Exp2 are not paired with each other because their mappings differ. No-rule baseline rows also provide the conventional-meaning treatment contrast when available. Conventional contrasts match source items and exact source/reference text rather than target identities.", paired)
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
