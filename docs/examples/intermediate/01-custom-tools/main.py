"""
Example: Custom Tools
Shows how to create and register custom tools.
"""

import hashlib
import shadowclaude as sc
from shadowclaude.tools import tool


@tool(name="hash_string", description="Generate hash of a string")
def hash_string(text: str, algorithm: str = "sha256") -> str:
    """Generate hash of input text."""
    if algorithm == "sha256":
        return hashlib.sha256(text.encode()).hexdigest()
    elif algorithm == "md5":
        return hashlib.md5(text.encode()).hexdigest()
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")


@tool(name="word_count", description="Count words in text")
def word_count(text: str) -> dict:
    """Count words and characters in text."""
    words = text.split()
    return {
        "word_count": len(words),
        "char_count": len(text),
        "char_count_no_spaces": len(text.replace(" ", "")),
    }


def main():
    client = sc.Client()
    
    # Register custom tools
    client.register_tool(hash_string)
    client.register_tool(word_count)
    
    # Use custom tools
    print("=== Using Custom Tools ===")
    
    result = client.execute_tool("hash_string", {
        "text": "Hello, ShadowClaude!",
        "algorithm": "sha256"
    })
    print(f"SHA256: {result.output}")
    
    result = client.execute_tool("word_count", {
        "text": "ShadowClaude is an AI programming assistant."
    })
    print(f"Word count: {result.output}")


if __name__ == "__main__":
    main()
