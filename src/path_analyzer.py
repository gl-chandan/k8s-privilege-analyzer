
import networkx as nx

def find_escalation_paths(graph, target, max_depth=6):
    paths = []

    for node, data in graph.nodes(data=True):
        if data.get("type") != "subject":
            continue

        found_paths = nx.all_simple_paths(
            graph,
            source=node,
            target=target,
            cutoff=max_depth
        )

        for path in found_paths:
            paths.append(path)

    return paths

