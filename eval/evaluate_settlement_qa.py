"""Evaluation harness for the Settlement Q&A endpoint.

Mirrors the structure and CLI conventions of eval/evaluate.py — takes a
--gold file and a --case-id, calls WorkspaceDocumentService.query() directly
(no HTTP client), and reports three independent metrics plus per-failure
details.

Usage:
  python eval/evaluate_settlement_qa.py \\
      --gold eval/settlement_qa_gold.json \\
      --user-id <user_id> \\
      --case-id <case_id> \\
      [--top-k 10]

Metrics reported:
  answer_correct      — all expected_answer_contains phrases found (case-insensitive)
  citation_correct    — expected_source_file appears in any evidence entity's source_files
  refused_correctly   — for answerable=false entries, answer contains a refusal signal
"""
from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

# ---------------------------------------------------------------------------
# Settlement preamble — must match workspace_settlement_qa.py exactly.
# Copied here so the eval calls the service the same way the route does,
# without importing the route module (which pulls in FastAPI app state).
# ---------------------------------------------------------------------------
_SETTLEMENT_PREAMBLE = (
    "You are a settlement and payout analyst. "
    "Answer using settlement/payout terminology (settlement IDs, payout status, "
    "fee deductions, UTR numbers, net amounts, processing dates). "
    "If the question is not about a settlement or payout, say so clearly rather "
    "than guessing or answering from unrelated context."
)

_REFUSAL_SIGNALS = (
    "don't know",
    "do not know",
    "not found",
    "cannot find",
    "no information",
    "not available",
    "not in",
    "not present",
    "unable to find",
    "not about a settlement",
    "not about",
    "no record",
    "cannot answer",
    "not mentioned",
)


def load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def answer_correct(answer: str, expected_contains: list[str]) -> bool:
    """All expected phrases must appear in the answer (case-insensitive)."""
    if not expected_contains:
        return True  # answerable=false entries have no expected phrases
    low = answer.lower()
    return all(phrase.lower() in low for phrase in expected_contains)


def citation_correct(result: dict, expected_source_file: str | None) -> bool:
    """expected_source_file appears in evidence entities' source_files OR citations list."""
    if expected_source_file is None:
        return True  # unanswerable — citation check not applicable
    needle = expected_source_file.lower()
    for entity in result.get("evidence", {}).get("entities", []):
        for sf in entity.get("source_files", []):
            if needle in sf.lower():
                return True
    for citation in result.get("citations", []):
        for field in ("source_chunk", "excerpt", "description", "entity"):
            if needle in str(citation.get(field, "")).lower():
                return True
    return False


def refused_correctly(answer: str) -> bool:
    """Answer contains at least one refusal signal phrase."""
    low = answer.lower()
    return any(signal in low for signal in _REFUSAL_SIGNALS)


