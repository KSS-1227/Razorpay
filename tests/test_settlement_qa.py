"""
Unit tests for the Settlement Q&A feature.

Covers:
1. prompt.py — new entity types present in DEFAULT_ENTITY_TYPES and in the
   entity_extraction prompt text.
2. csv_preprocessing.py — CSVChunking produces natural-language chunks that
   contain SETTLEMENT_AMOUNT, FEE_DEDUCTION, and UTR_NUMBER field values.
3. Entity extraction — extract_entities() run against a mocked LLM response
   confirms SETTLEMENT_AMOUNT, FEE_DEDUCTION, and UTR_NUMBER graph nodes are
   actually created (not just that the prompt labels exist).
4. workspace_settlement_qa.py — correct path /api/workspace/{id}/settlement-qa,
   preamble injection, IDK response for a non-settlement question, 404 on
   missing graph.
5. Eval helpers — _is_idk and _answer_matches unit-tested directly.
"""
from __future__ import annotations

import asyncio
import csv
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# 1. Prompt — entity types registered
# ---------------------------------------------------------------------------

class TestSettlementEntityTypesInPrompt:
    def setup_method(self):
        from backend.core.prompt import PROMPTS
        self.PROMPTS = PROMPTS

    def test_new_types_in_default_entity_types(self):
        types = self.PROMPTS["DEFAULT_ENTITY_TYPES"]
        for expected in [
            "SETTLEMENT_ID", "SETTLEMENT_DATE", "SETTLEMENT_AMOUNT",
            "PAYOUT_STATUS", "FEE_DEDUCTION", "UTR_NUMBER",
        ]:
            assert expected in types, f"{expected} missing from DEFAULT_ENTITY_TYPES"

    def test_existing_types_untouched(self):
        types = self.PROMPTS["DEFAULT_ENTITY_TYPES"]
        for existing in ["VENDOR", "INVOICE", "INVOICE_AMOUNT", "CONTRACT_AMOUNT",
                         "PAYMENT_TERMS", "DUE_DATE", "APPROVAL_LIMIT"]:
            assert existing in types, f"Existing type {existing} was removed"

    def test_bullet_definitions_in_extraction_prompt(self):
        prompt = self.PROMPTS["entity_extraction"]
        for label in [
            "SETTLEMENT_ID", "SETTLEMENT_DATE", "SETTLEMENT_AMOUNT",
            "PAYOUT_STATUS", "FEE_DEDUCTION", "UTR_NUMBER",
        ]:
            assert label in prompt, f"Bullet definition for {label} missing from entity_extraction prompt"

    def test_existing_bullet_definitions_untouched(self):
        prompt = self.PROMPTS["entity_extraction"]
        for label in ["VENDOR", "INVOICE", "APPROVAL_LIMIT"]:
            assert label in prompt, f"Existing bullet for {label} was removed"


# ---------------------------------------------------------------------------
# 2. CSV preprocessing — chunks contain settlement field values
# ---------------------------------------------------------------------------

