# Migration Guide: Transitioning to Stack 3.0

Welcome to Stack 3.0. This update introduces breaking changes in how tools are called and how context is managed to enable the new Cognitive Pipeline.

## 📋 Summary of Changes
| Feature | Stack 2.9 | Stack 3.0 | Migration Action |
| :--- | :--- | :--- | :--- |
| **Tool Calls** | `registry.call("tool_name")` | `domain.call("tool_name")` | Update to Hierarchical calls |
| **Context** | Vector-based | Graph-based | Re-index codebase with `stack-graph` |
| **Tasking** | Flat Task List | Task Dependency Graph | Update task creation logic |
| **Model** | 1.5B Single | Lite/Pro/Ultra | Choose variant based on VRAM |

## 🛠️ Step-by-Step Migration

### 1. Model Upgrade
Replace your `Stack-2-9-finetuned` loading logic with the new variant of your choice.
**Recommended:** Use `Stack-3-0-Pro` for a seamless balance of performance and hardware requirements.

### 2. Updating Tool Implementation
In v2.9, you called tools directly. In v3.0, you must specify the domain or allow the model to route.

**Legacy (v2.9):**
```python
# Flat call
result = await registry.call("grep", {"pattern": "main"})
```

**New (v3.0):**
```python
# Hierarchical call
# The agent now first enters the 'CodeIntelligence' domain
result = await agent.call_domain("CodeIntelligence", "grep", {"pattern": "main"})
```

### 3. Re-indexing for Graph-RAG
v3.0 does not use the same index format as v2.9. You must generate a new knowledge graph for your project.
```bash
# Install the new indexing tool
pip install stack-graph

# Index your codebase
stack-graph index --path ./src --output ./graph_db
```

### 4. Task Management Evolution
`TaskCreate` now supports a `blocks` parameter to define the Dependency Graph.
```python
# v2.9: Sequential tasks
await task_create("Step 1: Analysis")
await task_create("Step 2: Implementation")

# v3.0: Graph-based tasks
await task_create("Step 1: Analysis")
await task_create("Step 2: Implementation", blocks=["task_id_1"])
```

## ⚠️ Troubleshooting Common Issues
- **"DomainNotFound Error":** Ensure you have initialized the `DomainRouter` before calling tools.
- **"GraphQueryTimeout":** If your codebase is massive ($>1\text{M}$ lines), increase the `graph_timeout` in `config.json`.
- **VRAM Spikes:** If using `Stack-3-0-Pro`, ensure you are using 4-bit quantization if your VRAM is below 24GB.
