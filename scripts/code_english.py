"""Accepted-form English coding for saved conflict and baseline responses."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from code_english_baseline import normalize_text
from result_validity import row_is_valid


@dataclass
class EnglishLexicalCoder:
    forms: dict[str, list[str]]
    patterns: dict[str, list[re.Pattern]]

    @classmethod
    def from_csv(cls, path: Path) -> EnglishLexicalCoder:
        forms: dict[str, list[str]] = {}
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not {"item_id", "accepted_en"} <= set(reader.fieldnames or []):
                raise ValueError("Accepted translations require item_id and accepted_en")
            for row in reader:
                item, form = row["item_id"], normalize_text(row["accepted_en"])
                if not item or not form:
                    raise ValueError("Empty item or accepted form")
                if form not in forms.setdefault(item, []):
                    forms[item].append(form)
        return cls(forms, {item: [re.compile(rf"(?<![A-Za-z]){re.escape(form)}(?![A-Za-z])")
                                  for form in values] for item, values in forms.items()})

    def code(self, row: dict[str, str]) -> dict[str, str]:
        baseline = "target_item_id" not in row
        roles = [("expected" if baseline else "pk", row["source_item_id"])]
        if not baseline:
            roles.append(("ck", row["target_item_id"]))
        response = normalize_text(row["response"])
        valid = row_is_valid(row)
        result: dict[str, str] = {}
        hits: dict[str, bool] = {}
        for role, item in roles:
            if item not in self.forms:
                raise ValueError(f"No accepted translations for {item}")
            matches = [form for form, pattern in zip(self.forms[item], self.patterns[item])
                       if valid and pattern.search(response)]
            hits[role] = bool(matches)
            result[f"contains_{role}"] = str(bool(matches))
            result[f"{role}_forms"] = "|".join(self.forms[item])
            result[f"{role}_matched_forms"] = "|".join(matches)
        if baseline:
            result["baseline_label"] = "FAILED" if not valid else "EXPECTED" if hits["expected"] else "OTHER"
        else:
            result["auto_label"] = ("FAILED" if not valid else "BOTH" if hits["pk"] and hits["ck"]
                                    else "PK" if hits["pk"] else "CK" if hits["ck"] else "OTHER")
        return result
