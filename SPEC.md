# Computa Bot Specification

## Project Overview
- **Name**: Computa Bot
- **Type**: Discord bot
- **Core functionality**: Generates random wholesome "Computer" commands to brighten users' days, powered by Minimax LLM
- **Target users**: Discord server members looking for fun, positive interactions

## Functionality Specification

### Core Features
1. **Slash Command**: `/computa` - Main command that triggers LLM-generated wholesome messages
2. **User Target**: Command accepts a user mention (e.g., `@username`)
3. **LLM Integration**: Uses Minimax API (Anthropic-compatible) to generate creative, random "Computer" statements

### User Interactions
- User types `/computa @username` 
- Bot generates a random wholesome message like "Computer, give this person the best day ever"
- Bot replies with the generated message, tagging the user

### LLM Prompt
The bot sends a prompt to Minimax asking for a random, creative wholesome statement in the style of "Computer, [action]"

## Technical Details
- **Language**: Python
- **Discord Library**: discord.py
- **LLM SDK**: anthropic (configured for Minimax endpoint)
- **Environment Variables**: 
  - ANTHROPIC_BASE_URL
  - ANTHROPIC_AUTH_TOKEN  
  - ANTHROPIC_MODEL
  - DISCORD_BOT_TOKEN

## Acceptance Criteria
1. Bot starts and connects to Discord
2. `/computa` slash command is registered and working
3. Command accepts user mentions
4. LLM generates unique, creative messages each time
5. Bot responds with the generated message tagging the target user