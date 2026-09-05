"""
Settlement Q&A Evaluation Harness

Runs every question in eval/settlement_qa_gold.json through the live
POST /api/workspace/settlement-qa endpoint and reports:

  - answer_match_rate   : fraction of in-batch questions whose answer
                          contains the expected value (case-insensitive substring)
  - idk_rate            : fraction of out-of-batch questions where the model
                          correctly declined to answer (said "don't know" /
                          "not" / "no information" / "cannot" etc.)
  - citation_hit_rate   : fraction of in-batch questions where the response
                          cited the expected source document
  - overall_score       : simple average of the three rates above

Usage
-----
  python eval/evaluate_settlement_qa.py \\
      --gold eval/settlement_qa_gold.json \\
      --base-url http://localhost:8000 \\
      --token <JWT> \\
      --case-id <case_id>

The --token and --case-id flags are required because the endpoint is
JWT-protected and workspace-scoped.

Output
------
Prints a human-readable summary table suitable for a demo.
Optionally writes raw predictions to --out (default: eval/settlement_qa_pred.json).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

try:
    import httpx
except ImportError:
    print("httpx is required: pip install httpx", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# IDK detection — conservative list of phrases that indicate the model
# correctly declined rather than hallucinating an answer.
# ---------------------------------------------------------------------------
_IDK_PHRASES = [
    "don't know",
    "do not know",
    "not available",
    "no information",
    "cannot find",
    "not found",
    "not in",
    "not mentioned",
    "not about a settlement",
    "not related",
    "cannot answer",
    "unable to",
    "no data",
    "not provided",
]


def _is_idk(answer: str) -> bool:
    lower = answer.lower()
    return any(phrase in lower for phrase in _IDK_PHRASES)


def _answer_matches(answer: str, expected: str) -> bool:
    """Case-insensitive substring match, normalising whitespace."""
    return expected.lower().replace(",", "").replace(" ", "") in \
           answer.lower().replace(",", "").replace(" ", "")


def _citation_matches(citations: list[dict], expected_source: str | None) -> bool:
    if not expected_source:
        return False
    for c in citations:
        src = (c.get("source") or c.get("doc_id") or c.get("file_name") or "").lower()
        if expected_source.lower() in src or src in expected_source.lower():
            return True
    return False


def run_question(
    client: httpx.Client,
    base_url: str,
    token: str,
    case_id: str,
    question: str,
    top_k: int = 10,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/workspace/{case_id}/settlement-qa"
    payload = {"question": question, "top_k": top_k}
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = client.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result", {})
        return {
            "answer": result.get("answer", ""),
            "citations": result.get("citations", []),
            "error": None,
        }
    except Exception as exc:
        return {"answer": "", "citations": [], "error": str(exc)}


def evaluate(gold_path: str, base_url: str, token: str, case_id: str, out_path: str) -> None:
    with open(gold_path, encoding="utf-8") as f:
        gold = json.load(f)

    questions = gold["questions"]
    predictions: list[dict] = []

    in_batch   = [q for q in questions if q.get("answer_in_batch", True)]
    out_batch  = [q for q in questions if not q.get("answer_in_batch", True)]

    answer_hits   = 0
    idk_hits      = 0
    citation_hits = 0

    print(f"\n{'='*64}")
    print(f"  Settlement Q&A Evaluation — {len(questions)} questions")
    print(f"  Endpoint : {base_url}/api/workspace/{{case_id}}/settlement-qa")
    print(f"  Case     : {case_id}")
    print(f"{'='*64}\n")

    with httpx.Client() as client:
        for q in questions:
            t0 = time.time()
            pred = run_question(client, base_url, token, case_id, q["question"])
            elapsed = round(time.time() - t0, 2)

            answer    = pred["answer"]
            citations = pred["citations"]
            error     = pred["error"]

            in_batch_q   = q.get("answer_in_batch", True)
            idk_expected = q.get("idk_expected", False)

            answer_match   = False
            idk_correct    = False
            citation_match = False

            if error:
                status = f"ERROR: {error}"
            elif idk_expected:
                idk_correct = _is_idk(answer)
                if idk_correct:
                    idk_hits += 1
                status = "IDK ✓" if idk_correct else "IDK ✗ (hallucinated)"
            else:
                answer_match = _answer_matches(answer, q["expected_answer"])
                if answer_match:
                    answer_hits += 1
                citation_match = _citation_matches(citations, q.get("expected_source"))
                if citation_match:
                    citation_hits += 1
                status = (
                    f"{'ANS ✓' if answer_match else 'ANS ✗'} | "
                    f"{'CITE ✓' if citation_match else 'CITE ✗'}"
                )

            print(f"[{q['id']}] {q['question'][:72]}")
            print(f"       Status : {status}  ({elapsed}s)")
            if not idk_expected:
                print(f"       Expected: {q['expected_answer']}")
                snippet = answer[:120].replace("\n", " ")
                print(f"       Got     : {snippet}{'…' if len(answer) > 120 else ''}")
            print()

            predictions.append({
                "id": q["id"],
                "question": q["question"],
                "answer": answer,
                "citations": citations,
                "answer_match": answer_match,
                "idk_correct": idk_correct,
                "citation_match": citation_match,
                "error": error,
            })

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    n_in  = len(in_batch)
    n_out = len(out_batch)

    answer_match_rate = answer_hits / n_in  if n_in  else 0.0
    idk_rate          = idk_hits    / n_out if n_out else 0.0
    citation_hit_rate = citation_hits / n_in if n_in else 0.0
    overall_score     = (answer_match_rate + idk_rate + citation_hit_rate) / 3

    print(f"{'='*64}")
    print("  SUMMARY")
    print(f"{'='*64}")
    print(f"  In-batch questions   : {n_in}")
    print(f"  Out-of-batch (IDK)   : {n_out}")
    print()
    print(f"  Answer match rate    : {answer_hits}/{n_in}  = {answer_match_rate:.1%}")
    print(f"  IDK correct rate     : {idk_hits}/{n_out}  = {idk_rate:.1%}")
    print(f"  Citation hit rate    : {citation_hits}/{n_in}  = {citation_hit_rate:.1%}")
    print(f"  ─────────────────────────────────────────")
    print(f"  Overall score        : {overall_score:.1%}")
    print(f"{'='*64}\n")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": {
            "answer_match_rate": round(answer_match_rate, 4),
            "idk_rate": round(idk_rate, 4),
            "citation_hit_rate": round(citation_hit_rate, 4),
            "overall_score": round(overall_score, 4),
        }, "predictions": predictions}, f, indent=2, ensure_ascii=False)
    print(f"Raw predictions written to: {out_path}")


def main() -> None:
    p = argparse.ArgumentParser(description="Evaluate settlement Q&A endpoint")
    p.add_argument("--gold",     default="eval/settlement_qa_gold.json")
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--token",    required=True, help="Supabase JWT bearer token")
    p.add_argument("--case-id",  required=True, help="Workspace case ID")
    p.add_argument("--out",      default="eval/settlement_qa_pred.json")
    args = p.parse_args()
    evaluate(args.gold, args.base_url, args.token, args.case_id, args.out)


if __name__ == "__main__":
    main()
