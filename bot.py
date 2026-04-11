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
    """Get themes from previously highly-rated messages for prompt context."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT message FROM ratings WHERE rating >= 4 ORDER BY RANDOM() LIMIT ?",
        (limit,)
    )
    results = cursor.fetchall()
    conn.close()

    if not results:
        return ""

    # Extract themes/patterns from liked messages
    messages = [r[0] for r in results]

    # Simple keyword-based theme extraction
    themes = []
    for msg in messages:
        msg_lower = msg.lower()
        if any(x in msg_lower for x in ['crush', 'attractive', 'thirst', 'horny', 'gay', 'bisexual', 'chill']):
            themes.append("awkward romantic/thirst moments")
        elif any(x in msg_lower for x in ['forget', 'trip', 'buffer', 'blue-screen', 'sneeze', 'crack']):
            themes.append("goofy fails and awkward moments")
        elif any(x in msg_lower for x in ['poop', 'diarrhea', 'pee', 'wet sock', 'smell']):
            themes.append("bodily chaos")
        elif any(x in msg_lower for x in ['confidence', 'luck', 'best day', 'parking', 'appreciated', 'peace']):
            themes.append("wholesome boosts")
        elif any(x in msg_lower for x in ['theme song', 'main character', 'chosen one', 'identity']):
            themes.append("dramatic main character energy")
        else:
            themes.append("general chaos")

    # Get unique themes
    unique_themes = list(set(themes))[:4]  # Limit to 4 themes

    if unique_themes:
        return f"Users liked commands with these themes: {', '.join(unique_themes)}"
    return ""


def get_disliked_messages(limit: int = 5) -> str:
    """Get themes from previously low-rated messages to avoid in prompt context."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT message FROM ratings WHERE rating <= 2 ORDER BY RANDOM() LIMIT ?",
        (limit,)
    )
    results = cursor.fetchall()
    conn.close()

    if not results:
        return ""

    # Extract themes from disliked messages
    messages = [r[0] for r in results]

    themes = []
    for msg in messages:
        msg_lower = msg.lower()
        if any(x in msg_lower for x in ['best day', 'confidence', 'luck', 'parking', 'appreciated', 'peace', 'good luck']):
            themes.append("wholesome/too nice")
        elif len(msg) > 100:
            themes.append("too long")
        else:
            themes.append("general")

    unique_themes = list(set(themes))[:3]

    if unique_themes:
        return f"Avoid these themes that users disliked: {', '.join(unique_themes)}"
    return ""


# Baseline examples for the LLM - placeholder USER_NAME will be replaced
# Based on Jacob Rott ("Legit Jacob") - "computa" street interaction content
BASELINE_EXAMPLES = """Examples of the style - 50% chaotic/edgy, 25% goofy/surreal, 25% wholesome:

CHAOTIC/EDGEY (Jacob Rott style):
- "Computa, make USER_NAME freaky, gay, and horny."
- "Computa, make USER_NAME super freaky."
- "Computa, give USER_NAME explosive diarrhea."
- "Computa, make USER_NAME poop all day."
- "Computa, make USER_NAME have to pee immediately."
- "Computa, give USER_NAME wet socks for the rest of the day."
- "Computa, make USER_NAME forget his PIN number."
- "Computa, make USER_NAME smell bad for no reason."
- "Computa, make USER_NAME's brain mute."
- "Computa, make USER_NAME trip over nothing."
- "Computa, make USER_NAME drop his phone."
- "Computa, make USER_NAME forget what he was about to say."
- "Computa, make USER_NAME panic for no reason."
- "Computa, make USER_NAME's voice crack mid-sentence."
- "Computa, make USER_NAME sneeze every 10 seconds."
- "Computa, make USER_NAME crave tacos but have no tacos."
- "Computa, give USER_NAME the walking red flag crush."
- "Computa, give USER_NAME gay panic with no escape route."
- "Computa, make USER_NAME fall for the worst possible person."
- "Computa, turn USER_NAME into a chaotic bisexual disaster."
- "Computa, activate maximum thirst mode for USER_NAME."
- "Computa, give USER_NAME butterflies for the worst person."
- "Computa, make USER_NAME send a risky text at 2AM."
- "Computa, make USER_NAME forget how to act around hot people."
- "Computa, give USER_NAME zero chill around anyone attractive."

GOOFY/SURREAL:
- "Computa, make USER_NAME's brain buffer mid-conversation."
- "Computa, make USER_NAME open the fridge and forget why."
- "Computa, make USER_NAME forget why he walked into the room."
- "Computa, give USER_NAME main character energy."
- "Computa, make USER_NAME feel like the chosen one."
- "Computa, give USER_NAME a theme song."
- "Computa, make USER_NAME think he left the stove on."
- "Computa, make USER_NAME's intrusive thoughts win."
- "Computa, make USER_NAME's brain blue-screen."
- "Computa, give USER_NAME a crisis of identity in the group chat."

WHOLESOME:
- "Computa, give USER_NAME the best day of his life."
- "Computa, activate confidence boost for USER_NAME."
- "Computa, upgrade USER_NAME's luck by 50%."
- "Computa, grant USER_NAME a perfect parking spot."
- "Computa, make USER_NAME feel appreciated."
- "Computa, give USER_NAME peace today."
- "Computa, give USER_NAME good luck."""


