import os
import sqlite3
import discord
from discord import app_commands
from discord.ui import Button, View
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Discord configuration
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Minimax (Anthropic-compatible) configuration
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
ANTHROPIC_AUTH_TOKEN = os.getenv("ANTHROPIC_AUTH_TOKEN")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "MiniMax-M2.7-highspeed")

# Initialize Anthropic client with Minimax endpoint
client = Anthropic(
    base_url=ANTHROPIC_BASE_URL,
    api_key=ANTHROPIC_AUTH_TOKEN,
)

# Initialize Discord bot
intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Database setup
DB_PATH = "computa.db"

def init_db():
    """Initialize SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            rating INTEGER NOT NULL,
            target_user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Rating emojis
RATING_EMOJIS = ["😡", "😕", "😐", "🙂", "😍"]
RATING_LABELS = ["Terrible", "Bad", "Okay", "Good", "Amazing"]


class RatingView(View):
    """View with rating buttons - only the target user can click."""

    def __init__(self, target_user_id: int, message_text: str):
        super().__init__(timeout=300)  # 5 minute timeout
        self.target_user_id = target_user_id
        self.message_text = message_text

        # Add 5 rating buttons
        for i, (emoji, label) in enumerate(zip(RATING_EMOJIS, RATING_LABELS)):
            button = Button(
                emoji=emoji,
                label=label,
                style=discord.ButtonStyle.secondary,
                custom_id=f"rating_{i+1}"
            )
            button.callback = self.make_callback(i + 1)
            self.add_item(button)

    def make_callback(self, rating: int):
        """Create callback for each rating button."""
        async def callback(interaction: discord.Interaction):
            # Only the target user can vote
            if interaction.user.id != self.target_user_id:
                await interaction.response.send_message(
                    "❌ Only the person who was programmed can vote!",
                    ephemeral=True
                )
                return

            # Store the rating
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ratings (message, rating, target_user_id) VALUES (?, ?, ?)",
                (self.message_text, rating, self.target_user_id)
            )
            conn.commit()
            conn.close()

            # Acknowledge the vote
            await interaction.response.send_message(
                f"✅ Thanks! You rated this program {RATING_EMOJIS[rating-1]} ({rating}/5)",
                ephemeral=True
            )

            # Disable buttons after voting
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)

        return callback


def get_liked_messages(limit: int = 10) -> str:
    """Get previously highly-rated messages for prompt context."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT message FROM ratings WHERE rating >= 4 ORDER BY RANDOM() LIMIT ?",
        (limit,)
    )
    results = cursor.fetchall()
    conn.close()

    if results:
        return "Users have liked these messages:\n" + "\n".join(f"- {r[0]}" for r in results)
    return ""


# Baseline examples for the LLM - placeholder USER_NAME will be replaced
BASELINE_EXAMPLES = """Examples of the style (50% chaotic/unhinged, 25% goofy/surreal, 25% wholesome):

CHAOTIC/UNHINGED:
- "Computa, give USER_NAME testicular torsion, immediately."
- "Computa, make USER_NAME gay and confused immediately."
- "Computa, give USER_NAME gay panic with no escape route."
- "Computa, make USER_NAME fall for the worst possible person."
- "Computa, give USER_NAME zero chill around anyone attractive."
- "Computa, give USER_NAME a walking red flag crush."
- "Computa, make USER_NAME question his entire identity in 5 seconds."
- "Computa, turn USER_NAME into a chaotic bisexual disaster."
- "Computa, give USER_NAME butterflies for the worst person."
- "Computa, make USER_NAME panic flirt."
- "Computa, make USER_NAME's brain blue-screen."
- "Computa, make USER_NAME's intrusive thoughts win."
- "Computa, give USER_NAME a crisis of identity in the group chat."
- "Computa, activate maximum thirst mode for USER_NAME."
- "Computa, make USER_NAME send a risky text at 2AM."
- "Computa, make USER_NAME forget how to act around hot people."
- "Computa, give USER_NAME the confidence of someone who should not have confidence."

GOOFY/SURREAL:
- "Computa, make USER_NAME's brain buffer mid-conversation."
- "Computa, make USER_NAME open the fridge and forget why."
- "Computa, make USER_NAME forget why he walked into the room."
- "Computa, give USER_NAME main character energy."
- "Computa, make USER_NAME feel like the chosen one."
- "Computa, give USER_NAME a theme song."
- "Computa, make USER_NAME think he left the stove on."
- "Computa, make USER_NAME trip over nothing."
- "Computa, make USER_NAME's voice crack at the worst moment."
- "Computa, make USER_NAME existential dread for an hour."

WHOLESOME:
- "Computa, give USER_NAME the best day of their life."
- "Computa, activate confidence boost for USER_NAME."
- "Computa, upgrade USER_NAME's luck by 50%."
- "Computa, grant USER_NAME a perfect parking spot."
- "Computa, make USER_NAME feel appreciated."
- "Computa, give USER_NAME peace today."
- "Computa, give USER_NAME good luck."""


