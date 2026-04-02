"""
Example: Memory Advanced
Demonstrates advanced memory management features.
"""

import datetime
import shadowclaude as sc
from shadowclaude.memory import MemoryType


def main():
    client = sc.Client()
    memory = client.get_memory()
    
    print("=== Advanced Memory Management ===\n")
    
    # 1. Store different types of memories
    print("1. Storing memories...")
    
    # Semantic memory (knowledge)
    semantic_id = memory.store(
        "Python uses indentation for code blocks",
        memory_type=MemoryType.SEMANTIC,
        metadata={
            "topic": "python",
            "category": "syntax",
            "confidence": 0.95
        }
    )
    print(f"  Semantic memory stored: {semantic_id}")
    
    # Episodic memory (event)
    episodic_id = memory.store(
        "Debugged authentication bug in login module",
        memory_type=MemoryType.EPISODIC,
        metadata={
            "timestamp": datetime.datetime.now().isoformat(),
            "project": "auth-system",
            "outcome": "resolved"
        }
    )
    print(f"  Episodic memory stored: {episodic_id}")
    
    # 2. Retrieve with filters
    print("\n2. Retrieving memories with filters...")
    
    python_memories = memory.retrieve(
        query="python programming",
        memory_types=[MemoryType.SEMANTIC],
        filters={"topic": "python"},
        limit=5
    )
    print(f"  Found {len(python_memories)} Python-related memories")
    
    # 3. Update memory
    print("\n3. Updating memory...")
    memory.update(
        semantic_id,
        content="Python uses indentation for code blocks (4 spaces recommended)",
        metadata={"updated": True}
    )
    print(f"  Memory {semantic_id} updated")
    
    # 4. Memory relationships
    print("\n4. Creating memory relationships...")
    memory.link(
        source=semantic_id,
        target=episodic_id,
        relation_type="related_to"
    )
    print(f"  Linked {semantic_id} -> {episodic_id}")
    
    # 5. Memory consolidation
    print("\n5. Running memory consolidation...")
    stats = memory.consolidate(
        strategy="importance",
        threshold=0.7
    )
    print(f"  Consolidated: {stats['consolidated']} memories")
    print(f"  Archived: {stats['archived']} memories")
    
    # 6. Export/Import
    print("\n6. Exporting memories...")
    memory.export_to_file("/tmp/memories_backup.json")
    print("  Exported to /tmp/memories_backup.json")


if __name__ == "__main__":
    main()
