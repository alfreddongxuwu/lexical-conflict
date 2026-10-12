import re
from typing import Dict, List
import pandas as pd
from .paths import project_path
from .result_validity import row_is_valid

ACCEPTED_TRANSLATIONS_FILE = project_path("data/coding/accepted_translations.csv")
REQUIRED_AUTO_CODE_COLUMNS = {
    "prompt_id",
    "source_item_id",
    "target_item_id",
    "response",
}
REQUIRED_TRANSLATION_COLUMNS = {"item_id", "accepted_en"}


def normalize_text(text: str) -> str:
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = text.replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = re.sub("\\s+", " ", text)
    return text.strip()


def find_matched_terms(response: str, forms: List[str]) -> List[str]:
    response = normalize_text(response)
    matched_forms = []
    for form in forms:
        escaped = re.escape(form)
        pattern = f"(?<![A-Za-z]){escaped}(?![A-Za-z])"
        if re.search(pattern, response):
            matched_forms.append(form)
    return matched_forms


def load_accepted_translations() -> Dict[str, List[str]]:
    if not ACCEPTED_TRANSLATIONS_FILE.exists():
        raise FileNotFoundError(
            f"Cannot find accepted translations file: {ACCEPTED_TRANSLATIONS_FILE}"
        )
    translations = pd.read_csv(ACCEPTED_TRANSLATIONS_FILE, keep_default_na=False)
    missing = REQUIRED_TRANSLATION_COLUMNS - set(translations.columns)
    if missing:
        raise ValueError(
            f"Accepted translations file is missing required columns: {sorted(missing)}"
        )
    forms_by_item_id: Dict[str, List[str]] = {}
    for item_id, item_rows in translations.groupby("item_id", sort=False):
        forms = []
        for accepted_en in item_rows["accepted_en"]:
            form = normalize_text(accepted_en)
            if form and form not in forms:
                forms.append(form)
        if forms:
            forms_by_item_id[str(item_id)] = forms
    return forms_by_item_id


def get_forms_for_item(
    forms_by_item_id: Dict[str, List[str]], item_id: str
) -> List[str]:
    item_id = str(item_id)
    if item_id not in forms_by_item_id:
        raise ValueError(f"No accepted translations found for item_id={item_id}")
    return forms_by_item_id[item_id]


def auto_label_row(row: pd.Series, forms_by_item_id: Dict[str, List[str]]) -> pd.Series:
    pk_forms = get_forms_for_item(forms_by_item_id, row["source_item_id"])
    ck_forms = get_forms_for_item(forms_by_item_id, row["target_item_id"])
    if not row_is_valid(row):
        return pd.Series(
            {
                "contains_ck": False,
                "contains_pk": False,
                "ck_forms": "|".join(ck_forms),
                "pk_forms": "|".join(pk_forms),
                "ck_matched_forms": "",
                "pk_matched_forms": "",
                "auto_label": "FAILED",
            }
        )
    pk_matched_forms = find_matched_terms(row["response"], pk_forms)
    ck_matched_forms = find_matched_terms(row["response"], ck_forms)
    contains_pk = bool(pk_matched_forms)
    contains_ck = bool(ck_matched_forms)
    if contains_pk and contains_ck:
        auto_label = "BOTH"
    elif contains_pk:
        auto_label = "PK"
    elif contains_ck:
        auto_label = "CK"
    else:
        auto_label = "OTHER"
    return pd.Series(
        {
            "contains_ck": contains_ck,
            "contains_pk": contains_pk,
            "ck_forms": "|".join(ck_forms),
            "pk_forms": "|".join(pk_forms),
            "ck_matched_forms": "|".join(ck_matched_forms),
            "pk_matched_forms": "|".join(pk_matched_forms),
            "auto_label": auto_label,
        }
    )


def validate_for_auto_coding(df: pd.DataFrame) -> None:
    missing = REQUIRED_AUTO_CODE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Cannot auto-code because columns are missing: {sorted(missing)}"
        )


def code_file(run_directory, baseline=False):
    directory = project_path(run_directory)
    frame = pd.read_csv(directory / "responses_merged.csv", keep_default_na=False)
    if frame.prompt_id.duplicated().any():
        raise ValueError("Duplicate prompt identifiers in responses_merged.csv")
    if baseline:
        from .autocode_baseline import (
            auto_label_row as label_row,
            validate_for_auto_coding as validate,
        )
    else:
        label_row, validate = (auto_label_row, validate_for_auto_coding)
    validate(frame)
    columns = frame.apply(
        label_row, axis=1, forms_by_item_id=load_accepted_translations()
    )
    name = "responses_baseline_autocoded.csv" if baseline else "responses_autocoded.csv"
    destination = directory / name
    pd.concat([frame, columns], axis=1).to_csv(
        destination, index=False, encoding="utf-8-sig"
    )
    print(f"Coded {len(frame)} responses: {destination}")
    return destination
