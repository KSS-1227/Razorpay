"""
End-to-end demo: build a knowledge graph from a PDF and answer questions.

Usage:
    python examples/docqa_example.py
"""
import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.builder import MMKGBuilder
from backend.retrieval.query import GraphRAGQuery
from backend.config import settings as parameter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PDF_PATH  = os.path.join(os.path.dirname(__file__), "..", "data", "input", "2020.acl-main.45.pdf")
QA_PATH   = os.path.join(os.path.dirname(__file__), "..", "data", "input", "13_qa.jsonl")
OUT_PATH  = os.path.join(os.path.dirname(__file__), "docqa_results.md")


async def main():
    # ---- Step 1: build graph -------------------------------------------
    builder = MMKGBuilder(pdf_path=PDF_PATH)
    await builder.index(PDF_PATH)

    # ---- Step 2: load QA pairs -----------------------------------------
    qa_pairs = []
    if os.path.exists(QA_PATH):
        with open(QA_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    qa_pairs.append(json.loads(line))
    else:
        qa_pairs = [{"question": "What is the main contribution of this paper?", "answer": "N/A"}]

    # ---- Step 3: query & collect results --------------------------------
    querier = GraphRAGQuery()
    results = []

    for item in qa_pairs:
        question = item.get("question", "")
        gt       = item.get("answer", "N/A")
        print(f"\n❓ {question}")
        answer   = await querier.query(question)
        print(f"✅ {answer[:200]}...")
        results.append({"question": question, "ground_truth": gt, "model_answer": answer})

    # ---- Step 4: write report -------------------------------------------
    lines = ["# DocQA Results\n"]
    for i, r in enumerate(results, 1):
        lines += [
            f"## Q{i}: {r['question']}\n",
            f"**Ground Truth**: {r['ground_truth']}\n",
            f"**Model Answer**: {r['model_answer']}\n",
            "---\n",
        ]

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n📄 Results saved to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
