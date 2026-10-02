
import json
import networkx as nx


def build_graph(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    graph = nx.DiGraph()

    for node in data["nodes"]:
        node_attributes = {
            key: value
            for key, value in node.items()
            if key != "id"
        }
        graph.add_node(node["id"], **node_attributes)

    for edge in data["edges"]:
        if isinstance(edge, dict):
            graph.add_edge(
                edge["source"],
                edge["target"],
                relation=edge.get("relation", "unspecified")
            )
        else:
            # Backward compatibility with the synthetic test graphs.
            source, target = edge
            graph.add_edge(source, target)

    return graph, data.get("target")