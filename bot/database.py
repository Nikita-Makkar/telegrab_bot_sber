"""Database layer for persistence."""

import json
import aiosqlite
from typing import List, Optional, Dict, Any
from datetime import datetime

from bot.config import Config


class Database:
    """Database manager for storing chat history and poll results."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialize database manager."""
        self.db_path: str = db_path or Config.DATABASE_PATH

    # ------------------------------
    # Internal helpers
    # ------------------------------

    async def _execute(self, query: str, params: tuple = ()) -> None:
        """Execute a write query and commit changes."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, params)
            await db.commit()

    async def _fetchall(self, query: str, params: tuple = ()) -> List[aiosqlite.Row]:
        """Execute a SELECT query and fetch all rows."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                return await cursor.fetchall()

    async def _fetchone(self, query: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
        """Execute a SELECT query and fetch one row."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                return await cursor.fetchone()

    # ------------------------------
    # Schema initialization
    # ------------------------------

    async def init(self) -> None:
        """Initialize database tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    poll_id TEXT NOT NULL,
                    message_id INTEGER,
                    line_number INTEGER NOT NULL,
                    options TEXT NOT NULL,
                    winner_option INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    UNIQUE(chat_id, poll_id)
                );

                CREATE TABLE IF NOT EXISTS poll_votes (
                    poll_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    option_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (poll_id, user_id)
                );

                CREATE INDEX IF NOT EXISTS idx_chat_history_chat_id 
                    ON chat_history(chat_id);

                CREATE INDEX IF NOT EXISTS idx_chat_history_poll_id 
                    ON chat_history(poll_id);

                CREATE INDEX IF NOT EXISTS idx_poll_votes_poll_id 
                    ON poll_votes(poll_id);
                """
            )
            await db.commit()

    # ------------------------------
    # Chat history
    # ------------------------------

    async def get_chat_history(self, chat_id: int) -> List[Dict[str, Any]]:
        """Get all completed polls for a chat."""
        rows = await self._fetchall(
            """
            SELECT poll_id, line_number, options, winner_option, created_at, closed_at
            FROM chat_history
            WHERE chat_id = ? AND winner_option IS NOT NULL
            ORDER BY line_number ASC
            """,
            (chat_id,),
        )
        return [
            {
                "poll_id": row["poll_id"],
                "line_number": row["line_number"],
                "options": json.loads(row["options"]),
                "winner_option": row["winner_option"],
                "created_at": row["created_at"],
                "closed_at": row["closed_at"],
            }
            for row in rows
        ]

    async def save_poll(
        self,
        chat_id: int,
        poll_id: str,
        line_number: int,
        options: List[str],
        message_id: Optional[int] = None,
    ) -> None:
        """Save a new poll."""
        await self._execute(
            """
            INSERT OR REPLACE INTO chat_history 
            (chat_id, poll_id, message_id, line_number, options, winner_option, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chat_id,
                poll_id,
                message_id,
                line_number,
                json.dumps(options),
                None,
                datetime.now().isoformat(),
            ),
        )

    async def close_poll(self, poll_id: str, winner_option: int) -> None:
        """Mark a poll as closed with a winner."""
        await self._execute(
            """
            UPDATE chat_history
            SET winner_option = ?, closed_at = ?
            WHERE poll_id = ?
            """,
            (winner_option, datetime.now().isoformat(), poll_id),
        )

    async def get_active_poll(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get the active (unclosed) poll for a chat."""
        row = await self._fetchone(
            """
            SELECT poll_id, message_id, line_number, options, created_at
            FROM chat_history
            WHERE chat_id = ? AND winner_option IS NULL
            ORDER BY line_number DESC
            LIMIT 1
            """,
            (chat_id,),
        )
        if not row:
            return None
        return {
            "poll_id": row["poll_id"],
            "message_id": row["message_id"],
            "line_number": row["line_number"],
            "options": json.loads(row["options"]),
            "created_at": row["created_at"],
        }

    # ------------------------------
    # Votes
    # ------------------------------

    async def save_vote(self, poll_id: str, user_id: int, option_id: int) -> None:
        """Save or update a vote."""
        await self._execute(
            """
            INSERT OR REPLACE INTO poll_votes (poll_id, user_id, option_id, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (poll_id, user_id, option_id, datetime.now().isoformat()),
        )

    async def get_vote_counts(self, poll_id: str) -> Dict[int, int]:
        """Get vote counts for each option in a poll."""
        rows = await self._fetchall(
            """
            SELECT option_id, COUNT(*) as count
            FROM poll_votes
            WHERE poll_id = ?
            GROUP BY option_id
            """,
            (poll_id,),
        )
        return {row["option_id"]: row["count"] for row in rows}

    # ------------------------------
    # Cleanup and utility
    # ------------------------------

    async def clear_chat_history(self, chat_id: int) -> None:
        """Clear all history for a chat."""
        rows = await self._fetchall(
            "SELECT poll_id FROM chat_history WHERE chat_id = ?", (chat_id,)
        )
        poll_ids = [row["poll_id"] for row in rows]

        async with aiosqlite.connect(self.db_path) as db:
            if poll_ids:
                placeholders = ",".join("?" * len(poll_ids))
                await db.execute(
                    f"DELETE FROM poll_votes WHERE poll_id IN ({placeholders})",
                    poll_ids,
                )
            await db.execute("DELETE FROM chat_history WHERE chat_id = ?", (chat_id,))
            await db.commit()

    async def get_next_line_number(self, chat_id: int) -> int:
        """Get the next line number for a chat."""
        row = await self._fetchone(
            "SELECT MAX(line_number) as max_line FROM chat_history WHERE chat_id = ?",
            (chat_id,),
        )
        max_line = row["max_line"] if row and row["max_line"] is not None else 0
        return max_line + 1
