"""
Audio preprocessing pipeline.

Enterprise Compliance Intelligence Platform

Purpose
-------
Convert enterprise audio logs into text that can be processed
by the existing MMGraphRAG pipeline.

Supported Formats
-----------------
- mp3
- wav
- m4a
- flac
- ogg

Output
------
texts  : List[str]
images : List[dict]
"""

from __future__ import annotations

from openai import OpenAI

from ..config import settings
from ..utils.base import logger


class AudioChunking:

    def __init__(
        self,
        audio_path: str,
        working_dir: str,
    ):

        self.audio_path = audio_path
        self.working_dir = working_dir

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY or settings.API_KEY,
            # No base_url override — Whisper must hit api.openai.com directly.
        )

    # ---------------------------------------------------------
    # Public Entry
    # ---------------------------------------------------------

    async def process(
        self
    ) -> tuple[list[str], list[dict]]:

        logger.info("🎤 Processing Audio File...")

        transcript = self._transcribe()

        texts = self._chunk_transcript(
            transcript
        )

        images = []

        logger.info(
            f"✅ Audio transcription complete "
            f"({len(texts)} chunks)"
        )

        return texts, images

    # ---------------------------------------------------------
    # OpenAI Speech-to-Text
    # ---------------------------------------------------------

    def _transcribe(self) -> str:

        with open(
            self.audio_path,
            "rb"
        ) as audio:

            result = self.client.audio.transcriptions.create(

                model="gpt-4o-mini-transcribe",

                file=audio

            )

        return result.text

    # ---------------------------------------------------------
    # Chunk transcript
    # ---------------------------------------------------------

    def _chunk_transcript(
        self,
        transcript: str,
        chunk_size: int = 1200
    ) -> list[str]:

        transcript = transcript.strip()

        if not transcript:

            return []

        chunks = []

        start = 0

        while start < len(transcript):

            chunks.append(

                transcript[
                    start:
                    start + chunk_size
                ]

            )

            start += chunk_size

        return chunks
