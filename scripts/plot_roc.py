"""
Plot ROC curves (AUC) for RAG evaluation outputs.

This project is primarily an LLM/RAG system, so "accuracy" depends on how we
define a binary label. Here we use EvalCase.context_required as the label, and
use continuous evaluator scores as the model score to plot ROC/AUC.

Run:
  python scripts/evaluate_rag.py
  python scripts/plot_roc.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
from sklearn.metrics import auc, confusion_matrix, roc_curve


EVAL_PATH = Path("docs/evals/latest_rag_eval.json")
OUT_DIR = Path("docs/evals")


def _load_eval(path: Path) -> Dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing eval file at {path}. Run: python scripts/evaluate_rag.py"
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _extract_labels_and_scores(details: List[Dict]) -> Tuple[List[int], Dict[str, List[float]]]:
    y_true: List[int] = []
    scores: Dict[str, List[float]] = {"faithfulness_score": [], "relevance_score": []}

    for d in details:
        y_true.append(1 if bool(d["context_required"]) else 0)
        scores["faithfulness_score"].append(float(d["faithfulness_score"]))
        scores["relevance_score"].append(float(d["relevance_score"]))

    return y_true, scores


def _best_threshold_by_youden(y_true: List[int], y_score: List[float]) -> Tuple[float, float]:
    fpr, tpr, thresholds = roc_curve(y_true, y_score)
    j = tpr - fpr
    best_idx = int(j.argmax())
    return float(thresholds[best_idx]), float(j[best_idx])


def _accuracy_at_threshold(y_true: List[int], y_score: List[float], threshold: float) -> Tuple[float, List[List[int]]]:
    y_pred = [1 if s >= threshold else 0 for s in y_score]
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    acc = (tp + tn) / max((tp + tn + fp + fn), 1)
    return float(acc), cm.tolist()


def _plot_one(y_true: List[int], y_score: List[float], title: str, out_path: Path) -> Dict:
    fpr, tpr, _ = roc_curve(y_true, y_score)
    roc_auc = auc(fpr, tpr)

    best_thr, best_j = _best_threshold_by_youden(y_true, y_score)
    best_acc, cm = _accuracy_at_threshold(y_true, y_score, best_thr)

    plt.figure(figsize=(7, 6))
    plt.plot(fpr, tpr, linewidth=2, label=f"AUC = {roc_auc:.3f}")
    plt.plot([0, 1], [0, 1], linestyle="--", linewidth=1, color="gray")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend(loc="lower right")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=160)
    plt.close()

    return {
        "auc": float(roc_auc),
        "best_threshold": float(best_thr),
        "best_youden_j": float(best_j),
        "accuracy_at_best_threshold": float(best_acc),
        "confusion_matrix_at_best_threshold": cm,
        "plot_path": str(out_path),
    }


def main() -> None:
    report = _load_eval(EVAL_PATH)
    details = report.get("details", [])
    if not details:
        raise ValueError(f"No 'details' in {EVAL_PATH}")

    # NOTE: EvalResult currently doesn't persist context_required; defaulting to True
    # will make ROC undefined. We detect and warn below.
    y_true, scores = _extract_labels_and_scores(details)
    if len(set(y_true)) < 2:
        raise ValueError(
            "ROC needs both classes (0 and 1) in y_true. "
            "Update the eval report to include 'context_required' per case."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {
        "label": "context_required",
        "n": len(y_true),
        "positive_rate": sum(y_true) / max(len(y_true), 1),
        "metrics": {},
    }

    results["metrics"]["faithfulness_score"] = _plot_one(
        y_true=y_true,
        y_score=scores["faithfulness_score"],
        title="ROC: faithfulness_score predicting context_required",
        out_path=OUT_DIR / "roc_faithfulness_context_required.png",
    )
    results["metrics"]["relevance_score"] = _plot_one(
        y_true=y_true,
        y_score=scores["relevance_score"],
        title="ROC: relevance_score predicting context_required",
        out_path=OUT_DIR / "roc_relevance_context_required.png",
    )

    out_json = OUT_DIR / "roc_report.json"
    out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(json.dumps(results, indent=2))
    print(f"\nSaved: {out_json}")


if __name__ == "__main__":
    main()

