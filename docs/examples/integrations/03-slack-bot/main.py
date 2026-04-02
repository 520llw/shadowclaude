"""
Example: Slack Bot
Integration with Slack messaging platform.
"""

import os
import shadowclaude as sc
from flask import Flask, request, jsonify


class SlackBot:
    """ShadowClaude Slack bot."""
    
    def __init__(self):
        self.client = sc.Client()
        self.app = Flask(__name__)
        self.setup_routes()
    
    def setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route("/slack/events", methods=["POST"])
        def handle_events():
            data = request.json
            
            # Handle URL verification
            if data.get("type") == "url_verification":
                return jsonify({"challenge": data["challenge"]})
            
            # Handle messages
            if data.get("type") == "event_callback":
                event = data.get("event", {})
                
                if event.get("type") == "message" and "subtype" not in event:
                    self.handle_message(event)
            
            return jsonify({"status": "ok"})
        
        @self.app.route("/slack/slash", methods=["POST"])
        def handle_slash_command():
            command = request.form.get("command")
            text = request.form.get("text")
            channel_id = request.form.get("channel_id")
            
            response = self.process_command(command, text)
            
            return jsonify({
                "response_type": "in_channel",
                "text": response
            })
    
    def handle_message(self, event: dict):
        """Handle incoming message."""
        text = event.get("text", "")
        user = event.get("user")
        channel = event.get("channel")
        
        # Only respond to mentions
        if f"<@{os.getenv('SLACK_BOT_USER_ID')}>" in text:
            # Remove mention from text
            query = text.replace(f"<@{os.getenv('SLACK_BOT_USER_ID')}>", "").strip()
            
            # Process with ShadowClaude
            response = self.client.query(query)
            
            # Send response (simplified - would use Slack API)
            print(f"To {channel}: {response.content}")
    
    def process_command(self, command: str, text: str) -> str:
        """Process slash commands."""
        
        if command == "/shadowclaude":
            response = self.client.query(text)
            return response.content
        
        elif command == "/explain":
            response = self.client.query(f"Explain: {text}")
            return response.content
        
        elif command == "/code":
            response = self.client.query(f"Generate code: {text}")
            return f"```\n{response.content}\n```"
        
        return "Unknown command"
    
    def run(self, host="0.0.0.0", port=3000):
        """Run the bot."""
        print(f"Slack bot running on http://{host}:{port}")
        self.app.run(host=host, port=port)


def main():
    print("=== Slack Bot Example ===\n")
    
    # Note: This requires actual Slack credentials to run
    # Set these environment variables:
    # - SLACK_BOT_TOKEN
    # - SLACK_BOT_USER_ID
    # - SLACK_SIGNING_SECRET
    
    bot = SlackBot()
    
    # Simulate a command
    print("Simulating /shadowclaude command:")
    response = bot.process_command(
        "/shadowclaude",
        "What are the benefits of async programming?"
    )
    print(f"Response: {response}\n")
    
    # In production, run:
    # bot.run()


if __name__ == "__main__":
    main()
