"""
Example: Discord Bot
Integration with Discord messaging platform.
"""

import os
import asyncio
import shadowclaude as sc


class DiscordBot:
    """ShadowClaude Discord bot."""
    
    def __init__(self):
        self.client = sc.Client()
        self.prefix = "!sc "
    
    async def on_ready(self):
        """Called when bot is ready."""
        print(f"Discord bot logged in as {self.user}")
    
    async def on_message(self, message):
        """Handle incoming messages."""
        # Ignore own messages
        if message.author == self.user:
            return
        
        # Check for prefix
        if message.content.startswith(self.prefix):
            query = message.content[len(self.prefix):].strip()
            
            # Show typing indicator
            async with message.channel.typing():
                # Process with ShadowClaude
                response = self.client.query(query)
            
            # Send response (split if too long)
            content = response.content
            if len(content) > 2000:
                # Discord message limit
                for i in range(0, len(content), 1990):
                    await message.channel.send(content[i:i+1990])
            else:
                await message.channel.send(content)
        
        # Handle @mentions
        elif self.user.mentioned_in(message):
            # Remove mention from content
            content = message.content
            for mention in message.mentions:
                content = content.replace(f"<@{mention.id}", "")
            
            query = content.strip()
            
            async with message.channel.typing():
                response = self.client.query(query)
            
            await message.reply(response.content)
    
    async def handle_slash_command(self, interaction, command: str, **kwargs):
        """Handle Discord slash commands."""
        
        await interaction.response.defer()
        
        if command == "ask":
            question = kwargs.get("question", "")
            response = self.client.query(question)
            await interaction.followup.send(response.content)
        
        elif command == "code":
            description = kwargs.get("description", "")
            language = kwargs.get("language", "python")
            
            response = self.client.query(
                f"Generate {language} code: {description}"
            )
            
            await interaction.followup.send(
                f"```{language}\n{response.content}\n```"
            )
        
        elif command == "explain":
            code = kwargs.get("code", "")
            response = self.client.query(f"Explain this code:\n```\n{code}\n```")
            await interaction.followup.send(response.content)
    
    def run(self, token: str):
        """Run the bot."""
        # In production, this would use discord.py
        print(f"Discord bot would start with token: {token[:10]}...")


def main():
    print("=== Discord Bot Example ===\n")
    
    # Note: This requires actual Discord credentials to run
    # Set DISCORD_BOT_TOKEN environment variable
    
    bot = DiscordBot()
    
    # Simulate a message
    class MockMessage:
        def __init__(self, content):
            self.content = content
            self.author = "user123"
        
        async def reply(self, content):
            print(f"Reply: {content[:100]}...")
    
    print("Simulating message with prefix:")
    message = MockMessage("!sc What is Rust?")
    
    # Simulate processing
    if message.content.startswith(bot.prefix):
        query = message.content[len(bot.prefix):].strip()
        response = bot.client.query(query)
        print(f"Response: {response.content[:200]}...\n")


if __name__ == "__main__":
    main()
