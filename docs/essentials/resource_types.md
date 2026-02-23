# Resource Types

This page provides an overview of all available resource types in Microsoft Fabric CLI, including item types and virtual item types. Understanding these types helps you navigate, manage, and automate resources efficiently.

---

## Item Types

Item types are the primary content resources within Fabric workspaces. Each type has a unique extension and supports specific operations.

| Extension              | Description                        |
|------------------------|------------------------------------|
| `.Notebook`            | Analytical notebooks               |
| `.SparkJobDefinition`  | Spark job definitions              |
| `.DataPipeline`        | Data integration pipelines         |
| `.Report`              | Power BI reports                   |
| `.SemanticModel`       | Data models                        |
| `.KQLDatabase`         | Kusto databases                    |
| `.KQLDashboard`        | Kusto dashboards                   |
| `.KQLQueryset`         | Kusto query collections            |
| `.Lakehouse`           | Data lakehouse storage             |
| `.Warehouse`           | Data warehouses                    |
| `.SQLDatabase`         | SQL databases                      |
| `.MirroredDatabase`    | Mirrored databases                 |
| `.MirroredWarehouse`   | Mirrored data warehouses           |
| `.Eventhouse`          | Real-time analytics databases      |
| `.Eventstream`         | Real-time data streams             |
| `.Dashboard`           | Interactive dashboards             |
| `.Datamart`            | Self-service data marts            |
| `.CopyJob`             | Data copy operations               |
| `.Environment`         | Spark environments                 |
| `.MLExperiment`        | Machine learning experiments       |
| `.MLModel`             | Machine learning models            |
| `.MountedDataFactory`  | Mounted Data Factory resources     |
| `.PaginatedReport`     | Paginated reports                  |
| `.Reflex`              | Application development platform   |
| `.SQLEndpoint`         | SQL connection endpoints           |
| `.VariableLibrary`     | Variable libraries                 |
| `.GraphQLApi`          | GraphQL API endpoints              |
| `.Dataflow`            | Dataflow API endpoints             |
| `.ApacheAirflowJob`    | Apache Airflow job definitions     |
| `.CosmosDBDatabase`    | Cosmos DB databases                |
| `.DigitalTwinBuilder`  | Digital twin builder resources     |
| `.GraphQuerySet`       | Graph query collections            |
| `.UserDataFunction`    | User data functions                |

---

## Workspace Virtual Item Types

Workspace virtual item types are infrastructure or system resources that exist within the context of a specific workspace. They are not visible as regular items but are essential for advanced management and automation within a workspace.

| Extension                  | Description                        |
|----------------------------|------------------------------------|
| `.ExternalDataShare`       | Cross-tenant data sharing          |
| `.ManagedIdentity`         | Service authentication             |
| `.ManagedPrivateEndpoint`  | Private network access             |
| `.SparkPool`               | Dedicated Spark compute resources  |

---

## Tenant Virtual Item Types

Tenant virtual item types are infrastructure or system resources that exist at the tenant (organization) level. They provide shared capabilities and governance across all workspaces.

| Extension        | Description                        |
|------------------|------------------------------------|
| `.Capacity`      | Fabric capacity resources          |
| `.Connection`    | Data source connections            |
| `.Domain`        | Fabric domains                     |
| `.Gateway`       | On-premises data gateways          |
| `.Workspace`     | Fabric workspaces                  |

---

## Item Folders (OneLake Storage)

Certain item types expose **folders** that represent OneLake storage entities. These folders act as top-level directories inside an item and give you file-system-like access to the data stored within it. You can `cd` into them, use `ls` to list their contents, `get` to retrieve metadata, and perform other file operations depending on whether the folder is writable.

### What Are Item Folders?

When you navigate into a supported item (e.g., a Lakehouse), the CLI presents its internal storage structure as folders. Each folder maps to a distinct storage area within the item:

```
/workspace1.Workspace/myLakehouse.Lakehouse/
├── Files/            ← Unstructured file storage (writable)
├── Tables/           ← Managed Delta tables (read-only)
└── TableMaintenance/ ← Table maintenance operations
```

These folders are **not** regular workspace folders — they are OneLake storage partitions tied to the item type.

### Supported Item Types and Their Folders

The table below lists every item type that exposes folders, along with the folders available and their read/write status.

| Item Type              | Folder             | Writable | Description                                |
|------------------------|--------------------|---------:|--------------------------------------------|
| **Lakehouse**          | `Files`            | ✅       | Unstructured file storage                  |
|                        | `Tables`           | ❌       | Managed Delta tables                       |
|                        | `TableMaintenance` | ❌       | Table maintenance job scope                |
| **Warehouse**          | `Files`            | ✅       | File storage                               |
|                        | `Tables`           | ❌       | Warehouse tables                           |
| **SemanticModel**      | `Tables`           | ❌       | Model tables (requires explicit enablement)|
| **SparkJobDefinition** | `Libs`             | ✅       | Dependency libraries for Spark jobs        |
|                        | `Main`             | ✅       | Main executable files                      |
|                        | `Snapshots`        | ❌       | Snapshot history                           |
| **KQLDatabase**        | `Tables`           | ❌       | Kusto tables (requires explicit enablement)|
|                        | `Shortcut`         | ❌       | Kusto shortcuts                            |
| **MirroredDatabase**   | `Files`            | ✅       | File storage                               |
|                        | `Tables`           | ❌       | Mirrored tables                            |
| **MirroredWarehouse**  | `Files`            | ✅       | File storage                               |
|                        | `Tables`           | ❌       | Mirrored warehouse tables                  |
| **SQLDatabase**        | `Tables`           | ❌       | SQL tables                                 |
|                        | `Files`            | ✅       | File storage                               |
|                        | `Code`             | ❌       | SQL code objects                           |
| **CosmosDBDatabase**   | `Tables`           | ❌       | Cosmos DB tables                           |
|                        | `Files`            | ✅       | File storage                               |
|                        | `Code`             | ❌       | Code objects                               |
|                        | `Audit`            | ❌       | Audit data                                 |

!!! tip "Writable Folders"
    Only the following folder names are writable across all item types: **`Files`**, **`Libs`**, and **`Main`**. All other folders (e.g., `Tables`, `Snapshots`, `Code`, `Audit`) are **read-only** — you can browse and query them, but cannot upload or create files in them.

### Navigating Item Folders

Use standard CLI navigation commands to interact with item folders:

```bash
# Navigate into an item's folder
fab cd ws1.Workspace/lh1.Lakehouse/Files

# List folder contents
fab ls ws1.Workspace/lh1.Lakehouse/Files

# List top-level folders of an item
fab ls ws1.Workspace/lh1.Lakehouse

# Get metadata for a folder or file
fab get ws1.Workspace/lh1.Lakehouse/Files/my-data.csv

# Create a subfolder (writable folders only)
fab mkdir ws1.Workspace/lh1.Lakehouse/Files/raw-data

# Upload a file (writable folders only)
fab cp /tmp/data.csv ws1.Workspace/lh1.Lakehouse/Files/

# Remove a file or folder (writable folders only)
fab rm ws1.Workspace/lh1.Lakehouse/Files/old-data
```

!!! info "Read-Only Folders"
    Attempting to write to a read-only folder (e.g., `Tables`) will result in an error. Use `ls` and `get` to browse and inspect their contents.

For more examples, see [OneLake Examples](../examples/onelake_examples.md) and [Item Examples](../examples/item_examples.md).

---


See how to describe types using [Describe (desc) command](../examples/desc_examples.md).

