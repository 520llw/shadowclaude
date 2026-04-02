"""
Example: Multi-Agent
Demonstrates multiple agents working together.
"""

import asyncio
import shadowclaude as sc
from shadowclaude.agents import Agent, Task, TaskResult, Coordinator


class RequirementsAgent(Agent):
    """Analyzes requirements."""
    
    def handle(self, task: Task) -> TaskResult:
        description = task.data.get("description", "")
        
        # Extract requirements
        requirements = [
            req.strip()
            for req in description.split(",")
            if req.strip()
        ]
        
        return TaskResult(
            success=True,
            output={
                "requirements": requirements,
                "count": len(requirements),
            }
        )


class DesignAgent(Agent):
    """Creates design based on requirements."""
    
    def handle(self, task: Task) -> TaskResult:
        requirements = task.data.get("requirements", [])
        
        # Generate design
        design = {
            "components": [f"Component for: {req}" for req in requirements],
            "interfaces": ["API", "CLI", "Web"],
            "data_model": ["User", "Task", "Result"],
        }
        
        return TaskResult(
            success=True,
            output=design
        )


class ImplementationAgent(Agent):
    """Implements based on design."""
    
    def handle(self, task: Task) -> TaskResult:
        design = task.data.get("design", {})
        
        # Generate code structure
        code = {
            "files": [
                f"src/{comp.lower().replace(' ', '_')}.py"
                for comp in design.get("components", [])
            ],
            "tests": ["tests/test_main.py"],
            "docs": ["README.md", "API.md"],
        }
        
        return TaskResult(
            success=True,
            output=code
        )


class ReviewAgent(Agent):
    """Reviews the implementation."""
    
    def handle(self, task: Task) -> TaskResult:
        code = task.data.get("code", {})
        
        # Review
        issues = []
        if len(code.get("files", [])) < 3:
            issues.append("Consider splitting into more files")
        if "tests" not in code:
            issues.append("Missing tests")
        
        return TaskResult(
            success=True,
            output={
                "approved": len(issues) == 0,
                "issues": issues,
                "recommendations": ["Add documentation", "Write integration tests"],
            }
        )


def main():
    # Create coordinator
    coordinator = Coordinator()
    
    # Register agents
    coordinator.register_agent("requirements", RequirementsAgent())
    coordinator.register_agent("design", DesignAgent())
    coordinator.register_agent("implementation", ImplementationAgent())
    coordinator.register_agent("review", ReviewAgent())
    
    print("=== Multi-Agent Workflow ===\n")
    
    # Step 1: Requirements
    print("Step 1: Gathering requirements...")
    req_task = Task(
        agent_type="requirements",
        data={"description": "user authentication, data storage, API endpoints"}
    )
    req_result = coordinator.dispatch(req_task)
    print(f"  Found {req_result.output['count']} requirements")
    
    # Step 2: Design
    print("\nStep 2: Creating design...")
    design_task = Task(
        agent_type="design",
        data={"requirements": req_result.output["requirements"]}
    )
    design_result = coordinator.dispatch(design_task)
    print(f"  Components: {len(design_result.output['components'])}")
    
    # Step 3: Implementation
    print("\nStep 3: Implementing...")
    impl_task = Task(
        agent_type="implementation",
        data={"design": design_result.output}
    )
    impl_result = coordinator.dispatch(impl_task)
    print(f"  Files to create: {len(impl_result.output['files'])}")
    
    # Step 4: Review
    print("\nStep 4: Reviewing...")
    review_task = Task(
        agent_type="review",
        data={"code": impl_result.output}
    )
    review_result = coordinator.dispatch(review_task)
    print(f"  Approved: {review_result.output['approved']}")
    print(f"  Issues: {review_result.output['issues']}")
    
    print("\n=== Workflow Complete ===")


if __name__ == "__main__":
    main()