async def run_eval(gold_path: str, user_id: str, case_id: str, top_k: int) -> None:
    from backend.services.workspace_document_service import WorkspaceDocumentService

    gold = load(gold_path)
    questions = gold["questions"]

    svc = WorkspaceDocumentService(user_id=user_id, case_id=case_id)

    results: list[dict[str, Any]] = []
    total_processing_time = 0.0

    for entry in questions:
        qid        = entry["id"]
        question   = entry["question"]
        answerable = entry["answerable"]

        try:
            result = await svc.query(
                question=question,
                top_k=top_k,
                system_prompt_addendum=_SETTLEMENT_PREAMBLE,
            )
            answer        = result.get("answer", "")
            proc_time     = result.get("processing_time_seconds", 0.0)

            a_ok = answer_correct(answer, entry["expected_answer_contains"]) if answerable else None
            c_ok = citation_correct(result, entry["expected_source_file"])   if answerable else None
            r_ok = refused_correctly(answer)                                  if not answerable else None

            results.append({
                "id":               qid,
                "question":         question,
                "answerable":       answerable,
                "answer":           answer,
                "answer_correct":   a_ok,
                "citation_correct": c_ok,
                "refused_correctly": r_ok,
                "processing_time":  proc_time,
                "expected_answer_contains": entry["expected_answer_contains"],
                "expected_source_file":     entry.get("expected_source_file"),
            })
            total_processing_time += proc_time

        except Exception as exc:
            results.append({
                "id":               qid,
                "question":         question,
                "answerable":       answerable,
                "answer":           f"ERROR: {exc}",
                "answer_correct":   False if answerable else None,
                "citation_correct": False if answerable else None,
                "refused_correctly": False if not answerable else None,
                "processing_time":  0.0,
                "expected_answer_contains": entry["expected_answer_contains"],
                "expected_source_file":     entry.get("expected_source_file"),
            })

    # ------------------------------------------------------------------
    # Compute metrics
    # ------------------------------------------------------------------
    answerable_results   = [r for r in results if r["answerable"]]
    unanswerable_results = [r for r in results if not r["answerable"]]

    n_answerable   = len(answerable_results)
    n_unanswerable = len(unanswerable_results)

    answer_hits   = sum(1 for r in answerable_results if r["answer_correct"])
    citation_hits = sum(1 for r in answerable_results if r["citation_correct"])
    refusal_hits  = sum(1 for r in unanswerable_results if r["refused_correctly"])

    answer_acc   = answer_hits   / n_answerable   if n_answerable   else 0.0
    citation_acc = citation_hits / n_answerable   if n_answerable   else 0.0
    refusal_rate = refusal_hits  / n_unanswerable if n_unanswerable else 0.0
    avg_time     = total_processing_time / len(results) if results else 0.0

    # ------------------------------------------------------------------
    # Summary table
    # ------------------------------------------------------------------
    print("\n=== Settlement Q&A Evaluation ===")
    print(f"  Gold file          : {gold_path}")
    print(f"  Case ID            : {case_id}")
    print(f"  Total questions    : {len(results)}")
    print(f"  Answerable         : {n_answerable}")
    print(f"  Unanswerable       : {n_unanswerable}")
    print()
    print(f"  answer_accuracy    : {answer_acc:.1%}  ({answer_hits}/{n_answerable})")
    print(f"  citation_accuracy  : {citation_acc:.1%}  ({citation_hits}/{n_answerable})")
    print(f"  correct_refusal    : {refusal_rate:.1%}  ({refusal_hits}/{n_unanswerable})")
    print(f"  avg_time_seconds   : {avg_time:.2f}s")

    # ------------------------------------------------------------------
    # Failures — printed so they are debuggable, not just a number
    # ------------------------------------------------------------------
    failures = [
        r for r in results
        if r["answer_correct"] is False
        or r["citation_correct"] is False
        or r["refused_correctly"] is False
    ]

    if not failures:
        print("\nAll checks passed.")
        return

    print(f"\n=== Failures ({len(failures)}) ===")
    for r in failures:
        print(f"\n  [{r['id']}] {r['question']}")
        if r["answerable"]:
            if not r["answer_correct"]:
                print(f"    FAIL answer_correct")
                print(f"      expected_contains : {r['expected_answer_contains']}")
                print(f"      actual answer     : {r['answer'][:300]}")
            if not r["citation_correct"]:
                print(f"    FAIL citation_correct")
                print(f"      expected_source   : {r['expected_source_file']}")
        else:
            if not r["refused_correctly"]:
                print(f"    FAIL refused_correctly (should have declined)")
                print(f"      actual answer     : {r['answer'][:300]}")


def main() -> None:
    p = argparse.ArgumentParser(
        description="Evaluate the Settlement Q&A service against a gold set."
    )
    p.add_argument("--gold",    required=True,  help="Path to settlement_qa_gold.json")
    p.add_argument("--user-id", required=True,  help="User ID owning the case workspace")
    p.add_argument("--case-id", required=True,  help="Case ID whose graph will be queried")
    p.add_argument("--top-k",   type=int, default=10, help="top_k passed to query()")
    args = p.parse_args()

    asyncio.run(run_eval(args.gold, args.user_id, args.case_id, args.top_k))


if __name__ == "__main__":
    main()