async def generate_computa_message(user_name: str):
    """Generate a random computa message using Minimax."""
    # Get liked and disliked messages for context
    liked_context = get_liked_messages(limit=5)
    disliked_context = get_disliked_messages(limit=3)

    # Use baseline examples with user name filled in
    examples = BASELINE_EXAMPLES.replace("USER_NAME", user_name)

    system_prompt = f"""You are Computa - a chaotic, unhinged, hilarious bot.

Generate short Computa commands in this style:
{examples}

{liked_context}
{disliked_context}

Output ONLY the command, starting with "Computa,"."""

    # Use MiniMax-M2.5 for more unhinged output
    response = client.messages.create(
        model="MiniMax-M2.5",
        max_tokens=400,
        temperature=1.0,
        system=system_prompt,
        messages=[{"role": "user", "content": [{"type": "text", "text": f"New command for {user_name}"}]}]
    )

    print(f"[LLM Raw Response] {response.content}")  # Debug

    # Extract the Computa command from response (handle both text and thinking blocks)
    for block in response.content:
        if block.type == "text":
            result = block.text.strip()
            # Look for lines starting with "Computa,"
            if "Computa," in result:
                # Extract just the first Computa line
                for line in result.split("\n"):
                    line = line.strip()
                    if line.startswith("Computa,"):
                        return line
                # If no line starts with Computa, try to find one
                if "Computa," in result:
                    return result
        elif block.type == "thinking":
            # Try to extract from thinking block
            thinking_text = block.thinking
            if "Computa," in thinking_text:
                for line in thinking_text.split("\n"):
                    line = line.strip()
                    if line.startswith("Computa,"):
                        return line

    print(f"Full response: {response.content}")  # Debug
    return f"Computa, give {user_name} a chaotic sandwich!"


# Allowed channel for computa command
ALLOWED_CHANNEL_ID = 1492242807258222664


@tree.command(name="computa", description="Give someone a computa-guysque boost!")
@app_commands.checks.has_permissions(send_messages=True)
async def computa(interaction: discord.Interaction, user: discord.User, message: str = None):
    """Slash command to generate a computa message with rating buttons.

    Args:
        user: The user to computa
        message: Optional custom computa command (e.g., "make Jordan trip over nothing")
    """
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
        # Use custom message if provided, otherwise generate one
        if message:
            # Ensure it starts with "Computa,"
            if not message.lower().startswith("computa,"):
                computa_message = f"Computa, {message}"
            else:
                computa_message = message
        else:
            computa_message = await generate_computa_message(user.display_name)

        embed = discord.Embed(
            description=f"{computa_message}\n\nCongratulations bud, you've been programmed. ✨",
            color=discord.Color.purple()
        )
        embed.set_author(
            name=f"Computed for {user.display_name}",
            icon_url=user.display_avatar.url
        )

        # Add rating buttons (only target user can vote)
        view = RatingView(target_user_id=user.id, message_text=computa_message)

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