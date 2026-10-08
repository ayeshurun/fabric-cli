# Commands

Commands in `fab` are organized into logical groups based on their functionality, making it easy to find and use the right command for your task.

## Understanding CLI Commands

A CLI command in Fabric follows this general structure:

```
fab [command-group] [command] <arguments> [parameters]
```

Where:

- `fab` is the base CLI command
- `command-group` is the group of related commands (like fs, acls, table)
- `command` is the specific operation to perform
- `arguments` are required positional values needed by the command
- `parameters` are optional named options that modify the command behavior

## Command Groups

### Core Command Groups

#### File System Operations (fs)
File system (fs) commands provide a familiar interface for managing workspaces, items, and files using commands similar to traditional file system operations. 

It supports both Unix-style and Windows-style command names for file system operations. You can use whichever style you're most familiar with - both versions will work the same way regardless of your operating system:

| Unix Style | Windows Style | Description |
|------------|---------------|-------------|
| `mkdir` | `mkdir` | Create resources |
| `ls` | `dir` | List resources |
| `cp` | `copy` | Copy resources |
| `mv` | `move` | Move resources |
| `rm` | `del` | Delete resources |
| `ln` | `mklink` | Create shortcuts |


**Supported Types:**

- All workspace item types (e.g., `.Notebook`, `.Lakehouse`, `.Warehouse`, `.Report`, etc.)
- OneLake storage sections (e.g., `Files`, `Tables`)
- Some virtual item types for navigation (e.g., `.Workspace`)

**Available Commands:**

| Command | Description |
|---------|-------------|
| [`assign`](./fs/assign.md) | Assign a resource to a workspace |
| [`bulk-export`](./fs/bulk_export.md) | Export Folder or Workspace items in bulk |
| [`cd`](./fs/cd.md) | Change to the specified directory |
| [`cp` (copy)](./fs/cp.md) | Copy an item or file | 
| [`export`](./fs/export.md) | Export an item |
| [`exists`](./fs/exists.md) | Check if a workspace, item, or file exists |
| [`get`](./fs/get.md) | Get a workspace or item property | 
| [`import`](./fs/import.md) | Import an item (create/modify) |
| [`ln` (mklink)](./fs/ln.md) | Create a shortcut | 
| [`ls` (dir)](./fs/ls.md) | List workspaces, items, and files | 
| [`mkdir` (create)](./fs/mkdir.md) | Create a new workspace, item, or directory |
| [`mv` (move)](./fs/mv.md) | Move an item or file |
| [`open`](./fs/open.md) | Open a workspace or item in browser |
| [`pwd`](./fs/pwd.md) | Print the current working directory |
| [`rm` (del)](./fs/rm.md) | Delete a workspace, item, or file |
| [`set`](./fs/set.md) | Set a workspace or item property |
| [`start`](./fs/start.md) | Start a resource |
| [`stop`](./fs/stop.md) | Stop a resource |
| [`unassign`](./fs/unassign.md) | Unassign a resource from a workspace |
| [`deploy`](./fs/deploy.md) | Deploy Fabric workspace items from local source content into a target Microsoft Fabric workspace. |

#### [Table Management (table)](tables/index.md)
Commands for working with tables in lakehouses, including operations like loading data, optimizing tables, and managing schemas.

#### [Jobs Management (job)](jobs/index.md)
Manage and monitor various job operations, including starting, running, and scheduling tasks.

### Security and Access Command Groups

#### [Access Control List (acls)](acls/index.md)
Manage permissions and access control lists for workspaces and items.

#### [Sensitivity Labels (label)](labels/index.md)
Work with sensitivity labels to protect and classify your data.

### Configuration and Authentication Command Groups

#### [Authentication (auth)](auth/index.md)
Handle authentication with Microsoft Fabric services.

#### [Configuration (config)](config/index.md)
Manage CLI configuration settings and preferences.

### Additional Command Groups

#### [API Operations (api)](api/index.md)
Make authenticated API requests directly to Fabric services.

## Global parameters

The following parameters are available for all commands:

- `-h, --help`: Display help information for the command
- `--output_format`: Specify the output format (`text` or pretty-printed `json`).
- `--json`: Select compact, single-line JSON.

Both JSON formats use the same `timestamp`, `status`, `command`, and `result` envelope. Command data is wrapped in the `result.data` list: scalar values, including `null`, become `[value]`, objects become `[object]`, and an empty list stays `[]`. Messages and `hidden_data` remain outside the projected data.

You can place `--json` before a command, command group, or leaf command (the final subcommand). The deepest command level with an explicit output flag takes precedence; at the same level, the last output flag wins. For predictable results, place output flags after the leaf command.

## Common parameters

Most commands support a set of common parameters:

- `-f, --force`: Force operations without confirmation
- `-o, --output`: Specify output file path
- `-i, --input`: Specify input file path or value
- `-q, --query EXPRESSION`: Project command data using a JMESPath expression.

### Query behavior

Leaf commands without an existing query option support `-q, --query EXPRESSION` to project their structured data before the `result.data` wrapper. Each projection applies once. Commands with existing query options retain their semantics:

- [`ls` (dir)](./fs/ls.md) and [`acl ls`](./acls/index.md) query the resource list before selecting display columns.
- [`get`](./fs/get.md) and [`acl get`](./acls/index.md) enumerate properties when no query is supplied. Use `-q '.'` or `-q '@'` to return the full payload.
- [`set`](./fs/set.md) still requires `-q` to select the mutation target, not project output.
- [`api`](./api/index.md) queries its response object, including `status_code`, `text`, and any additional response fields.

Queries do not filter envelope status, errors, messages, or `hidden_data`. HTTP failures remain failures and are not projected; existing diagnostics remain on standard error (`stderr`). A projected result does not indicate how many resources were omitted.

Queries reduce local output, not API requests or data transfer. Existing defaults remain unchanged. These flags affect structured results, not arbitrary text, exported file content, or interactive prompts.

### JSON and query examples

```bash
# List configuration setting names as compact JSON
fab config ls --json -q '[].setting'

# List capacity names as compact JSON
fab ls .capacities --json -q '[].name'

# Return the full notebook payload as compact JSON
fab get ws.Workspace/f.Folder/n.Notebook --json -q '.'

# Return the same configuration projection as pretty-printed JSON
fab config ls --output_format json -q '[].setting'
```

## Getting Help

You can get help about any command using:
```
fab [command-group] --help
fab [command-group] [command] --help
```

For detailed examples and usage patterns, see the individual command group pages linked above.
