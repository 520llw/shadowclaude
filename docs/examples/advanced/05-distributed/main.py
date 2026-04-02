"""
Example: Distributed Deployment
Demonstrates distributed ShadowClaude setup.
"""

import shadowclaude as sc
from shadowclaude.distributed import Cluster, NodeConfig


def main():
    print("=== Distributed Deployment Example ===\n")
    
    # Configure cluster
    cluster = Cluster(
        name="production-cluster",
        coordinator_node="node-1",
    )
    
    # Add worker nodes
    nodes = [
        NodeConfig(
            id="node-1",
            host="192.168.1.10",
            port=8080,
            role="coordinator",
            resources={"cpu": 8, "memory": "32GB"}
        ),
        NodeConfig(
            id="node-2",
            host="192.168.1.11",
            port=8080,
            role="worker",
            resources={"cpu": 16, "memory": "64GB"}
        ),
        NodeConfig(
            id="node-3",
            host="192.168.1.12",
            port=8080,
            role="worker",
            resources={"cpu": 16, "memory": "64GB"}
        ),
    ]
    
    for node in nodes:
        cluster.add_node(node)
    
    # Configure load balancing
    cluster.configure_load_balancer(
        strategy="least_connections",
        health_check_interval=30,
    )
    
    # Start cluster
    print("Starting cluster...")
    cluster.start()
    
    print(f"\nCluster Status:")
    print(f"  Nodes: {len(cluster.nodes)}")
    print(f"  Active: {cluster.active_nodes}")
    print(f"  Load: {cluster.current_load:.1%}")
    
    # Submit distributed task
    print("\nSubmitting distributed task...")
    task = sc.Task(
        description="Analyze large codebase",
        data={"repository": "https://github.com/example/repo"},
        distributed=True,
        partitions=3,  # Split into 3 parallel tasks
    )
    
    result = cluster.submit(task)
    print(f"Task completed: {result.success}")
    print(f"Workers used: {result.workers}")
    print(f"Duration: {result.duration:.2f}s")


if __name__ == "__main__":
    main()
