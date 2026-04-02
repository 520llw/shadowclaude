"""
Example: Memory Basic
Demonstrates basic memory operations.
"""

import shadowclaude as sc


def main():
    client = sc.Client()
    memory = client.get_memory()
    
    print("=== Memory Basic Examples ===\n")
    
    # Store memory
    print("1. Store Memory:")
    memory_id = memory.store("Python was created by Guido van Rossum")
    print(f"   Stored: {memory_id}")
    
    # Retrieve
    print("\n2. Retrieve Memory:")
    results = memory.retrieve("Who created Python?", limit=5)
    for r in results:
        print(f"   - {r.content} (score: {r.score:.2f})")
    
    # Working memory
    print("\n3. Working Memory:")
    wm = memory.get_working_memory()
    wm.add_message("user", "Hello!")
    wm.add_message("assistant", "Hi there!")
    print(f"   Messages: {len(wm.messages)}")


if __name__ == "__main__":
    main()
