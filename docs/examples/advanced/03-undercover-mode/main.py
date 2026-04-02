"""
Example: Undercover Mode
Demonstrates stealth assistance features.
"""

import shadowclaude as sc
from shadowclaude.undercover import UndercoverMode, TriggerPattern


def main():
    print("=== Undercover Mode Demo ===\n")
    
    # Configure undercover mode
    undercover = UndercoverMode(
        # Trigger patterns
        triggers=[
            TriggerPattern(r"error|exception|bug|fail", priority="high"),
            TriggerPattern(r"TODO|FIXME|XXX", priority="medium"),
            TriggerPattern(r"optimize|improve|refactor", priority="low"),
        ],
        
        # Response settings
        auto_suggest=True,
        suggestion_delay=2.0,  # seconds
        
        # Notification settings
        notification_level="subtle",  # silent, subtle, normal
        
        # Context awareness
        context_detection=True,
    )
    
    # Simulate various scenarios
    scenarios = [
        {
            "input": "I'm getting a NullPointerException in line 42",
            "context": {"file": "Main.java", "line": 42},
        },
        {
            "input": "TODO: Implement user authentication",
            "context": {"file": "auth.py", "project": "web-app"},
        },
        {
            "input": "Need to refactor this messy code",
            "context": {"file": "utils.py"},
        },
        {
            "input": "The weather is nice today",
            "context": {},
        },
    ]
    
    for scenario in scenarios:
        print(f"Input: {scenario['input']}")
        print(f"Context: {scenario['context']}")
        
        # Process input
        result = undercover.process(
            input_text=scenario['input'],
            context=scenario['context']
        )
        
        if result.triggered:
            print(f"  [Triggered: {result.trigger}]")
            print(f"  [Suggestion: {result.suggestion}]")
        else:
            print("  [No trigger]")
        
        print()
    
    # Statistics
    stats = undercover.get_stats()
    print("Undercover Statistics:")
    print(f"  Total inputs processed: {stats['total_inputs']}")
    print(f"  Triggers fired: {stats['triggers_fired']}")
    print(f"  Suggestions made: {stats['suggestions_made']}")


if __name__ == "__main__":
    main()
