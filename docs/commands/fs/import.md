# `import` Command

!!! note "Prefer `cp`"
    The `import` command is superseded by [`cp`](cp.md). Use `cp` for all import workflows.

    ```
    # Old
    fab import ws.Workspace/nb.Notebook -i /tmp/nb.Notebook -f

    # New (equivalent)
    fab cp /tmp/nb.Notebook ws.Workspace/nb.Notebook -f
    ```

    See [`cp` command reference](cp.md) for full documentation.

---

Import an item (create/modify).

!!! warning "When importing, the item definition is imported without its sensitivity label"

**Supported Types:**

- All workspace item types that support definition import (e.g., `.Notebook`, `.Report`, etc.)

**Usage:**

```
fab import <path> -i <input_path> [--format <format>] [-f]
```

**Parameters:**

- `<path>`: Path to import to.
- `-i, --input <input_path>`: Input path.
- `--format <format>`: Format of the item definition to import. Supported only for Notebooks (`.ipynb`, `.py`), Semantic Models (`TMDL`, `TMSL`) and Spark Job Definition (`SparkJobDefinitionV1`, `SparkJobDefinitionV2`). Optional.
- `-f, --force`: Force import without confirmation. Optional.

**Example:**

```
fab import ws2.Workspace -i C:\Users\myuser\nb1.Notebook
```
