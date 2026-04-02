"""
Example: File Operations
Demonstrates file read, write, and search operations.
"""

import shadowclaude as sc


def main():
    client = sc.Client()
    
    # Read file example
    print("=== Reading File ===")
    result = client.execute_tool("read_file", {
        "path": "README.md"
    })
    print(f"File content preview: {result.output[:200]}...")
    
    # Search files example
    print("\n=== Searching Files ===")
    result = client.execute_tool("search_files", {
        "pattern": "TODO|FIXME",
        "glob": "*.{py,rs,js}"
    })
    print(f"Found {len(result.output)} matches")
    
    # Write file example
    print("\n=== Writing File ===")
    result = client.execute_tool("write_file", {
        "path": "/tmp/example.txt",
        "content": "Hello from ShadowClaude!"
    })
    print(f"Write result: {result.success}")


if __name__ == "__main__":
    main()
