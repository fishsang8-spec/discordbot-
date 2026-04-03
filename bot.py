import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import random

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

DB = "database.db"

# ---------- БАЗА ----------
async def setup_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            guild_id INTEGER,
            xp INTEGER,
            level INTEGER,
            PRIMARY KEY (user_id, guild_id)
        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS level_roles (
            guild_id INTEGER,
            level INTEGER,
            role_id INTEGER
        )
        """)

        await db.commit()

# ---------- READY ----------
@bot.event
async def on_ready():
    await setup_db()
    await bot.tree.sync()
    print(f"Готов: {bot.user}")

# ---------- XP ----------
async def add_xp(member, guild):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT xp, level FROM users WHERE user_id=? AND guild_id=?",
            (member.id, guild.id)
        )
        row = await cursor.fetchone()

        xp_gain = random.randint(5, 15)

        if not row:
            xp = xp_gain
            level = 1
            await db.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?)",
                (member.id, guild.id, xp, level)
            )
        else:
            xp, level = row
            xp += xp_gain
            new_level = int(xp ** 0.25)

            if new_level > level:
                level = new_level

                # 🎖️ Проверка ролей
                cursor = await db.execute(
                    "SELECT role_id FROM level_roles WHERE guild_id=? AND level=?",
                    (guild.id, level)
                )
                role_data = await cursor.fetchone()

                if role_data:
                    role = guild.get_role(role_data[0])
                    if role:
                        await member.add_roles(role)

                return True, level

            await db.execute(
                "UPDATE users SET xp=?, level=? WHERE user_id=? AND guild_id=?",
                (xp, level, member.id, guild.id)
            )

        await db.commit()
    return False, None

# ---------- MESSAGE ----------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    leveled, level = await add_xp(message.author, message.guild)

    if leveled:
        await message.channel.send(
            f"🎉 {message.author.mention} достиг уровня {level}!"
        )

    await bot.process_commands(message)

# ---------- SLASH КОМАНДЫ ----------

@bot.tree.command(name="rank", description="Посмотреть уровень")
async def rank(interaction: discord.Interaction):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT xp, level FROM users WHERE user_id=? AND guild_id=?",
            (interaction.user.id, interaction.guild.id)
        )
        row = await cursor.fetchone()

    if not row:
        await interaction.response.send_message("Нет данных")
        return

    xp, level = row

    embed = discord.Embed(
        title="📊 Твой уровень",
        color=discord.Color.blue()
    )
    embed.add_field(name="Уровень", value=level)
    embed.add_field(name="XP", value=xp)

    await interaction.response.send_message(embed=embed)

# 🏆 Лидерборд
@bot.tree.command(name="top", description="Топ участников")
async def top(interaction: discord.Interaction):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("""
            SELECT user_id, xp, level
            FROM users
            WHERE guild_id=?
            ORDER BY xp DESC
            LIMIT 10
        """, (interaction.guild.id,))
        rows = await cursor.fetchall()

    text = ""
    for i, (uid, xp, lvl) in enumerate(rows, 1):
        user = interaction.guild.get_member(uid)
        text += f"{i}. {user} — lvl {lvl} ({xp} XP)\n"
        embed = discord.Embed(
        title="🏆 Лидерборд",
        description=text,
        color=discord.Color.gold()
    )

    await interaction.response.send_message(embed=embed)

# 🎖️ Назначить роль за уровень
@bot.tree.command(name="setrole", description="Роль за уровень")
@app_commands.describe(level="Уровень", role="Роль")
async def setrole(interaction: discord.Interaction, level: int, role: discord.Role):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO level_roles VALUES (?, ?, ?)",
            (interaction.guild.id, level, role.id)
        )
        await db.commit()

    await interaction.response.send_message(f"Роль {role.name} выдается на уровне {level}")