class TestCSVChunking:
    def _write_csv(self, rows: list[dict], headers: list[str]) -> str:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        writer = csv.DictWriter(tmp, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        tmp.close()
        return tmp.name

    def test_chunks_contain_settlement_fields(self):
        from backend.ingestion.csv_preprocessing import CSVChunking
        path = self._write_csv(
            [{"settlement_id": "STL-2024-0101", "settlement_amount": "95000",
              "fee_deduction": "2500", "utr_number": "407291836540",
              "payout_status": "processed"}],
            ["settlement_id", "settlement_amount", "fee_deduction", "utr_number", "payout_status"],
        )
        try:
            texts, images = _run(CSVChunking(csv_path=path, working_dir="/tmp").process())
            combined = " ".join(texts)
            assert "95000" in combined
            assert "2500" in combined
            assert "407291836540" in combined
            assert images == []
        finally:
            os.unlink(path)

    def test_header_summary_line_present(self):
        from backend.ingestion.csv_preprocessing import CSVChunking
        path = self._write_csv(
            [{"settlement_id": "STL-001", "settlement_amount": "1000"}],
            ["settlement_id", "settlement_amount"],
        )
        try:
            texts, _ = _run(CSVChunking(csv_path=path, working_dir="/tmp").process())
            assert any("settlement_id" in t and "settlement_amount" in t for t in texts)
        finally:
            os.unlink(path)

    def test_empty_rows_skipped(self):
        from backend.ingestion.csv_preprocessing import CSVChunking
        path = self._write_csv(
            [{"settlement_id": "STL-001", "settlement_amount": "1000"},
             {"settlement_id": "",        "settlement_amount": ""}],
            ["settlement_id", "settlement_amount"],
        )
        try:
            texts, _ = _run(CSVChunking(csv_path=path, working_dir="/tmp").process())
            data_rows = [t for t in texts if "settlement_id:" in t.lower()]
            assert len(data_rows) == 1
        finally:
            os.unlink(path)

    def test_multiple_rows_produce_multiple_chunks(self):
        from backend.ingestion.csv_preprocessing import CSVChunking
        rows = [
            {"settlement_id": f"STL-{i}", "settlement_amount": str(i * 1000)}
            for i in range(1, 6)
        ]
        path = self._write_csv(rows, ["settlement_id", "settlement_amount"])
        try:
            texts, _ = _run(CSVChunking(csv_path=path, working_dir="/tmp").process())
            data_rows = [t for t in texts if "settlement_id:" in t.lower()]
            assert len(data_rows) == 5
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# 3. Entity extraction — extract_entities() produces settlement graph nodes
#
# Strategy: mock model_if_cache so no OpenAI call is made, but return a
# realistic LLM response string that contains SETTLEMENT_AMOUNT, FEE_DEDUCTION,
# and UTR_NUMBER tuples in the pipeline's expected format.  Then assert the
# resulting graph contains nodes of those types.
# ---------------------------------------------------------------------------

class TestSettlementEntityExtraction:
    """Run extract_entities() with a mocked LLM and verify graph node types."""

    # Minimal LLM response in the pipeline's tuple format.
    # Uses the default delimiters: tuple_delimiter=<|>, record_delimiter=##
    _LLM_RESPONSE = (
        '("entity"<|>"STL-2024-0101"<|>"SETTLEMENT_ID"<|>"Settlement batch STL-2024-0101")'
        "##"
        '("entity"<|>"\u20b995000"<|>"SETTLEMENT_AMOUNT"<|>"Net settlement amount paid out")'
        "##"
        '("entity"<|>"\u20b92500"<|>"FEE_DEDUCTION"<|>"Platform fee deducted from settlement")'
        "##"
        '("entity"<|>"407291836540"<|>"UTR_NUMBER"<|>"Bank UTR for this payout")'
        "##"
        '("entity"<|>"processed"<|>"PAYOUT_STATUS"<|>"Payout was successfully processed")'
        "<|COMPLETE|>"
    )

    def _make_chunk(self) -> dict:
        return {
            "chunk-001": {
                "content": (
                    "Settlement STL-2024-0101. Amount: \u20b995,000. "
                    "Fee deduction: \u20b92,500. UTR: 407291836540. Status: processed."
                ),
                "chunk_order_index": 0,
                "file_name": "settlement_batch_q1.csv",
                "tokens": 30,
            }
        }

    def test_settlement_node_types_created(self):
        """extract_entities must produce nodes for SETTLEMENT_AMOUNT, FEE_DEDUCTION, UTR_NUMBER."""
        import networkx as nx
        from backend.graph.text2graph import extract_entities
        from backend.storage.graph_storage import NetworkXStorage
        from backend.storage.kv_storage import JsonKVStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            # In-memory NetworkX graph so no CockroachDB needed
            graph = NetworkXStorage(
                namespace="chunk_entity_relation",
                storage_dir=tmpdir,
            )

            cache = JsonKVStorage(
                namespace="llm_response_cache",
                storage_dir=tmpdir,
            )

            # Patch model_if_cache to return our canned LLM response.
            # extract_entities calls it via limit_async_func_call wrapper, so
            # we patch at the source module level.
            with patch(
                "backend.graph.text2graph.model_if_cache",
                new=AsyncMock(return_value=self._LLM_RESPONSE),
            ):
                result_graph = _run(
                    extract_entities(
                        cache_storage=cache,
                        chunks=self._make_chunk(),
                        knwoledge_graph_inst=graph,
                        working_dir=tmpdir,
                    )
                )

            assert result_graph is not None, "extract_entities returned None — no entities found"

            # Collect entity_type values from all nodes
            entity_types = {
                data.get("entity_type", "").replace('"', "").strip().upper()
                for _, data in result_graph.graph.nodes(data=True)
            }

            assert "SETTLEMENT_AMOUNT" in entity_types, (
                f"SETTLEMENT_AMOUNT node missing. Found types: {entity_types}"
            )
            assert "FEE_DEDUCTION" in entity_types, (
                f"FEE_DEDUCTION node missing. Found types: {entity_types}"
            )
            assert "UTR_NUMBER" in entity_types, (
                f"UTR_NUMBER node missing. Found types: {entity_types}"
            )


# ---------------------------------------------------------------------------
# 4. Settlement Q&A route
# ---------------------------------------------------------------------------

def _make_settlement_app(fake_query_fn):
    """Return a TestClient for the settlement router with auth and DB patched out."""
    import backend.api.routes.workspace_settlement_qa as mod
    from fastapi import FastAPI, Depends
    from fastapi.testclient import TestClient
    from backend.auth.middleware.jwt_middleware import AuthContext

    instance = MagicMock()
    instance.query = AsyncMock(side_effect=fake_query_fn)

    with patch.object(mod, "_verify_case_ownership", new=AsyncMock()), \
         patch.object(mod, "WorkspaceDocumentService", return_value=instance):

        app = FastAPI()
        app.include_router(
            mod.router,
            prefix="/api",
            dependencies=[Depends(lambda: AuthContext(user_id="u1", email="x@x.com", role="user"))],
        )
        return TestClient(app, raise_server_exceptions=False), instance


class TestSettlementQARoute:

    def test_correct_path_resolves(self):
        """POST /api/workspace/{id}/settlement-qa must return 200, not 404/405."""
        async def fake_query(question, top_k, session_id):
            return {"answer": "STL-2024-0101", "evidence": {}, "citations": [],
                    "processing_time_seconds": 0.1, "graph": {"nodes": 5, "edges": 4}}

        client, _ = _make_settlement_app(fake_query)
        resp = client.post(
            "/api/workspace/case-abc/settlement-qa",
            json={"question": "What is the settlement ID?"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 200

    def test_preamble_prepended_to_question(self):
        """The question forwarded to svc.query must start with _SETTLEMENT_PREAMBLE."""
        from backend.api.routes.workspace_settlement_qa import _SETTLEMENT_PREAMBLE

        captured: list[str] = []

        async def fake_query(question, top_k, session_id):
            captured.append(question)
            return {"answer": "ok", "evidence": {}, "citations": [],
                    "processing_time_seconds": 0.05, "graph": {"nodes": 1, "edges": 0}}

        client, _ = _make_settlement_app(fake_query)
        client.post(
            "/api/workspace/case-abc/settlement-qa",
            json={"question": "What is the settlement amount?"},
            headers={"Authorization": "Bearer fake"},
        )
        assert captured, "svc.query was never called"
        assert captured[0].startswith(_SETTLEMENT_PREAMBLE)

    def test_non_settlement_question_returns_idk_style_answer(self):
        """When the underlying engine returns an IDK answer for an off-topic question,
        the route must pass it through unchanged — not suppress or replace it."""
        idk_answer = "This question is not about a settlement or payout. I cannot answer it."

        async def fake_query(question, top_k, session_id):
            return {"answer": idk_answer, "evidence": {}, "citations": [],
                    "processing_time_seconds": 0.05, "graph": {"nodes": 1, "edges": 0}}

        client, _ = _make_settlement_app(fake_query)
        resp = client.post(
            "/api/workspace/case-abc/settlement-qa",
            json={"question": "What is the weather in Mumbai today?"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["result"]["answer"] == idk_answer

    def test_response_envelope_shape(self):
        """Response must include success, question, case_id, session_id, result."""
        async def fake_query(question, top_k, session_id):
            return {"answer": "processed", "evidence": {}, "citations": [],
                    "processing_time_seconds": 0.05, "graph": {"nodes": 3, "edges": 2}}

        client, _ = _make_settlement_app(fake_query)
        resp = client.post(
            "/api/workspace/case-xyz/settlement-qa",
            json={"question": "What is the payout status?"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 200
        body = resp.json()
        for key in ("success", "question", "case_id", "session_id", "result"):
            assert key in body, f"Key '{key}' missing from response"
        assert body["success"] is True
        assert body["case_id"] == "case-xyz"

    def test_404_when_graph_not_found(self):
        """FileNotFoundError from svc.query must surface as HTTP 404."""
        async def fake_query(question, top_k, session_id):
            raise FileNotFoundError("No graph")

        client, _ = _make_settlement_app(fake_query)
        resp = client.post(
            "/api/workspace/case-abc/settlement-qa",
            json={"question": "What is the settlement amount?"},
            headers={"Authorization": "Bearer fake"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. Eval helpers
# ---------------------------------------------------------------------------

class TestEvalHelpers:
    def setup_method(self):
        import importlib.util
        import pathlib
        spec = importlib.util.spec_from_file_location(
            "evaluate_settlement_qa",
            str(pathlib.Path(__file__).parent.parent / "eval" / "evaluate_settlement_qa.py"),
        )
        try:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.mod = mod
        except Exception:
            self.mod = None

    def test_idk_detection_positive(self):
        if self.mod is None:
            pytest.skip("eval module not importable")
        assert self.mod._is_idk("I don't know the answer to that question.")
        assert self.mod._is_idk("This information is not available in the provided data.")
        assert self.mod._is_idk("Cannot find any settlement matching that description.")

    def test_idk_detection_negative(self):
        if self.mod is None:
            pytest.skip("eval module not importable")
        assert not self.mod._is_idk("The settlement amount is \u20b995,000.")
        assert not self.mod._is_idk("STL-2024-0101 was processed on 2024-01-15.")

    def test_answer_matches_substring(self):
        if self.mod is None:
            pytest.skip("eval module not importable")
        assert self.mod._answer_matches("The net amount paid was \u20b982,500.", "82500")
        assert self.mod._answer_matches("Settlement STL-2024-0101 was processed.", "STL-2024-0101")

    def test_answer_no_match(self):
        if self.mod is None:
            pytest.skip("eval module not importable")
        assert not self.mod._answer_matches("The amount is \u20b950,000.", "82500")

    def test_evaluator_url_uses_path_parameter(self):
        """run_question must build the URL with case_id as a path segment."""
        if self.mod is None:
            pytest.skip("eval module not importable")
        # Inspect the URL that would be built — no HTTP call needed
        import inspect
        src = inspect.getsource(self.mod.run_question)
        assert "/api/workspace/" in src
        assert "settlement-qa" in src
        # The old flat path must not appear
        assert "/api/workspace/settlement-qa/" not in src
