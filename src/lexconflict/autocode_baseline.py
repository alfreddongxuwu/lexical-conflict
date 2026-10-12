import pandas as pd
from .autocode import find_matched_terms, get_forms_for_item
from .result_validity import row_is_valid

REQUIRED_AUTO_CODE_COLUMNS = {
    "prompt_id",
    "baseline_type",
    "source_item_id",
    "response",
}


def auto_label_row(row: pd.Series, forms_by_item_id: dict[str, list[str]]) -> pd.Series:
    expected_forms = get_forms_for_item(forms_by_item_id, row["source_item_id"])
    if not row_is_valid(row):
        return pd.Series(
            {
                "contains_expected": False,
                "expected_forms": "|".join(expected_forms),
                "expected_matched_forms": "",
                "baseline_label": "FAILED",
            }
        )
    expected_matched_forms = find_matched_terms(row["response"], expected_forms)
    contains_expected = bool(expected_matched_forms)
    baseline_label = "EXPECTED" if contains_expected else "OTHER"
    return pd.Series(
        {
            "contains_expected": contains_expected,
            "expected_forms": "|".join(expected_forms),
            "expected_matched_forms": "|".join(expected_matched_forms),
            "baseline_label": baseline_label,
        }
    )


def validate_for_auto_coding(df: pd.DataFrame) -> None:
    missing = REQUIRED_AUTO_CODE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Cannot auto-code because columns are missing: {sorted(missing)}"
        )
    unexpected_types = set(df["baseline_type"].dropna().unique()) - {
        "normal_lexical",
        "anomalous_no_lexicon",
    }
    if unexpected_types:
        raise ValueError(f"Unexpected baseline_type values: {sorted(unexpected_types)}")
