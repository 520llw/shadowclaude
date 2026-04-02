"""
Example: Agent Basic
Demonstrates basic agent creation and task handling.
"""

import shadowclaude as sc
from shadowclaude.agents import Agent, Task, TaskResult


class CodeAnalyzerAgent(Agent):
    """Agent that analyzes code quality."""
    
    def handle(self, task: Task) -> TaskResult:
        code = task.data.get("code", "")
        
        # Simple analysis
        lines = code.split("\n")
        issues = []
        
        for i, line in enumerate(lines, 1):
            if len(line) > 80:
                issues.append(f"Line {i}: Too long ({len(line)} chars)")
            if "TODO" in line:
                issues.append(f"Line {i}: Contains TODO")
        
        return TaskResult(
            success=True,
            output={
                "total_lines": len(lines),
                "issues": issues,
                "issue_count": len(issues),
            }
        )


class SummaryAgent(Agent):
    """Agent that summarizes text."""
    
    def handle(self, task: Task) -> TaskResult:
        text = task.data.get("text", "")
        words = text.split()
        
        # Simple summary
        summary = " ".join(words[:20]) + "..." if len(words) > 20 else text
        
        return TaskResult(
            success=True,
            output={
                "original_length": len(words),
                "summary": summary,
            }
        )


def main():
    client = sc.Client()
    coordinator = client.get_coordinator()
    
    # Register agents
    coordinator.register_agent("analyzer", CodeAnalyzerAgent())
    coordinator.register_agent("summarizer", SummaryAgent())
    
    # Create tasks
    code = """
def my_function():
    # TODO: Implement this
    very_long_variable_name_that_makes_this_line_way_too_long_for_standard = True
    pass
"""
    
    task1 = Task(
        agent_type="analyzer",
        data={"code": code}
    )
    
    result1 = coordinator.dispatch(task1)
    print("Code Analysis:", result1.output)
    
    task2 = Task(
        agent_type="summarizer",
        data={"text": "ShadowClaude is a powerful AI programming assistant framework built with Rust and Python."}
    )
    
    result2 = coordinator.dispatch(task2)
    print("Summary:", result2.output)


if __name__ == "__main__":
    main()
