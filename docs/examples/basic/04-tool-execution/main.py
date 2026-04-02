"""
Example: Tool Execution
Demonstrates various tool executions.
"""

import shadowclaude as sc


def main():
    client = sc.Client()
    
    print("=== Tool Execution Examples ===\n")
    
    # File read
    print("1. Read File:")
    result = client.execute_tool("read_file", {"path": "README.md"})
    print(f"   Lines: {len(result.output.split(chr(10)))}")
    
    # Bash command
    print("\n2. Run Command:")
    result = client.execute_tool("bash", {"command": "echo Hello from ShadowClaude"})
    print(f"   Output: {result.output.strip()}")
    
    # Web fetch
    print("\n3. Fetch Web Page:")
    result = client.execute_tool("web_fetch", {"url": "https://example.com"})
    print(f"   Length: {len(result.output)} chars")
    
    # Search
    print("\n4. Search Files:")
    result = client.execute_tool("search_files", {
        "pattern": "def ",
        "glob": "*.py"
    })
    print(f"   Matches: {len(result.output)}")


if __name__ == "__main__":
    main()
