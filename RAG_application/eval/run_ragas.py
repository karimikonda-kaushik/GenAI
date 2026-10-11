#!/usr/bin/env python3
"""
RAGAS evaluation runner for the RAG application.

Example:
  cd RAG_application
  source backend/.venv/bin/activate
  pip install -r eval/requirements.txt
  cp eval/dataset/golden_dataset.example.json eval/dataset/golden_dataset.json
  # edit golden_dataset.json with real questions + ground_truth
  python -m eval.run_ragas --dataset eval/dataset/golden_dataset.json --user-id api-key-user
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError(f"Dataset must be a non-empty JSON list: {path}")
    for i, row in enumerate(data):
        if "question" not in row:
            raise ValueError(f"Row {i} missing 'question'")
        if "ground_truth" not in row or not str(row["ground_truth"]).strip():
            raise ValueError(
                f"Row {i} missing 'ground_truth' "
                "(required for context_precision / context_recall)"
            )
    return data


def _build_predictions(rows: list[dict[str, Any]], user_id: str, k: int) -> list[dict[str, Any]]:
    from eval.pipeline import run_rag_sample

    samples: list[dict[str, Any]] = []
    for i, row in enumerate(rows, start=1):
        q = row["question"].strip()
        print(f"[{i}/{len(rows)}] Retrieving + generating: {q[:80]}...")
        sample = run_rag_sample(q, user_id=user_id, k=k)
        sample["reference"] = row["ground_truth"].strip()
        samples.append(sample)
    return samples


def _run_ragas(samples: list[dict[str, Any]], metric_names: list[str], judge_model: str) -> Any:
    import math

    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    from ragas import EvaluationDataset, SingleTurnSample, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness
    from ragas.run_config import RunConfig

    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY is not set in .env")

    # Free-tier Gemini is ~5 RPM — keep concurrency at 1 and retry slowly.
    judge_llm = LangchainLLMWrapper(
        ChatGoogleGenerativeAI(
            model=judge_model,
            temperature=0,
            max_retries=6,
        )
    )
    judge_embeddings = LangchainEmbeddingsWrapper(
        GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    )

    metric_map = {
        "faithfulness": Faithfulness(llm=judge_llm),
        "answer_relevancy": AnswerRelevancy(llm=judge_llm, embeddings=judge_embeddings),
        "context_precision": ContextPrecision(llm=judge_llm),
        "context_recall": ContextRecall(llm=judge_llm),
    }
    unknown = [m for m in metric_names if m not in metric_map]
    if unknown:
        raise ValueError(f"Unknown metrics: {unknown}. Choose from {list(metric_map)}")
    metrics = [metric_map[m] for m in metric_names]

    eval_samples = [
        SingleTurnSample(
            user_input=s["user_input"],
            retrieved_contexts=s["retrieved_contexts"],
            response=s["response"],
            reference=s["reference"],
        )
        for s in samples
    ]
    dataset = EvaluationDataset(samples=eval_samples)

    print(
        f"\nRunning RAGAS metrics={metric_names} with judge={judge_model} "
        "(batch_size=1, max_workers=1 for free-tier rate limits)..."
    )
    return evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=judge_llm,
        embeddings=judge_embeddings,
        raise_exceptions=False,
        show_progress=True,
        batch_size=1,
        run_config=RunConfig(max_workers=1, max_retries=8, max_wait=120),
    )


def _scores_dict(result: Any) -> dict[str, float]:
    """Normalize EvaluationResult → flat metric averages (skip NaN)."""
    import math

    def _avg(vals: list[float]) -> float | None:
        clean = [v for v in vals if v is not None and not math.isnan(v)]
        return sum(clean) / len(clean) if clean else None

    if hasattr(result, "scores") and isinstance(result.scores, list) and result.scores:
        keys = set()
        for row in result.scores:
            keys.update(row.keys())
        out: dict[str, float] = {}
        for key in sorted(keys):
            vals = []
            for r in result.scores:
                if key not in r or r[key] is None:
                    continue
                try:
                    vals.append(float(r[key]))
                except (TypeError, ValueError):
                    continue
            avg = _avg(vals)
            if avg is not None:
                out[key] = avg
        return out

    try:
        out = {}
        for k, v in dict(result).items():
            try:
                fv = float(v)
            except (TypeError, ValueError):
                continue
            if not math.isnan(fv):
                out[k] = fv
        return out
    except Exception:
        return {"raw": str(result)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the RAG app with RAGAS")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "eval" / "dataset" / "golden_dataset.json",
        help="JSON list of {question, ground_truth}",
    )
    parser.add_argument(
        "--user-id",
        default=os.getenv("DEV_USER_ID", "api-key-user"),
        help="user_id used for retrieval scoping (K8s API key user = api-key-user)",
    )
    parser.add_argument("--k", type=int, default=4, help="Top-K chunks to retrieve")
    parser.add_argument(
        "--predictions-only",
        action="store_true",
        help="Only run RAG and save predictions (skip RAGAS scoring)",
    )
    parser.add_argument(
        "--from-predictions",
        type=Path,
        default=None,
        help="Skip RAG; score an existing predictions JSON from a prior run",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "eval" / "results",
        help="Directory for JSON reports",
    )
    parser.add_argument(
        "--metrics",
        default="faithfulness,answer_relevancy,context_precision,context_recall",
        help="Comma-separated metrics. Free tier tip: start with faithfulness only.",
    )
    parser.add_argument(
        "--judge-model",
        default=os.getenv("RAGAS_JUDGE_MODEL", "gemini-2.0-flash"),
        help="Gemini model for RAGAS judge (default: gemini-2.0-flash; lower free-tier pressure than 2.5)",
    )
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    if args.from_predictions:
        samples = json.loads(args.from_predictions.read_text(encoding="utf-8"))
        if not isinstance(samples, list):
            raise ValueError("--from-predictions must be a JSON list")
    else:
        if not args.dataset.exists():
            example = ROOT / "eval" / "dataset" / "golden_dataset.example.json"
            raise SystemExit(
                f"Dataset not found: {args.dataset}\n"
                f"Copy the example and edit ground_truth values:\n"
                f"  cp {example} {args.dataset}"
            )
        rows = _load_dataset(args.dataset)
        samples = _build_predictions(rows, user_id=args.user_id, k=args.k)

    pred_path = args.out_dir / f"predictions_{stamp}.json"
    pred_path.write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved predictions → {pred_path}")

    empty_ctx = sum(1 for s in samples if not s.get("retrieved_contexts"))
    if empty_ctx:
        print(
            f"WARNING: {empty_ctx}/{len(samples)} questions retrieved 0 chunks. "
            f"Check --user-id ({args.user_id}) matches the user who uploaded docs."
        )

    if args.predictions_only:
        print("Skipping RAGAS scoring (--predictions-only).")
        return

    metric_names = [m.strip() for m in args.metrics.split(",") if m.strip()]
    result = _run_ragas(samples, metric_names=metric_names, judge_model=args.judge_model)
    scores = _scores_dict(result)

    report = {
        "timestamp_utc": stamp,
        "user_id": args.user_id,
        "k": args.k,
        "judge_model": args.judge_model,
        "metric_names": metric_names,
        "n_samples": len(samples),
        "metrics": scores,
        "predictions_file": str(pred_path),
    }
    report_path = args.out_dir / f"ragas_report_{stamp}.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n========== RAGAS RESULTS ==========")
    if not scores:
        print("  (no scores — usually Gemini rate limit / 429)")
        print("  Wait ~60s, then re-score saved predictions:")
        print(
            f"  python -m eval.run_ragas --from-predictions {pred_path} "
            f"--metrics faithfulness --judge-model {args.judge_model}"
        )
    else:
        for name, value in scores.items():
            print(f"  {name:22s} {value:.4f}")
    print(f"Saved report → {report_path}")
    print("===================================")


if __name__ == "__main__":
    main()
