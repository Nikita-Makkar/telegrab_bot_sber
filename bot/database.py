"""Database layer for persistence."""

import json
import aiosqlite
from typing import List, Optional, Dict, Any
from datetime import datetime

from bot.config import Config


class Database:
    """Database manager for storing chat history and poll results."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH

    async def init(self) -> None:
        """Initialize database tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
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
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS poll_votes (
                    poll_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    option_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (poll_id, user_id)
                )
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_history_chat_id 
                ON chat_history(chat_id)
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_history_poll_id 
                ON chat_history(poll_id)
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_poll_votes_poll_id 
                ON poll_votes(poll_id)
                """
            )
            await db.commit()

    async def get_chat_history(self, chat_id: int) -> List[Dict[str, Any]]:
        """Get all completed polls for a chat."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT poll_id, line_number, options, winner_option, created_at, closed_at
                FROM chat_history
                WHERE chat_id = ? AND winner_option IS NOT NULL
                ORDER BY line_number ASC
                """,
                (chat_id,),
            ) as cursor:
                rows = await cursor.fetchall()
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
        message_id: int = None,
    ) -> None:
        """Save a new poll."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
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
            await db.commit()

    async def close_poll(
        self,
        poll_id: str,
        winner_option: int,
    ) -> None:
        """Mark a poll as closed with a winner."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE chat_history
                SET winner_option = ?, closed_at = ?
                WHERE poll_id = ?
                """,
                (winner_option, datetime.now().isoformat(), poll_id),
            )
            await db.commit()

    async def get_active_poll(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get the active (unclosed) poll for a chat."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT poll_id, message_id, line_number, options, created_at
                FROM chat_history
                WHERE chat_id = ? AND winner_option IS NULL
                ORDER BY line_number DESC
                LIMIT 1
                """,
                (chat_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "poll_id": row["poll_id"],
                        "message_id": row["message_id"],
                        "line_number": row["line_number"],
                        "options": json.loads(row["options"]),
                        "created_at": row["created_at"],
                    }
                return None

    async def save_vote(
        self,
        poll_id: str,
        user_id: int,
        option_id: int,
    ) -> None:
        """Save or update a vote."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO poll_votes (poll_id, user_id, option_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (poll_id, user_id, option_id, datetime.now().isoformat()),
            )
            await db.commit()

    async def get_vote_counts(self, poll_id: str) -> Dict[int, int]:
        """Get vote counts for each option in a poll."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """
                SELECT option_id, COUNT(*) as count
                FROM poll_votes
                WHERE poll_id = ?
                GROUP BY option_id
                """,
                (poll_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}

    async def clear_chat_history(self, chat_id: int) -> None:
        """Clear all history for a chat."""
        async with aiosqlite.connect(self.db_path) as db:
            # First get all poll_ids to delete votes
            async with db.execute(
                "SELECT poll_id FROM chat_history WHERE chat_id = ?", (chat_id,)
            ) as cursor:
                poll_ids = [row[0] for row in await cursor.fetchall()]

            # Delete votes for these polls
            if poll_ids:
                placeholders = ",".join("?" * len(poll_ids))
                await db.execute(
                    f"DELETE FROM poll_votes WHERE poll_id IN ({placeholders})",
                    poll_ids,
                )

            # Delete chat history
            await db.execute("DELETE FROM chat_history WHERE chat_id = ?", (chat_id,))
            await db.commit()

    async def get_next_line_number(self, chat_id: int) -> int:
        """Get the next line number for a chat."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT MAX(line_number) as max_line FROM chat_history WHERE chat_id = ?",
                (chat_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return (row[0] or 0) + 1
