"""
CSV preprocessing pipeline.

Enterprise Compliance Intelligence Platform

Purpose
-------
Process CSV settlement exports into the same natural-language chunk format
expected by MMKGBuilder / text2graph.py entity extraction.

Each data row is converted to a single "Column: Value. Column: Value." sentence
so the LLM entity extractor can recognise SETTLEMENT_ID, SETTLEMENT_AMOUNT,
FEE_DEDUCTION, UTR_NUMBER, etc. from raw CSV exports.

Output
------
texts  : List[str]   — one string per non-empty data row
images : List[dict]  — always empty (CSV carries no embedded images)

Compatible with:
- .csv  (UTF-8 or system default encoding, comma-separated)
"""
from __future__ import annotations

import csv
from pathlib import Path

from ..utils.base import logger


class CSVChunking:

    def __init__(self, csv_path: str, working_dir: str):
        self.csv_path = csv_path
        self.working_dir = working_dir

    # ---------------------------------------------------------
    # Public Entry
    # ---------------------------------------------------------

    async def process(self) -> tuple[list[str], list[dict]]:
        logger.info("📄 Processing CSV file: %s", self.csv_path)
        texts = self._extract_text()
        logger.info("✅ CSV parsed (%d rows extracted)", len(texts))
        return texts, []

    # ---------------------------------------------------------
    # Extract rows as natural-language sentences
    # ---------------------------------------------------------

    def _extract_text(self) -> list[str]:
        path = Path(self.csv_path)
        extracted: list[str] = []

        try:
            raw = path.read_bytes()
            encoding = "utf-8-sig" if raw[:3] == b"\xef\xbb\xbf" else "utf-8"
        except Exception:
            encoding = "utf-8"

        try:
            with path.open(newline="", encoding=encoding, errors="replace") as fh:
                reader = csv.DictReader(fh)
                headers = reader.fieldnames or []
                if headers:
                    extracted.append(f"This CSV contains columns: {', '.join(headers)}.")
                for row in reader:
                    pairs = [
                        f"{k}: {v.strip()}"
                        for k, v in row.items()
                        if v and v.strip()
                    ]
                    if pairs:
                        extracted.append(". ".join(pairs) + ".")
        except Exception as exc:
            logger.error("Failed to parse CSV %s: %s", self.csv_path, exc)

        return extracted
