"""
Example: VS Code Extension
Integration with VS Code editor.
"""

# This example shows the Python backend for a VS Code extension
# The actual extension would be written in TypeScript

import json
import shadowclaude as sc


class VSCodeIntegration:
    """Backend for VS Code extension."""
    
    def __init__(self):
        self.client = sc.Client()
    
    def handle_command(self, command: str, args: dict) -> dict:
        """Handle commands from VS Code."""
        handlers = {
            "explain": self.explain_code,
            "refactor": self.refactor_code,
            "generate": self.generate_code,
            "review": self.review_code,
        }
        
        handler = handlers.get(command)
        if handler:
            return handler(args)
        return {"error": f"Unknown command: {command}"}
    
    def explain_code(self, args: dict) -> dict:
        """Explain selected code."""
        code = args.get("code", "")
        language = args.get("language", "")
        
        response = self.client.query(
            f"Explain this {language} code:\n\n```\n{code}\n```"
        )
        
        return {
            "explanation": response.content,
            "actions": ["insert_comment", "copy"]
        }
    
    def refactor_code(self, args: dict) -> dict:
        """Refactor selected code."""
        code = args.get("code", "")
        goal = args.get("goal", "improve readability")
        
        response = self.client.query(
            f"Refactor this code to {goal}:\n\n```\n{code}\n```"
        )
        
        return {
            "refactored_code": response.content,
            "changes": self.extract_changes(code, response.content),
        }
    
    def generate_code(self, args: dict) -> dict:
        """Generate code from description."""
        description = args.get("description", "")
        language = args.get("language", "python")
        
        response = self.client.query(
            f"Generate {language} code for: {description}"
        )
        
        return {
            "code": response.content,
            "language": language,
        }
    
    def review_code(self, args: dict) -> dict:
        """Review code for issues."""
        code = args.get("code", "")
        
        response = self.client.query(
            f"Review this code for bugs, security issues, and improvements:\n\n```\n{code}\n```"
        )
        
        return {
            "review": response.content,
            "severity": "info",
        }
    
    def extract_changes(self, original: str, refactored: str) -> list:
        """Extract specific changes made."""
        # Simplified change detection
        return [
            {"type": "improvement", "description": "Code structure improved"}
        ]


def main():
    print("=== VS Code Extension Backend ===\n")
    
    integration = VSCodeIntegration()
    
    # Simulate VS Code commands
    commands = [
        {
            "command": "explain",
            "args": {
                "code": "def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)",
                "language": "python"
            }
        },
        {
            "command": "generate",
            "args": {
                "description": "function to reverse a string",
                "language": "python"
            }
        }
    ]
    
    for cmd in commands:
        print(f"Command: {cmd['command']}")
        result = integration.handle_command(cmd['command'], cmd['args'])
        print(f"Result: {json.dumps(result, indent=2)}\n")


if __name__ == "__main__":
    main()
