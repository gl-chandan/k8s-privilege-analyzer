
import json
from collections import Counter
from pathlib import Path

GRAPH_FILE = Path("data/extracted/k8s_graph.json")


def validate():
    with GRAPH_FILE.open(encoding="utf-8") as f:
        data = json.load(f)

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    node_map = {node["id"]: node for node in nodes}
    errors = []
    relation_counts = Counter()

    if len(node_map) != len(nodes):
        errors.append("Duplicate node IDs detected.")

    for edge in edges:
        if not isinstance(edge, dict):
            errors.append(f"Unexpected edge format: {edge}")
            continue

        source = edge.get("source")
        target = edge.get("target")
        relation = edge.get("relation", "unspecified")

        relation_counts[relation] += 1

        if source not in node_map:
            errors.append(f"Missing source node: {source}")

        if target not in node_map:
            errors.append(f"Missing target node: {target}")

    expected = {
        "subject_to_binding",
        "binding_to_role",
        "role_to_permission",
        "pod_uses_serviceaccount"
    }

    missing = expected - set(relation_counts)
    if missing:
        errors.append(
            "Expected relationship types missing: "
            + ", ".join(sorted(missing))
        )

    # Validate the original binding chain for each derived edge.
    subject_binding = set()
    binding_role = set()
    role_permission = set()

    for edge in edges:
        if not isinstance(edge, dict):
            continue

        relation = edge.get("relation")
        pair = (edge.get("source"), edge.get("target"))

        if relation == "subject_to_binding":
            subject_binding.add(pair)
        elif relation == "binding_to_role":
            binding_role.add(pair)
        elif relation == "role_to_permission":
            role_permission.add(pair)

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if edge.get("relation") != "effective_permission":
            continue

        subject = edge.get("source")
        permission = edge.get("target")
        binding = edge.get("binding")
        role = edge.get("role")

        valid_chain = (
            (subject, binding) in subject_binding
            and (binding, role) in binding_role
            and (role, permission) in role_permission
        )

        if not valid_chain:
            errors.append(
                f"Invalid effective permission chain: "
                f"{subject} -> {permission}"
            )

    # Check whether permission nodes retain core rule fields.
    permission_nodes = [
        node for node in nodes
        if node.get("type") == "permission"
    ]

    missing_rule_fields = []
    for node in permission_nodes:
        for field in ("verbs", "apiGroups", "resources"):
            if field not in node:
                missing_rule_fields.append((node["id"], field))

    print("Nodes:", len(nodes))
    print("Edges:", len(edges))
    print("Permission nodes:", len(permission_nodes))
    print("\nRelationship counts:")
    for relation, count in sorted(relation_counts.items()):
        print(f"  {relation}: {count}")

    if missing_rule_fields:
        print(
            "\nPermission nodes missing core rule fields:",
            len(missing_rule_fields)
        )
        for node_id, field in missing_rule_fields[:10]:
            print(f"  {node_id}: missing {field}")

    if errors:
        print("\nVALIDATION FAILED")
        for error in errors[:30]:
            print(" -", error)
        return False

    print("\nVALIDATION PASSED")
    return True


if __name__ == "__main__":
    if not validate():
        raise SystemExit(1)