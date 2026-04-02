"""
Example: Jupyter Notebook
Integration with Jupyter notebooks.
"""

import shadowclaude as sc


class JupyterMagic:
    """Jupyter magic commands for ShadowClaude."""
    
    def __init__(self):
        self.client = sc.Client()
    
    def shadowclaude(self, line: str, cell: str = None):
        """%%shadowclaude magic command.
        
        Usage:
            %shadowclaude explain this code
            %%shadowclaude
            Generate a function to sort a list
        """
        query = cell if cell else line
        response = self.client.query(query)
        return response.content
    
    def shadow_explain(self, line: str):
        """%shadow_explain magic - explain current cell."""
        # In real usage, this would get the cell content from Jupyter
        code = line
        
        response = self.client.query(
            f"Explain this code step by step:\n\n```python\n{code}\n```"
        )
        
        print(response.content)
    
    def shadow_fix(self, line: str):
        """%shadow_fix magic - fix code issues."""
        code = line
        
        response = self.client.query(
            f"Fix any issues in this code:\n\n```python\n{code}\n```"
        )
        
        print("Suggested fix:")
        print(response.content)
    
    def shadow_optimize(self, line: str):
        """%shadow_optimize magic - optimize code."""
        code = line
        
        response = self.client.query(
            f"Optimize this code for better performance:\n\n```python\n{code}\n```"
        )
        
        print("Optimized version:")
        print(response.content)
    
    def shadow_doc(self, line: str):
        """%shadow_doc magic - generate documentation."""
        code = line
        
        response = self.client.query(
            f"Generate docstring and type hints for this code:\n\n```python\n{code}\n```"
        )
        
        print("Documented code:")
        print(response.content)


# Example notebook cells
def example_notebook_usage():
    """Demonstrates how the magic commands would be used in a notebook."""
    
    magic = JupyterMagic()
    
    # Cell 1: Simple query
    print("=== Cell 1: Simple Query ===")
    result = magic.shadowclaude("What is the best way to handle errors in Python?")
    print(result)
    
    # Cell 2: Explain code
    print("\n=== Cell 2: Explain Code ===")
    code = """
    def factorial(n):
        if n == 0:
            return 1
        return n * factorial(n - 1)
    """
    magic.shadow_explain(code)
    
    # Cell 3: Fix code
    print("\n=== Cell 3: Fix Code ===")
    buggy_code = """
    def divide(a, b):
        return a / b
    """
    magic.shadow_fix(buggy_code)
    
    # Cell 4: Optimize
    print("\n=== Cell 4: Optimize ===")
    slow_code = """
    result = []
    for i in range(10000):
        result.append(i * 2)
    """
    magic.shadow_optimize(slow_code)
    
    # Cell 5: Document
    print("\n=== Cell 5: Document ===")
    undoc_code = """
    def greet(name):
        return f"Hello, {name}!"
    """
    magic.shadow_doc(undoc_code)


if __name__ == "__main__":
    example_notebook_usage()
