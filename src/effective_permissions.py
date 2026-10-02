
import json
from pathlib import Path


INPUT_FILE = Path("data/extracted/k8s_graph.json")
OUTPUT_FILE = Path("data/extracted/k8s_graph.json")


def add_effective_permission_edges(data):
    nodes = {node["id"]: node for node in data["nodes"]}
    data["edges"] = [
        edge for edge in data["edges"]
        if edge.get("relation") != "effective_permission"
    ]
    edges = data["edges"]

    # Index existing edges by their relationship.
    subjects_by_binding = {}
    roles_by_binding = {}
    permissions_by_role = {}

    for edge in edges:
        if not isinstance(edge, dict):
            continue

        source = edge.get("source")
        target = edge.get("target")
        relation = edge.get("relation")

        if relation == "subject_to_binding":
            subjects_by_binding.setdefault(target, []).append(source)

        elif relation == "binding_to_role":
            roles_by_binding.setdefault(source, []).append(target)

        elif relation == "role_to_permission":
            permissions_by_role.setdefault(source, []).append(target)

    new_edges = []
    existing = {
        (
            edge.get("source"),
            edge.get("target"),
            edge.get("relation")
        )
        for edge in edges
        if isinstance(edge, dict)
    }

    for binding_id, subject_ids in subjects_by_binding.items():
        binding = nodes.get(binding_id, {})
        binding_kind = binding.get("binding_kind")

        # Namespace is meaningful for RoleBindings.
        namespace = binding.get("namespace")

        if binding_kind == "ClusterRoleBinding":
            scope = "cluster"
            namespace = None
        else:
            scope = "namespace"

        for role_id in roles_by_binding.get(binding_id, []):
            for permission_id in permissions_by_role.get(role_id, []):
                for subject_id in subject_ids:
                    key = (
                        subject_id,
                        permission_id,
                        "effective_permission"
                    )

                    if key in existing:
                        continue

                    new_edges.append({
                        "source": subject_id,
                        "target": permission_id,
                        "relation": "effective_permission",
                        "binding": binding_id,
                        "role": role_id,
                        "scope": scope,
                        "namespace": namespace
                    })
                    existing.add(key)

    data["edges"].extend(new_edges)
    return data, len(new_edges)


def main():
    with INPUT_FILE.open(encoding="utf-8") as f:
        data = json.load(f)

    data, count = add_effective_permission_edges(data)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("Effective permission relationships added:", count)
    print("Updated graph:", OUTPUT_FILE)


if __name__ == "__main__":
    main()