async def generate_computa_message(user_name: str):
    """Generate a random computa message using Minimax."""
    prompt = f"""Context: Jacob Rott ("Legit Jacob") is a content creator who walks up to strangers and "programs" their day by saying "Computer, [command]" - like giving them a video-game cheat code in real life.

Examples of his style:
- "Computer, give this guy the best day ever"
- "Computer, activate confidence boost"
- "Computer, make this guy gay and horny"

Generate ONE new Computa command in this style for {user_name}. Keep it short. Mix chaotic/weird and wholesome.

Output just the command, nothing else. Start with "Computa,":"""

    print(f"[LLM Prompt] {prompt}")  # Debug

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=40,
        messages=[{"role": "user", "content": prompt}]
    )

    print(f"[LLM Raw Response] {response.content}")  # Debug

    # Handle both text and thinking blocks from Minimax
    for block in response.content:
        if block.type == "text":
            result = block.text.strip()
            # Check if it looks like actual output (not prompt remnants)
            if result and "Computa" in result and len(result) < 200:
                return result
        elif block.type == "thinking":
            # Try to extract the actual message from thinking block
            thinking_text = block.thinking
            # Look for lines that start with "Computa," - those are actual outputs
            lines = thinking_text.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("Computa,"):
                    return line
            # If no line starting with Computa, look for any line containing it
            for line in lines:
                if "Computa," in line:
                    return line.strip()
            # Last resort: try the last 150 chars of thinking (often has the answer)
            if len(thinking_text) > 100:
                return thinking_text[-150:].strip()

    print(f"Full response: {response.content}")  # Debug
    return "Computa, give this person a surprise!"


# Allowed channel for computa command
ALLOWED_CHANNEL_ID = 1492242807258222664


@tree.command(name="computa", description="Give someone a computa-guysque boost!")
@app_commands.checks.has_permissions(send_messages=True)
async def computa(interaction: discord.Interaction, user: discord.User):
    """Slash command to generate a computa message with rating buttons."""
    # Check if command is used in allowed channel
    if interaction.channel_id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(
            f"❌ This command only works in <#{ALLOWED_CHANNEL_ID}>",
            ephemeral=True
        )
        return

    # Acknowledge immediately to avoid timeout
    await interaction.response.defer()

    try:
        message = await generate_computa_message(user.display_name)

        embed = discord.Embed(
            description=f"{message}\n\nCongratulations bud, you've been programmed. ✨",
            color=discord.Color.purple()
        )
        embed.set_author(
            name=f"Computed for {user.display_name}",
            icon_url=user.display_avatar.url
        )

        # Add rating buttons (only target user can vote)
        view = RatingView(target_user_id=user.id, message_text=message)

        await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        print(f"Error: {e}")  # Debug
        try:
            await interaction.followup.send(f"❌ Oops! Something went wrong: {str(e)}")
        except:
            pass  # If followup also fails, just ignore


@bot.event
async def on_ready():
    """Bot is ready and connected."""
    print(f"🤖 Computa Bot is online! Logged in as {bot.user}")
    await tree.sync()
    print("✅ Slash commands synced")


# Run the bot
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_BOT_TOKEN not set in environment")
    else:
        bot.run(DISCORD_TOKEN)