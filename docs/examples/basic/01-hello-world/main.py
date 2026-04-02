"""
Example: Hello World
Basic usage of ShadowClaude client.
"""

import shadowclaude as sc


def main():
    # Create client
    client = sc.Client()
    
    # Simple query
    print("Sending query...")
    response = client.query("Hello, ShadowClaude! Tell me about yourself.")
    
    print(f"\nResponse: {response.content}")
    
    # Query with context
    response = client.query(
        "What can you help me with?",
        context={"topic": "programming"}
    )
    
    print(f"\nContextual response: {response.content}")


if __name__ == "__main__":
    main()
