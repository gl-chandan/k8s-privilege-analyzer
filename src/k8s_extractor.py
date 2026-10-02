
import json
from pathlib import Path

DATA_DIR = Path("data/extracted")
OUTPUT_FILE = DATA_DIR / "k8s_graph.json"


def load_items(filename):
    """Load the Kubernetes items from one exported JSON file."""
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        return json.load(file).get("items", [])


def add_node(nodes, node_id, node_type, **attributes):
    """Add a node once, preserving its metadata."""
    if node_id not in nodes:
        nodes[node_id] = {
            "id": node_id,
            "type": node_type,
            **attributes
        }


def add_edge(edges, source, target, relation):
    """Add a directed, labeled relationship."""
    edge = {
        "source": source,
        "target": target,
        "relation": relation
    }
    if edge not in edges:
        edges.append(edge)


def service_account_id(namespace, name):
    return f"serviceaccount::{namespace}::{name}"


def role_id(kind, namespace, name):
    if kind == "ClusterRole":
        return f"clusterrole::{name}"
    return f"role::{namespace}::{name}"


def subject_id(subject, binding_namespace=None):
    """Create a stable ID for a binding subject."""
    kind = subject.get("kind", "")
    name = subject.get("name", "")

    if kind == "ServiceAccount":
        namespace = subject.get("namespace") or binding_namespace or "unknown"
        return service_account_id(namespace, name), "subject"

    if kind == "User":
        return f"user::{name}", "subject"

    if kind == "Group":
        return f"group::{name}", "subject"

    return f"unknown-subject::{kind}::{name}", "subject"


def build_kubernetes_graph():
    nodes = {}
    edges = []

    service_accounts = load_items("serviceaccounts.json")
    roles = load_items("roles.json")
    cluster_roles = load_items("clusterroles.json")
    role_bindings = load_items("rolebindings.json")
    cluster_role_bindings = load_items("clusterrolebindings.json")
    pods = load_items("pods.json")

    # 1. ServiceAccounts
    for item in service_accounts:
        metadata = item.get("metadata", {})
        namespace = metadata.get("namespace", "default")
        name = metadata.get("name", "")
        if not name:
            continue

        add_node(
            nodes,
            service_account_id(namespace, name),
            "subject",
            subject_kind="ServiceAccount",
            name=name,
            namespace=namespace,
            source="serviceaccounts"
        )

    # 2. Roles and ClusterRoles
    for item in roles:
        metadata = item.get("metadata", {})
        namespace = metadata.get("namespace", "default")
        name = metadata.get("name", "")
        if not name:
            continue

        add_node(
            nodes,
            role_id("Role", namespace, name),
            "role",
            role_kind="Role",
            name=name,
            namespace=namespace,
            rules=item.get("rules", [])
        )

    for item in cluster_roles:
        metadata = item.get("metadata", {})
        name = metadata.get("name", "")
        if not name:
            continue

        add_node(
            nodes,
            role_id("ClusterRole", None, name),
            "role",
            role_kind="ClusterRole",
            name=name,
            namespace=None,
            rules=item.get("rules", []),
            aggregation_rule=item.get("aggregationRule")
        )

    # 3. RoleBindings and ClusterRoleBindings
    bindings = [
        (item, "RoleBinding")
        for item in role_bindings
    ] + [
        (item, "ClusterRoleBinding")
        for item in cluster_role_bindings
    ]

    for item, binding_kind in bindings:
        metadata = item.get("metadata", {})
        namespace = metadata.get("namespace", "default")
        name = metadata.get("name", "")
        if not name:
            continue

        if binding_kind == "RoleBinding":
            binding_node_id = f"rolebinding::{namespace}::{name}"
        else:
            binding_node_id = f"clusterrolebinding::{name}"

        add_node(
            nodes,
            binding_node_id,
            "binding",
            binding_kind=binding_kind,
            name=name,
            namespace=namespace if binding_kind == "RoleBinding" else None
        )

        # A binding connects subjects to a Role or ClusterRole.
        for subject in item.get("subjects", []):
            sid, stype = subject_id(
                subject,
                binding_namespace=namespace if binding_kind == "RoleBinding" else None
            )

            add_node(
                nodes,
                sid,
                stype,
                subject_kind=subject.get("kind"),
                name=subject.get("name"),
                namespace=subject.get("namespace") or (
                    namespace if binding_kind == "RoleBinding"
                    and subject.get("kind") == "ServiceAccount"
                    else None
                )
            )
            add_edge(edges, sid, binding_node_id, "subject_to_binding")

        role_ref = item.get("roleRef", {})
        ref_kind = role_ref.get("kind", "")
        ref_name = role_ref.get("name", "")

        if ref_kind in ("Role", "ClusterRole") and ref_name:
            if ref_kind == "Role":
                target_role_id = role_id("Role", namespace, ref_name)
            else:
                target_role_id = role_id("ClusterRole", None, ref_name)

            # Preserve a reference even if the role was not in the snapshot.
            if target_role_id not in nodes:
                add_node(
                    nodes,
                    target_role_id,
                    "role",
                    role_kind=ref_kind,
                    name=ref_name,
                    namespace=namespace if ref_kind == "Role" else None,
                    rules=[],
                    unresolved=True
                )

            add_edge(edges, binding_node_id, target_role_id, "binding_to_role")

    # 4. RBAC rule nodes
    # Each rule is retained as metadata on its permission node.
    for node_id, node in list(nodes.items()):
        if node.get("type") != "role":
            continue

        for index, rule in enumerate(node.get("rules", [])):
            permission_id = f"permission::{node_id}::rule::{index}"

            add_node(
                nodes,
                permission_id,
                "permission",
                role=node_id,
                rule_index=index,
                verbs=rule.get("verbs", []),
                api_groups=rule.get("apiGroups", []),
                resources=rule.get("resources", []),
                resource_names=rule.get("resourceNames", []),
                non_resource_urls=rule.get("nonResourceURLs", [])
            )
            add_edge(edges, node_id, permission_id, "role_to_permission")

    # 5. Pods and their configured ServiceAccounts
    for item in pods:
        metadata = item.get("metadata", {})
        spec = item.get("spec", {})
        namespace = metadata.get("namespace", "default")
        name = metadata.get("name", "")
        if not name:
            continue

        pod_node_id = f"pod::{namespace}::{name}"
        sa_name = spec.get("serviceAccountName", "default")
        sa_node_id = service_account_id(namespace, sa_name)

        add_node(
            nodes,
            pod_node_id,
            "pod",
            name=name,
            namespace=namespace
        )

        # A pod references a ServiceAccount. If it was absent from the
        # ServiceAccount snapshot, retain the reference as an inferred node.
        if sa_node_id not in nodes:
            add_node(
                nodes,
                sa_node_id,
                "subject",
                subject_kind="ServiceAccount",
                name=sa_name,
                namespace=namespace,
                source="inferred_from_pod"
            )

        add_edge(edges, pod_node_id, sa_node_id, "pod_uses_serviceaccount")

    # The target is the cluster-admin ClusterRole, if present.
    target_id = "clusterrole::cluster-admin"
    if target_id not in nodes:
        target_id = None

    graph_data = {
        "nodes": list(nodes.values()),
        "edges": edges,
        "target": target_id
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(graph_data, file, indent=2)

    print("Kubernetes configuration graph created")
    print(f"Nodes: {len(nodes)}")
    print(f"Edges: {len(edges)}")
    print(f"Target: {target_id}")
    print(f"Output: {OUTPUT_FILE}")

    return graph_data


if __name__ == "__main__":
    build_kubernetes_graph()