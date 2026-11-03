<!-- Copyright (c) Microsoft Corporation. Licensed under the MIT License. -->

# Experimental Windows broker lifecycle

This optional native boundary backs `fabric-identity/windows-broker`. It does
not select a production identity backend or establish MFA, Conditional Access,
guest-account, alias, packaging or service acceptance. Authentication/core team
review and separately authorized native and live evidence remain required.

## Credential API and local logout

The existing `WindowsCredential::login(options, allow_interaction)`,
`WindowsCredential::connect(options)`, Azure `TokenCredential::get_token` and
`fabric_identity::sign_out(options)` signatures are unchanged. Only explicit
login permission can authorize UI. Connect requests Fabric only. Login requests
Fabric, OneLake and ARM in order, and publishes no partial credential. SDK
refresh remains silent and native-account pinned. Metadata is historical, not a
fresh status check. SDK credentials remain caller-injected; SDKs do not depend
on this identity implementation.

`WindowsCredential::status(options)` silently checks all three login audiences
using read-only lifecycle admission: it cannot reopen signed-out or unconfirmed
state and rejects those states before broker work. It is not equivalent to
`login(options, false)`: the latter is an explicit login that may reopen confirmed
sign-out while still forbidding UI. Interaction permission never determines
whether an action is an explicit login. CLI hosts must route status to `status`,
not to a no-interaction login.

These credential entry points share a process-local coordinator. Its keys are
the fixed public-cloud provider namespace, explicit tenant/client GUIDs and
ASCII-case-folded UPN. Tenant keys sharing provider/client/UPN join one
operation/invalidation domain **before** their first acquisition. Validated
equal native IDs join same-client domains conservatively, without releasing
active native reservations or discarding logout generations. No alias discovery
or guest mapping is performed.

Logout linearizes on its first poll: it invalidates existing credentials before
waiting for native work. Constructing and dropping an unpolled logout does
nothing. Token/credential publication linearizes at the final locked domain and
native-ID generation check, not at a broker callback. A success buffered before
logout but not yet published is rejected. A token published before that check
cannot be recalled.

Logout cancels prior matching operations and waits up to five seconds for actual
teardown before starting native app/client sign-out. Failure, cancellation,
deadline or unknown cleanup leaves old credentials invalid and local state
unconfirmed. Explicit same-identity logout retry is required before reopening
through explicit login. Silent connect and an old credential cannot reopen the
session. Even a later successful login does not rehabilitate old objects.

Native logout pins the original validated account ID when known. A missing
original account is idempotent absence; a different same-UPN account is rejected
rather than selected. For an identity never acquired locally, lookup still
requires today's unique explicit UPN contract. The broad same-client publication
barrier is transient: confirmed absence means no native account sign-out occurred,
and releases that barrier after actual teardown without reopening the selected
domain. A found native ID retains its precise account/client invalidation.
If logout fails or is dropped, confirmed late teardown likewise releases the
broad barrier, but leaves the selected domain unconfirmed and its old credentials
invalid. Uncertain or still-active cleanup does not expire on a timer.

A retained client publication cutoff rejects acquisitions admitted before
or during unresolved logout **without a previously confirmed native binding**,
including aliases whose native ID arrives only after confirmed absence.
Binding knowledge is captured at admission, not learned from the operation's
own response. A previously bound, distinct principal's overlapping refresh can
publish after confirmed absence without retry or logging in the absent selection.
Precise native-ID and selected-domain invalidation checks always apply, even
to previously bound requests whose ID matches a found logout target.
The cutoff applies to unbound operation admission, not older credential objects.
While cleanup is unresolved, same-client publication fails cleanup-pending.
Other client registrations remain isolated. No equivalence is inferred for an
unknown future principal; alias support and cross-process revocation remain
outside this contract.

This is **in-process application-account invalidation**, not cross-process access
token revocation. WAM sign-out applies to that client/account on this device,
potentially including other programs using the registration. It does not remove
the Windows account, revoke other-device sessions, recall previously returned
access tokens, reset Python CLI settings or guarantee rollback of broker cache
updates. Raw native `acquire`/`logout`/`logout_bound` callers do not participate in
the credential coordinator and must supply their own session policy.

## Bounds, cancellation and pending cleanup

- The coordinator retains at most **64 identity keys**, including signed-out
  tombstones, for the process lifetime. It never evicts invalidation state.
  Registry exhaustion returns `IdentityCapacityExhausted` with restart guidance,
  not interaction-required or "no account". Existing selections remain usable.
- One native operation may be admitted per known application-account domain.
  Concurrent acquisition returns `OperationInProgress`, not an unbounded queue.
- All native spawn paths, including raw interactive requests, share **four**
  worker reservations. A worker owns its permit until its final explicit action,
  after confirmed operation/window/apartment cleanup. Consumer drop, timeout,
  cancellation or early result delivery never releases that permit.
- Native absolute deadlines are **120 seconds** for silent/logout work and
  **600 seconds** for explicitly interactive work, across the entire operation.
  Coordinated credentials also bound local waiting on the caller's Tokio
  runtime, even if a native synchronous call prevents the worker observing its
  deadline. The caller may impose a shorter deadline. No independent async
  runtime is created.
- Cancellation requests WinRT `Cancel` once. After five seconds without terminal
  cleanup, local waiting can return `CleanupPending`; the worker still owns the
  operation, hidden parent and STA. Timeout similarly returns `TimedOut` without
  claiming teardown. Completion notification failure remains
  `CompletionUnconfirmed`, not successful cleanup.
- Late native termination automatically recovers its worker capacity after
  confirmed cleanup. An unconfirmed window/resource cleanup quarantines its
  reservation. Four stuck/quarantined workers cause deterministic
  `CapacityExhausted`, with non-secret active/limit counts. Wait for actual cleanup;
  if it remains unconfirmed, restart this process deliberately. **Do not retry in
  a loop.** No replacement threads, forced thread termination or premature window
  destruction are used to conceal exhaustion.
- Poisoned lifecycle bookkeeping returns `CoordinationFailed` and fails closed;
  it does not repeatedly panic, recover a credential or silently recycle
  uncertain native resources.

WinRT cancellation is cooperative. Native synchronous calls/provider hangs can
prevent the worker from observing its deadline. Raw native API callers must impose
their own local-wait deadline. No bounded OS/provider termination is promised. WinRT
[`Close`](https://learn.microsoft.com/en-us/uwp/api/windows.foundation.iasyncinfo.close)
is not legal before completion. The native owner retains resources until it can
observe terminal completion; it does not force-close to improve availability.

WAM retains secure persistence. This implementation adds no token file, raw
token input, credential fallback, registration/consent operation, provider-field
change or access-token JWT identity proof. Claims-challenge replay and CAE remain
unimplemented; Azure Core 1.1.0 token request method options are not evidence of
those capabilities.

## Offline evidence boundary

Synthetic tests exercise the real private coordinator backing credential entry
points and actual returned credentials' SDK refresh, using controlled broker
results and independent teardown signals. Cases include initial cross-tenant
admission, late native-ID alias merging, buffered success versus logout,
cancelled/failed logout, unpolled logout, retained capacity and late recovery,
registry saturation, scope rejection, poison and redaction. These fixtures never
use a real token provider, account or sign-in UI.

Source changes and test definitions alone are not passing evidence. Record exact
source hashes, feature/platform scope, executed commands/exits and independent
review. Existing tests that really create an STA/hidden window require their
own native execution authorization. Live MFA/CA, guests/aliases, service access
and team approval remain unproved.
