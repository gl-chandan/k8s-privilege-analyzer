


import csv
import os
import time

from src.graph_builder import build_graph
from src.visualize import draw_graph
from src.path_analyzer import (
    find_escalation_paths,
    find_direct_admin_assignments
)


# Step 1: Build the graph
graph, target = build_graph("data/extracted/k8s_graph.json")

print("Nodes:", graph.number_of_nodes())
print("Edges:", graph.number_of_edges())
print("Target:", target)


# Step 2: Display graph nodes
print("\nGraph nodes:")
for node, data in graph.nodes(data=True):
    print(node, data)


# Step 3: Display graph edges
print("\nGraph edges:")
for source, destination in graph.edges():
    print(source, "->", destination)


# Step 4: Visualize the graph
draw_graph(graph,target)


# Step 5: Find privilege escalation paths
paths = find_escalation_paths(graph, target, max_depth=6)

print("\nPrivilege Escalation Paths:")

if paths:
    for i, path in enumerate(paths, start=1):
        print(f"Path {i}: {' -> '.join(path)}")
else:
    print("No paths found")


# Step 6: Save paths to CSV
os.makedirs("results", exist_ok=True)

with open("results/paths.csv", "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Path ID", "Source", "Target", "Path Length", "Path"])

    for i, path in enumerate(paths, start=1):
        writer.writerow([
            i,
            path[0],
            target,
            len(path) - 1,
            " -> ".join(path)
        ])

print("\nPaths saved to results/paths.csv")


# Step 7: Compare baseline and graph-based method
baseline_start = time.perf_counter()
baseline_paths = find_direct_admin_assignments(graph, target)
baseline_time = time.perf_counter() - baseline_start

graph_start = time.perf_counter()
graph_paths = find_escalation_paths(graph, target, max_depth=6)
graph_time = time.perf_counter() - graph_start

print("\nComparative Evaluation")
print("Baseline paths:", len(baseline_paths))
print("Graph-based paths:", len(graph_paths))
print(f"Baseline time: {baseline_time:.6f} seconds")
print(f"Graph-based time: {graph_time:.6f} seconds")

os.makedirs("results", exist_ok=True)
with open("results/baseline_comparison.csv", "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Method", "Candidate Paths", "Execution Time (seconds)"])
    writer.writerow(["Baseline", len(baseline_paths), baseline_time])
    writer.writerow(["Graph-based", len(graph_paths), graph_time])

print("Comparison saved to results/baseline_comparison.csv")