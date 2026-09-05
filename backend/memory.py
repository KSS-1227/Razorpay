"""CockroachDB-backed conversation memory for workspace GraphRAG sessions."""
from __future__ import annotations

from .cockroach_vector_storage import _get_pool


async def get_session_history(workspace_id: str, session_id: str) -> list[dict[str, str | int]]:
    """Return prior turns for one workspace/session in chronological order."""
    pool = await _get_pool()
    async with pool.connection() as conn:
        rows = await (await conn.execute(
            """
            SELECT turn, question, answer
            FROM agent_memory
            WHERE workspace_id = %s AND session_id = %s
            ORDER BY turn ASC
            """,
            (workspace_id, session_id),
        )).fetchall()
    return [
        {"turn": row[0], "question": row[1], "answer": row[2]}
        for row in rows
    ]


async def save_turn(
    workspace_id: str,
    session_id: str,
    question: str,
    answer: str,
) -> int:
    """Persist a turn and return its per-session sequence number.

    The next turn is calculated immediately before insertion, avoiding the
    unresolved constant-turn bug that would silently drop every follow-up.
    """
    pool = await _get_pool()
    async with pool.connection() as conn:
        row = await (await conn.execute(
            "SELECT COALESCE(MAX(turn), 0) + 1 FROM agent_memory WHERE session_id = %s",
            (session_id,),
        )).fetchone()
        next_turn = int(row[0])
        await conn.execute(
            """
            INSERT INTO agent_memory (workspace_id, session_id, turn, question, answer)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (session_id, turn) DO NOTHING
            """,
            (workspace_id, session_id, next_turn, question, answer),
        )
    return next_turn
