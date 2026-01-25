# Settings

The Fabric CLI provides a comprehensive set of configuration settings that allow you to customize its behavior, performance, and default values. All settings persist across CLI sessions, except for `mode` and `encryption_fallback_enabled`.

## Available Settings

| Name                           | Description                                                                                 | Type       | Default |
|--------------------------------|-------------------------------------------------------------------------------------------- |------------|---------|
| `cache_enabled`                | Toggles caching of CLI HTTP responses                           | `BOOLEAN`  | `true`  |
| `check_cli_version_updates`                | Enables automatic update notifications on login                                            | `BOOLEAN`  | `true`  |
| `debug_enabled`                | Toggles additional diagnostic logs for troubleshooting                                   | `BOOLEAN`  | `false` |
| `context_persistence_enabled`  | Persists CLI navigation context in command line mode across sessions | `BOOLEAN` | `false` |
| `encryption_fallback_enabled`  | Permits storing tokens in plain text if secure encryption is unavailable                  | `BOOLEAN`  | `false` |
| `job_cancel_ontimeout`         | Cancels job runs that exceed the timeout period                                  | `BOOLEAN`  | `true`  |
| `local_definition_labels`      | Indicates the local JSON file path for label definitions mapping                 | `VARCHAR`  |         |
| `mode`                         | Determines the CLI mode (`interactive` or `command_line`)              | `VARCHAR`  | `command_line` |
| `output_item_sort_criteria`    | Defines items output order (`byname` or `bytype`)               | `VARCHAR`  | `byname`|
| `show_hidden`                  | Displays all Fabric elements                                                               | `BOOLEAN`  | `false` |
| `default_az_admin`             | Defines the default Fabric administrator email for capacities  | `VARCHAR`  |         |
| `default_az_location`          | Defines the default Azure location for capacities            | `VARCHAR`  |         |
| `default_az_resource_group`    | Defines the default Azure resource group for capacities        | `VARCHAR`  |         |
| `default_az_subscription_id`   | Defines the default Azure subscription for capacities          | `VARCHAR`  |         |
| `default_capacity`             | Defines the default Fabric capacity for `mkdir`        | `VARCHAR`  |         |
| `default_open_experience`      | Defines the default Fabric portal user experience (`fabric` or `powerbi`)                 | `VARCHAR`  | `fabric` |
| `output_format`                | Defines the CLI output format (`text` or `json`)                 | `VARCHAR`  | `text` |
| `folder_listing_enabled`       | Enables recursive folder listing when using `ls` command            | `BOOLEAN`  | `false` |
| `workspace_private_links_enabled`      | Enables workspace private links support in `api` command                | `BOOLEAN`  | `false` |

## Debug Logging

Debug logging can be enabled in two ways:

1. **Using the `--debug` global flag**: Add `--debug` after the command to enable debug logging for a single command execution.
   ```
   fab ls / --debug
   ```

2. **Using the `debug_enabled` config setting**: Set `debug_enabled` to `true` to enable debug logging for all CLI commands.
   ```
   fab config set debug_enabled true
   ```

When debug logging is enabled:
- Debug messages are printed to the console with a `[debug]` prefix
- All debug logs are saved to a log file (location shown when debug is enabled)
- HTTP request/response details are logged for troubleshooting API issues

## Managing Settings

You can view and modify these settings using the following commands:

```
# List all current settings
fab config ls

# Get a specific setting value
fab config get <setting_name>

# Set a new value for a setting
fab config set <setting_name> <value>
```

For detailed examples, see the [Configuration Examples](../examples/config_examples.md).