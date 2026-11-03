<!-- Copyright (c) Microsoft Corporation. Licensed under the MIT License. -->

# Bounded GET option support

This slice follows Python
`cf67fd52ea8b47e24c725e73d792de6f4a08e2e4`, not the current Python checkout.
The metadata-only entry and the explicitly injected definition/output entry have
different capability requirements. Neither establishes live-service acceptance.

## Metadata-only entry

`ReadSession::dispatch` and `ReadHost::dispatch` retain this bounded option policy.
The explicitly selected native host uses the definition/output entry instead.

| Target/options | Implemented behavior |
| --- | --- |
| Workspace GET with `--force`, `--verbose`, or both | Existing workspace retrieval/enrichment and query, unchanged output |
| Item GET with a metadata-property query and either/both flags | Existing specialized metadata endpoint and query, without definition confirmation or sensitivity warning |
| Item GET without a metadata-property query and either flag | Explicit `NotSupported` after target discovery, before metadata/definition retrieval |
| Any `--output`, including a present empty value | Explicit `NotSupported` before discovery or file access; never silently ignored |
| No options | Existing read path, including its previously documented gaps |

The source metadata check is an exact, case-sensitive root split at the first
dot. Recognized roots are `id`, `type`, `displayName`, `description`,
`workspaceId`, `folderId`, and `properties`. For example, `properties.nested`
is metadata; `properties[0]`, `Properties`, `.`, and an absent/empty query are
not. This is intentionally not an AST-based JMESPath classifier.

The pinned parser describes `--verbose` as showing all JSON properties, but its
value is never consumed by the GET dispatch, handlers, query helper or error UI.
The handlers' separate `verbose=True` parameter controls printing, and
`deep_traversal` controls path inventory. Neither comes from `args.verbose`.
The bounded host preserves that source behavior rather than inventing deeper
traversal or verbose service-error disclosure. `--force` is similarly inert for
workspace and metadata-only item GET, where no definition prompt occurs.

## Definition and projected-output entry

`fabric_cli::session::get_options::is_metadata_property_query` exposes the source
classifier. `ReadSession::execute_get` / `dispatch_get` and
`ReadHost::execute_get` accept an explicit `GetHost` with the caller's existing
operation executor, confirmation/progress UI, optional `TransferFiles`, local
timestamp, newline policy and finite limits. They share one orchestration path.
They do not discover credentials, create a runtime, access an ambient clock or
replace specialized metadata with generic metadata.

`ClockedGetHost` and `ReadSession::dispatch_get_clocked` alternatively accept a
caller-owned asynchronous `GetOutputClock`. The clock runs after projection and
output-directory resolution, never for absent/empty output. Clock failure is a
failure, not permission to substitute a UTC or epoch filename. The caller-owned
`GetEvidence` also retains observed effects if a bounded host drain expires.

Definition-supported items require consent before metadata acquisition, unless
`--force` explicitly selects the warning-only branch. Metadata-property queries
bypass that consent and definition acquisition, but still retrieve connections,
schedules and applicable type-specific metadata. Parsed verbose remains inert.
Definition acquisition uses the shared `read_definition` / operation session,
then `decode_get_definition_value`, then enrichment and the existing query
provider. Successful decoding sets `payloadType` to `DecodeBase64`; it does not
remove that field. Metadata-only acquisition preserves encoded payloads.

The shared synchronous operation policy fetches `/operations/<id>/result` only
when the **terminal polling response** has a nonempty `Location` header.
Without that header it returns the original accepted body with status 200.
An initial response's location alone does not select result retrieval. GET does
not replay the definition POST or install a second polling loop.

GET `--output` writes the **projected result**, even when empty, not definition
parts and not an output envelope. The pinned storage path is
`<output>/<full_name>/get_<local timestamp>`. Local and Lakehouse JSON each receive
exactly one `.json` suffix. `do_output` adds a suffix only to its displayed
message; the storage writer receives the unsuffixed path and appends the actual
suffix. Local output uses pretty Unicode JSON and explicit native newlines;
Lakehouse output uses default ASCII JSON.

The shared query provider preserves objects/lists but stringifies ordinary
scalar query results before storage classification: queried zero becomes `"0"`
and receives `.json`; queried false and null become `"False"` and `"None"` and
remain unsuffixed text. An identity query (`.`) preserves the input value's type.
Empty strings/containers are quiet on stdout but still written with nonempty
`--output`; a present empty output selects stdout instead of granting file
authority.

