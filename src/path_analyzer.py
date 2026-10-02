
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

def find_direct_admin_assignments(graph, target):
    """
    Baseline: Find subjects directly connected to the target
    role through a binding.
    """
    paths = []

    for subject, data in graph.nodes(data=True):
        if data.get("type") != "subject":
            continue

        # Subject -> Binding
        for binding in graph.successors(subject):
            binding_data = graph.nodes[binding]

            if binding_data.get("type") != "binding":
                continue

            edge_data = graph.get_edge_data(subject, binding, {})
            if edge_data.get("relation") != "subject_to_binding":
                continue

            # Binding -> Target role
            if not graph.has_edge(binding, target):
                continue

            edge_data = graph.get_edge_data(binding, target, {})
            if edge_data.get("relation") != "binding_to_role":
                continue

            paths.append([subject, binding, target])

    return paths
