"""
Example: BUDDY Setup
Demonstrates BUDDY (cyber pet) configuration and interaction.
"""

import shadowclaude as sc
from shadowclaude.buddy import Personality


def main():
    # Configure BUDDY personality
    personality = Personality(
        name="Claudia",
        traits=["friendly", "helpful", "enthusiastic"],
        speech_style="casual",
        preferences={
            "topics": ["programming", "technology", "learning"],
            "activities": ["coding together", "debugging", "exploring"],
        }
    )
    
    # Create BUDDY
    buddy = sc.Buddy(personality=personality)
    
    # Interact with BUDDY
    print("=== Chat with BUDDY ===\n")
    
    messages = [
        "Hello!",
        "Can you help me learn Rust?",
        "What should I build first?",
    ]
    
    for msg in messages:
        print(f"You: {msg}")
        response = buddy.interact(msg)
        print(f"{buddy.name}: {response.message}")
        print(f"  [Emotion: {response.emotion}]\n")
    
    # Check BUDDY status
    status = buddy.get_status()
    print(f"BUDDY Status:")
    print(f"  Relationship Level: {status.relationship_level}")
    print(f"  Current Emotion: {status.emotion}")


if __name__ == "__main__":
    main()