`GetEvidence` retains accepted operation IDs, possible remote effects,
best-effort enrichment failures, definition access denial and completed or
possibly partial file effects. Negative consent is a quiet no-op; EOF/UI errors,
cancellation, codec-domain failures, file failures and failed stream delivery
remain failures. Cancellation is not rollback.

## Native availability

The `native-read` and `headless` source composition selects
`ReadSession::dispatch_get_with_storage` for GET, using its existing SDK session,
HTTP/operation executor and current-thread runtime. Non-GET dispatch remains on
the existing read/job/family paths. Native output reuses the classified
local/Lakehouse adapter; authentication and service failures never authorize
local fallback. The deferred local worker resolves cwd and native tilde inputs
only when local output is selected. Unix current-user tilde uses an absolute
`HOME`; named-user tilde is explicitly unsupported.

Native GET signals cancellation cooperatively and drains for at most two
seconds before the existing bounded runtime shutdown. Typed operation errors,
accepted IDs and completed/possibly partial files remain owned through the final
one-shot stdout/stderr write. A final writer error preserves its original
`io::ErrorKind` and typed `GetWriteFailure`; no retry or rollback is implied.
The original unconfigured/default-host contract remains unchanged.

The new native GET composition tests require a fresh controller-granted run;
earlier metadata/library receipts do not validate this revision. GET identity
binding validates the exact tenant/account/client/provider selection without
initializing navigation or reading cwd. A later non-GET command with the same
identity initializes its actual navigation normally. The isolated Unix
missing-cwd test and injected remote-output tests require execution before
claiming missing-cwd acceptance. Source availability is not a passed native
acceptance gate.
Unsupported binary/wide/nonfinite/surrogate projection domains remain explicit
failures, not silent conversion. Live identity/service and cross-platform
acceptance remain unrun gates, not a GA claim.

## Typed dispatch evidence

The metadata-only `ReadSession` and its `SourceOperationReadSession` wrapper
also expose `dispatch_with_evidence`. The returned `ReadDispatch` contains the
unchanged `TextPlan` and an optional original `CommandError`. A rendered command
failure retains that error directly; callers do not need to infer cancellation
or unexpected-error classification from output text or numeric exit status.
Source-synchronous workspace failures additionally retain their original
`OperationError` in `operation_error`, including its typed cause, accepted
operation ID, exact raw terminal error and uncertain-effects flag. The command
error is projected through the same existing CLI policy; the rendered operation
envelope is unchanged. The original operation is never reconstructed from that
projection. The metadata-only legacy entry uses the same workspace algorithm
without requiring callers to consume the additional evidence.
Success and quiet no-op reads have no command error, and quiet reads retain an
empty successful plan. Rendering failures remain `Err(TextError)`, including any
partial output. Existing `dispatch` methods delegate and return only the plan,
preserving their signatures, stream contents and exit behavior.

This additive metadata-only evidence API does not change SDK request/response
behavior. Native definition GET separately retains its `GetDispatch` rather than
flattening it into this metadata-only result.

## Offline evidence

From `rust/`, the isolated source helper is:

```text
python -I -B hosts\cli\fabric-cli\tests\test_get_options_source.py
```

It executes selected unchanged functions from the exact Git object with explicit
offline dependencies, never imports the product, and reports pinned versus
current-checkout SHA-256 values separately. It observes metadata classification,
confirmation bypass, decline/EOF/force behavior, inert verbose handling,
query/output precedence, writer failures and isolated storage behavior.
It does not replace or regenerate protected fixtures or baselines.

The end-to-end source helper additionally exercises projection before storage,
single-suffix output, decoded payload types and terminal-location reconciliation:

```text
python -I -B hosts\cli\fabric-cli\tests\test_get_host_source.py
```

The Rust integration targets `fabric-cli --test get_options --test get_host` deny
`unnameable_test_items` and cover the real session/direct host, byte-for-byte
option/no-option output, specialized SDK requests, consent, shared reconciliation,
definition decoding, scalar/container projection, output filenames/newlines,
invalid format, cancellation, partial effects, service errors and failed writers.
Rust compilation/execution and independent review remain controller validation
requirements, not evidence supplied by formatting or the Python source helper.
The binary unit-test selector `native_read::get::tests` covers the mounted native
GET with injected offline HTTP, its classified storage, lazy clock, typed
cancellation and final failed writer. Run it for both `headless` and
`native-read`; it does not use live credentials or service operations.
