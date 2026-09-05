Evaluation harness
=================

This folder contains a minimal evaluation harness to compute the metrics required by the problem statement:

- Retrieval precision (precision@k)
- Entity extraction precision/recall/F1
- Hallucination containment rate (fraction of predicted entities that are grounded in gold evidence)
- Citation traceability (fraction of predicted answers/retrievals that include correct evidence links)

How it works
------------

1. Produce predictions: run the pipeline (ingest -> build KG -> GraphRAG) and export the pipeline outputs to a JSON file. The extractor writes per-chunk KG info to `kv_store_chunk_knowledge_graph.json` inside the working dir (see `backend/graph/text2graph.py`). You can also assemble predicted retrieval results into the same JSON format.
2. Run the evaluator below with `--gold` (gold annotations) and `--pred` (predicted results).

Files
-----

- `evaluate.py` — evaluation script. Compares `gold.json` and `pred.json` and prints metrics.
- `gold_sample.json` — a tiny example gold dataset and a matching predicted file `pred_sample.json` can be used to test the script.

Reproducibility / External dependencies
-------------------------------------

The pipeline depends on several external components. To reproduce results end-to-end, ensure the following are available and documented for judges:

- MinerU (optional but recommended) — high-quality PDF parser used by the ingestion pipeline. Provide installation instructions or a binary in a reproducible environment.
- YOLO weights (for image entity detection) — include the exact weights filename and where to download them (or a small placeholder if not used in evaluation).
- LLM/API keys (e.g. OpenAI) — set via environment variables (e.g. `LLM_API_KEY`). Provide instructions for obtaining keys and setting them in a `.env` file.
- Supabase credentials (if running auth-protected routes locally) — document how to create a dev project or run the routes with `--no-auth` for evaluation.

Running the sample evaluation
-----------------------------

1. Create a Python virtual environment and install the project requirements.

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
```

2. Run the evaluator with the provided sample files:

```bash
python eval/evaluate.py --gold eval/gold_sample.json --pred eval/pred_sample.json
```

Notes
-----
This harness is intentionally lightweight: it compares structured JSON outputs against gold labels and computes straightforward metrics. For full automation (ingest → pipeline → evaluate) you can extend the harness to (a) call the pipeline programmatically, (b) populate `pred.json` automatically, and (c) add CI steps.
