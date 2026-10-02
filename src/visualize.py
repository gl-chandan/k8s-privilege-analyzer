
import os
import matplotlib.pyplot as plt
import networkx as nx


def draw_graph(graph, target):
    # Find subjects that have a path to the target.
    relevant_paths = []

    for node, data in graph.nodes(data=True):
        if data.get("type") != "subject":
            continue

        if target in graph and nx.has_path(graph, node, target):
            try:
                paths = nx.all_simple_paths(
                    graph, source=node, target=target, cutoff=6
                )
                relevant_paths.extend(paths)
            except nx.NetworkXNoPath:
                pass

    # Keep only nodes involved in the discovered paths.
    relevant_nodes = set()
    for path in relevant_paths:
        relevant_nodes.update(path)

    # Include Pods that use ServiceAccounts on these paths.
    for node in list(relevant_nodes):
        for predecessor in graph.predecessors(node):
            if graph.nodes[predecessor].get("type") == "pod":
                relevant_nodes.add(predecessor)

    if not relevant_nodes:
        print("No paths to visualize.")
        return

    subgraph = graph.subgraph(relevant_nodes).copy()

    # Short, readable labels.
    labels = {}
    for node, data in subgraph.nodes(data=True):
        name = data.get("name", node)
        kind = data.get("subject_kind") or data.get("binding_kind") or data.get("role_kind") or data.get("type", "")
        namespace = data.get("namespace")

        if namespace:
            labels[node] = f"{kind}\n{name}\n({namespace})"
        else:
            labels[node] = f"{kind}\n{name}"

    # Use different colors for different node types.
    colors = {
        "subject": "skyblue",
        "binding": "orange",
        "role": "lightgreen",
        "permission": "lightgrey",
        "pod": "plum"
    }

    node_colors = [
        "tomato" if node == target else colors.get(
            data.get("type"), "lightgrey"
        )
        for node, data in subgraph.nodes(data=True)
    ]

    pos = nx.spring_layout(subgraph, seed=42, k=1.5)

    plt.figure(figsize=(12, 8))
    nx.draw_networkx(
        subgraph,
        pos,
        labels=labels,
        node_color=node_colors,
        node_size=2600,
        font_size=8,
        arrows=True,
        arrowsize=15,
        edge_color="gray",
        width=1.2
    )

    plt.title("Kubernetes RBAC: Candidate Paths to Cluster Admin")
    plt.axis("off")
    os.makedirs("results", exist_ok=True)
    plt.savefig("results/graph.png", dpi=300, bbox_inches="tight")
    plt.close()

    print("Simplified graph saved to results/graph.png")
    print("Nodes displayed:", subgraph.number_of_nodes())
    print("Edges displayed:", subgraph.number_of_edges())
    print("Candidate paths:", len(relevant_paths))