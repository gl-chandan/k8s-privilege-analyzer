
import json
from collections import defaultdict

GRAPH_FILE = "data/extracted/k8s_graph.json"

SENSITIVE_VERBS = {"bind", "escalate", "impersonate"}

WORKLOAD_RESOURCES = {
    "pods",
    "deployments",
    "replicasets",
    "statefulsets",
    "daemonsets",
    "jobs",
    "cronjobs",
}


def main():
    with open(GRAPH_FILE, encoding="utf-8") as file:
        data = json.load(file)

    nodes = {node["id"]: node for node in data["nodes"]}
    edges = data["edges"]

    subject_roles = defaultdict(set)

    for edge in edges:
        if edge.get("relation") != "subject_to_binding":
            continue

        subject_id = edge["source"]
        binding_id = edge["target"]

        for next_edge in edges:
            if (
                next_edge.get("source") == binding_id
                and next_edge.get("relation") == "binding_to_role"
            ):
                subject_roles[subject_id].add(next_edge["target"])

    print("RBAC Configuration Audit")
    print("=" * 50)

    # Direct administrative grants
    print("\n1. Direct cluster-admin assignments")
    direct_count = 0

    for subject_id, roles in sorted(subject_roles.items()):
        if "clusterrole::cluster-admin" in roles:
            direct_count += 1
            subject = nodes.get(subject_id, {})
            print(
                f"- {subject.get('subject_kind', subject.get('type'))}: "
                f"{subject.get('name', subject_id)} "
                f"(namespace={subject.get('namespace')})"
            )

    print("Total:", direct_count)

    # Permissions that may enable privilege escalation
    print("\n2. Roles with sensitive RBAC verbs")
    sensitive_count = 0

    for role_id, role in sorted(nodes.items()):
        if role.get("type") != "role":
            continue

        for index, rule in enumerate(role.get("rules", [])):
            verbs = set(rule.get("verbs", []))
            resources = set(rule.get("resources", []))

            sensitive = verbs & SENSITIVE_VERBS

            if "*" in verbs:
                sensitive.add("* (wildcard verbs)")

            if sensitive:
                sensitive_count += 1
                print(f"\n- Role: {role_id}")
                print(f"  Rule index: {index}")
                print(f"  Verbs: {sorted(sensitive)}")
                print(f"  Resources: {sorted(resources)}")
                print(f"  API groups: {rule.get('apiGroups', [])}")

    print("\nSensitive rules found:", sensitive_count)

    # Workload creation is a candidate condition, not proof of escalation.
    print("\n3. Roles with workload creation permissions")
    workload_count = 0

    for role_id, role in sorted(nodes.items()):
        if role.get("type") != "role":
            continue

        for index, rule in enumerate(role.get("rules", [])):
            verbs = set(rule.get("verbs", []))
            resources = set(rule.get("resources", []))

            can_create = "create" in verbs or "*" in verbs
            can_create_workload = (
                "*" in resources
                or bool(resources & WORKLOAD_RESOURCES)
            )

            if can_create and can_create_workload:
                workload_count += 1
                print(f"\n- Role: {role_id}")
                print(f"  Rule index: {index}")
                print(f"  Verbs: {sorted(verbs)}")
                print(f"  Resources: {sorted(resources)}")

    print("\nWorkload creation rules found:", workload_count)
    print("\nNote: These are configuration findings, not confirmed")
    print("exploitable privilege-escalation paths.")


if __name__ == "__main__":
    main()