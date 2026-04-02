"""
Example: Query Engine
Demonstrates QueryEngine usage.
"""

import shadowclaude as sc


def main():
    # Create client with custom config
    client = sc.Client()
    engine = client.query_engine
    
    print("=== Query Engine Examples ===\n")
    
    # Simple query
    print("1. Simple Query:")
    result = engine.process("What is Python?")
    print(f"   Response: {result.content[:100]}...\n")
    
    # Query with context
    print("2. Contextual Query:")
    result = engine.process(
        "Explain how it works",
        context={"topic": "Python decorators"}
    )
    print(f"   Response: {result.content[:100]}...\n")
    
    # Batch queries
    print("3. Batch Processing:")
    queries = [
        "What is a variable?",
        "What is a function?",
        "What is a class?",
    ]
    
    results = engine.process_batch(queries)
    for i, result in enumerate(results, 1):
        print(f"   Query {i}: {result.content[:50]}...")


if __name__ == "__main__":
    main()
