# `cp` / `copy` Command

Copy an item, a folder or a file.
The behavior of the `cp` command varies depending on the source (item or folder) and the destination path.

!!! warning "When copying an item, the item definition is copied without its sensitivity label"

**Supported Types:**

- All workspace item types that support definition export/import (e.g., `.Notebook`, `.Report`, etc.)
- OneLake files and folders
- Local file system directories (import/export)

**Usage:**

```
fab cp <from_path> <to_path> [-r] [-f] [-bpc] [--format <format>]
```

**Parameters:**

- `<from_path>`: Source path. Can be a Fabric path or a local file system path.
- `<to_path>`: Destination path. Can be a Fabric path or a local file system path.
- `-r, --recursive`: Copies all items in the source path recursively, including subfolders and their contents. Only applicable for Fabric→Fabric workspace/folder copies. Optional.
- `-f, --force`: Force copy without confirmation. Optional.
- `-bpc, --block_on_path_collision`: Block on path collision. Prevents copying when an item with the same name exists in a different folder within the target workspace. Only applicable for Fabric→Fabric copies. Optional.
- `--format <format>`: Format of the item definition (e.g., `.ipynb`, `.py` for Notebooks; `TMDL`, `TMSL` for Semantic Models; `SparkJobDefinitionV1`, `SparkJobDefinitionV2` for Spark Job Definitions). Applicable for local↔Fabric copies. Optional.


## Flag Applicability

| Flag | Fabric→Fabric | Fabric→Local (export) | Local→Fabric (import) |
|------|:---:|:---:|:---:|
| `-r, --recursive` | ✅ | — | — |
| `-f, --force` | ✅ | ✅ | ✅ |
| `-bpc, --block_on_path_collision` | ✅ | — | ✅ |
| `--format` | — | ✅ | ✅ |


## Limitations

- When copying a folder, items that do not support the copy operation are skipped. Only supported items will be copied.
- When copying an item to the same workspace, `_copy` is automatically appended to the item name to avoid conflicts.


## Examples

### Fabric to Fabric

```bash
# copy items from one workspace to another
fab cp ws1.Workspace ws2.Workspace

# copy a notebook between workspaces
fab cp ws1.Workspace/nb1.Notebook ws2.Workspace

# copy all items recursively (including folders)
fab cp ws1.Workspace ws2.Workspace -r -f

# copy a OneLake file
fab cp Files/csv/data.csv Files/dest/data_copy.csv
```

### Fabric to Local (export)

```bash
# export a single item to a local directory
fab cp ws1.Workspace/nb1.Notebook /tmp

# export a single item to home directory
fab cp ws1.Workspace/nb1.Notebook ~/exports

# export with a different local name
fab cp ws1.Workspace/nb1.Notebook /tmp/MyRenamed.Notebook

# export a notebook as .py format
fab cp ws1.Workspace/nb1.Notebook /tmp --format .py

# export items from a workspace (interactive selection)
fab cp ws1.Workspace /tmp -f
```

### Local to Fabric (import)

```bash
# import a local item to a workspace (item name derived from directory)
fab cp /tmp/MyNotebook.Notebook ws1.Workspace

# import a local item to a specific item path
fab cp /tmp/MyNotebook.Notebook ws1.Workspace/MyNotebook.Notebook

# import with a different name in Fabric
fab cp /tmp/MyNotebook.Notebook ws1.Workspace/RenamedNotebook.Notebook

# import from home directory
fab cp ~/exports/MyNotebook.Notebook ws1.Workspace -f

# import with a specific format
fab cp /tmp/MyNotebook.Notebook ws1.Workspace/nb.Notebook --format .py
```


## Migrating from `import` / `export`

The `cp` command replaces the standalone `import` and `export` commands with a unified syntax.

| Old command | Equivalent `cp` command |
|---|---|
| `export nb1.Notebook -o /tmp` | `cp nb1.Notebook /tmp` |
| `export nb1.Notebook -o /tmp --format .py` | `cp nb1.Notebook /tmp --format .py` |
| `import nb1.Notebook -i ~/nb1.Notebook` | `cp ~/nb1.Notebook nb1.Notebook` |
| `import nb1.Notebook -i ~/nb1.Notebook -f` | `cp ~/nb1.Notebook nb1.Notebook -f` |
| `import nb1.Notebook -i ~/nb1.Notebook --format .py` | `cp ~/nb1.Notebook nb1.Notebook --format .py` |
