"""
Example: Telegram Bot
Integration with Telegram messaging platform.
"""

import os
import asyncio
import shadowclaude as sc


class TelegramBot:
    """ShadowClaude Telegram bot."""
    
    def __init__(self):
        self.client = sc.Client()
        self.allowed_users = set()  # Set of allowed user IDs
    
    async def handle_start(self, update):
        """Handle /start command."""
        user_id = update.effective_user.id
        
        await update.message.reply_text(
            "👋 Welcome to ShadowClaude Bot!\n\n"
            "I can help you with:\n"
            "• Code explanations\n"
            "• Bug fixes\n"
            "• Code generation\n"
            "• And much more!\n\n"
            "Just send me your question or code."
        )
    
    async def handle_message(self, update, context):
        """Handle incoming messages."""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Check authorization
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text(
                "⛔ You are not authorized to use this bot."
            )
            return
        
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        # Process with ShadowClaude
        try:
            response = self.client.query(message_text)
            
            # Send response
            await update.message.reply_text(response.content)
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ Error: {str(e)}"
            )
    
    async def handle_code_command(self, update, context):
        """Handle /code command."""
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "Usage: /code <language> <description>\n"
                "Example: /code python function to reverse string"
            )
            return
        
        language = args[0]
        description = " ".join(args[1:])
        
        await update.message.chat.send_action(action="typing")
        
        response = self.client.query(
            f"Generate {language} code: {description}"
        )
        
        # Format as code block
        formatted = f"```{language}\n{response.content}\n```"
        
        await update.message.reply_text(formatted)
    
    async def handle_explain_command(self, update, context):
        """Handle /explain command."""
        # In real usage, this would handle code from replies
        if update.message.reply_to_message:
            code = update.message.reply_to_message.text
            
            await update.message.chat.send_action(action="typing")
            
            response = self.client.query(
                f"Explain this code:\n```\n{code}\n```"
            )
            
            await update.message.reply_text(response.content)
        else:
            await update.message.reply_text(
                "Reply to a message containing code to explain it."
            )
    
    async def handle_image(self, update, context):
        """Handle image messages (for code screenshots)."""
        await update.message.reply_text(
            "📷 I can see the image. In the full version, "
            "I would use OCR to extract and analyze any code in it."
        )
    
    def run(self, token: str):
        """Run the bot."""
        # In production, this would use python-telegram-bot
        print(f"Telegram bot would start with token: {token[:10]}...")


def main():
    print("=== Telegram Bot Example ===\n")
    
    # Note: This requires actual Telegram Bot Token to run
    # Set TELEGRAM_BOT_TOKEN environment variable
    
    bot = TelegramBot()
    
    # Simulate a command
    print("Simulating /code command:")
    
    class MockUpdate:
        class effective_user:
            id = 123456
        
        class message:
            @staticmethod
            async def reply_text(text):
                print(f"Bot: {text[:200]}...")
            
            class chat:
                @staticmethod
                async def send_action(action):
                    print(f"Action: {action}")
    
    class MockContext:
        args = ["python", "function", "to", "calculate", "fibonacci"]
    
    asyncio.run(bot.handle_code_command(MockUpdate(), MockContext()))


if __name__ == "__main__":
    main()
