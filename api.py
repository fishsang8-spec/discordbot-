from fastapi import FastAPI
import aiosqlite

app = FastAPI()
DB = "database.db"

@app.get("/guild/{guild_id}")
async def get_config(guild_id: int):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT welcome_channel FROM config WHERE guild_id=?",
            (guild_id,)
        )
        row = await cursor.fetchone()

    return {"welcome_channel": row[0] if row else None}


@app.post("/guild/{guild_id}")
async def set_config(guild_id: int, data: dict):
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        INSERT OR REPLACE INTO config VALUES (?, ?, 1)
        """, (guild_id, data["channel"]))
        await db.commit()

    return {"status": "ok"}