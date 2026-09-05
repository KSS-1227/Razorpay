"""Minimal evaluation harness for MMGraphRAG outputs.

Usage:
  python eval/evaluate.py --gold eval/gold_sample.json --pred eval/pred_sample.json

The script expects two JSON files with the following minimal structure:
  {
    "documents": [
      {"doc_id": "doc1", "content": "...", "entities": [{"entity_name": "X", "entity_type": "..."}] }
    ],
    "queries": [
      {"query": "...", "retrieval": ["ENTITY_NAME"], "citations": [{"doc_id":"doc1","span":"..."}] }
    ]
  }

The evaluator computes:
- Entity extraction precision / recall / F1
- Retrieval precision@k (default k=1)
- Hallucination containment rate (predicted entities that match any gold entity)
- Citation traceability (fraction of queries with at least one matching citation span)

This is intentionally small and extensible. It does NOT call the pipeline; it compares predicted JSON to gold JSON.
"""
import argparse
import json
import math
from collections import Counter
from typing import Dict, List, Set


def normalize_name(name: str) -> str:
    return " ".join(name.upper().split())


def load(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_entity_set(docs: List[Dict]) -> Set[str]:
    s = set()
    for d in docs:
        for e in d.get("entities", []):
            s.add(normalize_name(e.get("entity_name", "")))
    return s


def entity_f1(gold_docs: List[Dict], pred_docs: List[Dict]):
    gold = extract_entity_set(gold_docs)
    pred = extract_entity_set(pred_docs)
    tp = len(gold & pred)
    prec = tp / len(pred) if pred else 0.0
    rec = tp / len(gold) if gold else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    return prec, rec, f1, len(gold), len(pred), tp


def retrieval_precision_at_k(gold_queries: List[Dict], pred_queries: List[Dict], k: int = 1):
    total = 0
    hits = 0
    for g, p in zip(gold_queries, pred_queries):
        expected = set([normalize_name(x) for x in g.get("expected_retrieval", [])])
        retrieved = [normalize_name(x) for x in p.get("retrieval", [])][:k]
        if not retrieved:
            continue
        total += 1
        if any(r in expected for r in retrieved):
            hits += 1
    prec_at_k = hits / total if total else 0.0
    return prec_at_k, hits, total


def citation_traceability(gold_queries: List[Dict], pred_queries: List[Dict]):
    total = 0
    matched = 0
    for g, p in zip(gold_queries, pred_queries):
        gold_cites = g.get("expected_citation", []) or []
        pred_cites = p.get("citations", []) or []
        total += 1
        found = False
        for pc in pred_cites:
            for gc in gold_cites:
                if pc.get("doc_id") == gc.get("doc_id") and gc.get("span") and gc.get("span").strip() in (pc.get("span", "")):
                    found = True
                    break
            if found:
                break
        if found:
            matched += 1
    return matched / total if total else 0.0, matched, total


def hallucination_containment(gold_docs: List[Dict], pred_docs: List[Dict]):
    gold = extract_entity_set(gold_docs)
    pred = extract_entity_set(pred_docs)
    if not pred:
        return 1.0, 0, 0
    contained = len(pred & gold)
    rate = contained / len(pred)
    return rate, contained, len(pred)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gold", required=True)
    p.add_argument("--pred", required=True)
    p.add_argument("--k", type=int, default=1, help="precision@k for retrieval")
    args = p.parse_args()

    gold = load(args.gold)
    pred = load(args.pred)

    prec, rec, f1, gold_count, pred_count, tp = entity_f1(gold.get("documents", []), pred.get("documents", []))
    print("Entity extraction:")
    print(f"  gold_entities={gold_count}, pred_entities={pred_count}, true_positive={tp}")
    print(f"  precision={prec:.3f}, recall={rec:.3f}, f1={f1:.3f}\n")

    p_at_k, hits, total_q = retrieval_precision_at_k(gold.get("queries", []), pred.get("queries", []), k=args.k)
    print("Retrieval:")
    print(f"  precision@{args.k} = {p_at_k:.3f} ({hits}/{total_q})\n")

    rate, contained, total_pred = hallucination_containment(gold.get("documents", []), pred.get("documents", []))
    print("Hallucination containment:")
    print(f"  contained={contained}/{total_pred} -> rate={rate:.3f}\n")

    trace_rate, matched, total_q2 = citation_traceability(gold.get("queries", []), pred.get("queries", []))
    print("Citation traceability:")
    print(f"  matched_queries={matched}/{total_q2} -> traceability={trace_rate:.3f}\n")


if __name__ == "__main__":
    main()
