import os
import discord
from discord import app_commands
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


async def generate_computa_message(user_name: str):
    """Generate a random wholesome 'Computer' message using Minimax."""
    prompt = f"""Generate a short, fun, wholesome message in the style of someone giving commands to a computer/AI assistant.

Examples of the style:
- "Computer, give {user_name} the best day of their life."
- "Computer, activate confidence boost for {user_name}."
- "Computer, upgrade {user_name}'s luck by 50%."
- "Computer, grant {user_name} a perfect parking spot."

Generate ONE new, creative, wholesome message in this style. Keep it short (1-2 sentences). Make it funny, heartwarming, or inspiring. Don't include quotes in your response. Start with "Computa,"."""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=50,
        messages=[{"role": "user", "content": prompt}]
    )

    # Handle both text and thinking blocks from Minimax
    for block in response.content:
        print(f"Block type: {block.type}")  # Debug
        if block.type == "text":
            return block.text.strip()
    print(f"Full response: {response.content}")  # Debug
    return "Computa, give this person a surprise!"


# Allowed channels for computa command
ALLOWED_CHANNEL_IDS = [1492242807258222664, 1492245748442464286]


@tree.command(name="computa", description="Give someone a computa-guysque boost!")
@app_commands.checks.has_permissions(send_messages=True)
async def computa(interaction: discord.Interaction, user: discord.User):
    """Slash command to generate a wholesome computa message for a user."""
    # Check if command is used in an allowed channel
    if interaction.channel_id not in ALLOWED_CHANNEL_IDS:
        await interaction.response.send_message(
            f"❌ This command only works in <#{ALLOWED_CHANNEL_IDS[0]}> or <#{ALLOWED_CHANNEL_IDS[1]}>",
            ephemeral=True
        )
        return

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

        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Oops! Something went wrong: {str(e)}")


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