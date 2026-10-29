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

## Global Parameters

The following parameters are available for all commands:

- `-h, --help`: Display help information for the command
- `--output_format`: Specify the output format (`text` or `json`).

## Common Parameters

Most commands support a set of common parameters:

- `-f, --force`: Force operations without confirmation
- `-o, --output`: Specify output file path
- `-i, --input`: Specify input file path or value
- `-q, --query`: Filter output using JMESPath queries

## Getting Help

You can get help about any command using:
```
fab [command-group] --help
fab [command-group] [command] --help
```

For detailed examples and usage patterns, see the individual command group pages linked above.

### Machine-readable help

Request JSON help explicitly with `--output_format json`. Existing text help remains the default, even when your configuration selects JSON. The format option can appear before or after `--help`:

```bash
# Describe the root, a group, or a command
fab --help --output_format json
fab job --help --output_format json
fab job run --output_format json --help

# Use equals syntax
fab job run --help --output_format=json

# Inherit the root format option for help only
fab --output_format json job run --help
```

Root-level `--output_format` before a command is inherited for help only, not command execution. Discovery needs no required arguments or authentication, runs no command, and makes no network requests. Successful JSON help writes only JSON to standard output and exits with code zero. It excludes hidden flags, parsed runtime values, and credentials.

The document contains static metadata:

- **Identity:** `schema_version` is `"1.0"`; `cli_version` identifies the CLI version. `name`, canonical `command`, `description`, and `aliases` identify the command. Alias requests normalize to the canonical command.
- **Discovery:** `subcommands` lists immediate children with their names, canonical commands, descriptions, and aliases. Request JSON help for each child's `command` recursively to discover the command tree.
- **Inputs:** `inputs` describes parser declarations through `name`, `flags`, `kind`, `description`, `required`, `default`, `default_suppressed`, `choices`, `nargs`, `multiple`, `repeatable`, `type`, and optional `constraints`. Types describe each value; multiplicity is separate. `nargs: null` means one value; `nargs: 0` means a flag taking no value. Unknown custom types remain `unknown`, with a `validator` name rather than an inferred type. The positive-integer validator explicitly declares integer type and `constraints.minimum: 1`.
- **Outputs:** `outputs` describes command execution, not the help document. `exists`, `config get`, `config ls`, and `api` declare text and JSON formats with partial success JSON schemas (`schema_status: "partial"`). `version` is text-only, with `schema: null` and `schema_status: "not_applicable"`. Remaining commands have `formats: null`, `schema: null`, and `schema_status: "unknown"`; the format flag does not establish JSON support.
- **Errors:** `common_errors` provides nonexhaustive CLI-wide examples with recovery guidance. `errors_scope` states their limits; service APIs can return additional codes. Separate `exit_codes` describes process exit codes. Runtime errors remain unchanged.

This is initial metadata coverage, not a complete typed output contract. Use `schema_version` to interpret the document and tolerate added fields.
