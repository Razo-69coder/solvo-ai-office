import asyncio
import asyncpg
from typing import Optional

from config import DATABASE_URL

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None or _pool._closed:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=0, max_size=3)
    return _pool


async def init_db():
    pool = await get_pool()
    connected = False
    for attempt in range(10):
        try:
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
            connected = True
            break
        except Exception as e:
            print(f"DB connection attempt {attempt+1}/10 failed: {e}")
            if attempt < 9:
                await asyncio.sleep(10)
    if not connected:
        print("WARNING: DB not reachable, continuing anyway")
        return
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS office_tasks (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                original_request TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS office_results (
                id SERIAL PRIMARY KEY,
                task_id INTEGER REFERENCES office_tasks(id),
                agent_name TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
    print("DB tables ready")


async def create_task(user_id: int, request_text: str) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO office_tasks (user_id, original_request, status) VALUES ($1, $2, 'pending') RETURNING id",
            user_id, request_text
        )
        return row["id"]


async def update_task_status(task_id: int, status: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE office_tasks SET status=$1 WHERE id=$2",
            status, task_id
        )


async def save_result(task_id: int, agent_name: str, result: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO office_results (task_id, agent_name, result) VALUES ($1, $2, $3)",
            task_id, agent_name, result
        )


async def get_recent_tasks(user_id: int, limit: int = 3) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, original_request, status, created_at FROM office_tasks WHERE user_id=$1 ORDER BY created_at DESC LIMIT $2",
            user_id, limit
        )
        return [dict(r) for r in rows]


async def get_results(task_id: int) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT agent_name, result FROM office_results WHERE task_id=$1 ORDER BY created_at ASC",
            task_id
        )
        return [dict(r) for r in rows]
