"""Sentence metrics for lexical-conflict translations.

BLEU/chrF are divided by 100 and all scores are rounded to four decimals.
Empty hypotheses and COMET exact-zero failures remain null.
"""

from __future__ import annotations

from typing import Any, Optional
from sacrebleu.metrics import BLEU, CHRF


class Scorer:
    def __init__(self, target_language: str = "en") -> None:
        if target_language not in {"en", "zh"}:
            raise ValueError("target_language must be 'en' or 'zh'")
        self.target_language = target_language
        self.bleu = BLEU(effective_order=True, tokenize="zh" if target_language == "zh" else "13a")
        self.chrf = CHRF(word_order=2 if target_language == "en" else 0)
        self._comet_model: Any = None

    @property
    def chrf_label(self) -> str:
        return "chrF++" if self.target_language == "en" else "chrF"

    def score_rows(
        self,
        sources: list[str],
        hypotheses: list[str],
        references: list[str],
        *,
        with_comet: bool = True,
    ) -> list[dict[str, Optional[float]]]:
        """Per-row metrics, reusing local metric objects and any loaded COMET model."""
        nonempty = [i for i, hyp in enumerate(hypotheses) if hyp]

        comet_by_i: dict[int, Optional[float]] = {}
        if with_comet and nonempty:
            comet_by_i = dict(zip(nonempty, self.comet(
                [sources[i] for i in nonempty],
                [hypotheses[i] for i in nonempty],
                [references[i] for i in nonempty],
            )))

        rows: list[dict[str, Optional[float]]] = []
        for i, (hyp, ref) in enumerate(zip(hypotheses, references)):
            if hyp:
                rows.append({
                    "bleu": round(self.bleu.sentence_score(hyp, [ref]).score / 100.0, 4),
                    "chrf": round(self.chrf.sentence_score(hyp, [ref]).score / 100.0, 4),
                    "comet": comet_by_i.get(i),
                })
            else:
                rows.append({"bleu": None, "chrf": None, "comet": None})
        return rows

    def _load_comet_model(self) -> Any:
        if self._comet_model is None:
            from comet import download_model, load_from_checkpoint  # heavy; imported on demand

            self._comet_model = load_from_checkpoint(download_model("Unbabel/wmt22-comet-da"))
        return self._comet_model

    def comet(
        self, sources: list[str], hypotheses: list[str], references: list[str]
    ) -> list[Optional[float]]:
        """COMET-22 scores, guarded so an exact 0.0 becomes None, not a real score."""
        import torch

        model = self._load_comet_model()
        data = [{"src": s, "mt": h, "ref": r} for s, h, r in zip(sources, hypotheses, references)]
        gpus = 1 if torch.cuda.is_available() else 0
        raw = model.predict(data, batch_size=8, gpus=gpus).scores

        out: list[Optional[float]] = []
        for v in raw:
            if v == 0.0:
                print("WARNING: COMET returned exactly 0.0 -> recording null (scorer failure)")
                out.append(None)
            else:
                out.append(round(float(v), 4))
        return out
