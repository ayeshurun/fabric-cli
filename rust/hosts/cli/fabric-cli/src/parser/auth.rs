// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

use clap::{Arg, ArgAction, ArgMatches, Command};

/// Registered public client used when no explicit or saved broker client is selected.
pub const DEFAULT_BROKER_CLIENT_ID: &str = "5814bfb4-2705-4994-b8d6-39aabeb5eaeb";

/// Explicit authentication action; no action runs during parsing.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AuthAction {
    /// Silent acquisition, allowing user-initiated broker UI when required.
    Login,
    /// Silent-only acquisition of the selected identity's three audiences.
    Status,
    /// Explicit app-scoped sign-out on this device.
    Logout,
}

/// Parsed non-secret authentication inputs, independent of read-command arguments.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AuthCommand {
    /// Operation to execute only through the opt-in authentication host.
    pub action: AuthAction,
    /// Optional target tenant GUID; otherwise use the saved selection or login picker.
    pub tenant: Option<String>,
    /// Optional work UPN; never selected from the first cached account.
    pub account: Option<String>,
    /// Public application registration GUID.
    pub client_id: String,
    /// Whether argv explicitly overrides the saved/environment application selection.
    pub client_id_explicit: bool,
    /// Explicit presentation override, otherwise selected from the caller's settings.
    pub output_format: Option<String>,
    /// Maximum CLI wait in seconds (1-600).
    pub timeout_seconds: u64,
    /// Whether login may initiate interactive broker/MFA UI.
    pub allow_interaction: bool,
}

pub(super) fn register(command: Command) -> Command {
    let mut auth = Command::new("auth")
        .about("Explicit Windows Entra broker authentication")
        .subcommand_required(true);
    for (name, about) in [
        (
            "login",
            "Acquire Fabric, OneLake and ARM tokens, with broker MFA when required",
        ),
        (
            "status",
            "Validate all three audiences silently; never open sign-in UI",
        ),
        (
            "logout",
            "Sign out only this application's selected broker account on this device",
        ),
    ] {
        let mut subcommand = Command::new(name)
            .about(about)
            .arg(
                Arg::new("tenant")
                    .long("tenant")
                    .help("Target tenant GUID; defaults to the saved selection or broker sign-in")
                    .value_name("TENANT_GUID"),
            )
            .arg(
                Arg::new("account")
                    .long("account")
                    .help("Work account UPN; defaults to the saved selection or broker account picker")
                    .value_name("WORK_ACCOUNT_UPN"),
            )
            .arg(
                Arg::new("client-id")
                    .long("client-id")
                    .default_value(DEFAULT_BROKER_CLIENT_ID)
                    .value_name("CLIENT_GUID"),
            )
            .arg(
                Arg::new("timeout-seconds")
                    .long("timeout-seconds")
                    .default_value("120")
                    .value_parser(clap::value_parser!(u64).range(1..=600)),
            );
        if name == "login" {
            subcommand = subcommand.arg(
                Arg::new("no-interactive")
                    .long("no-interactive")
                    .action(ArgAction::SetTrue)
                    .help("Never show UI; fail if interaction is required"),
            );
        }
        auth = auth.subcommand(subcommand);
    }
    command.after_help("Windows broker authentication is opt-in. Login remembers only the selected account, tenant and client ID; tokens stay in WAM. Remote commands require a native-read build.")
        .subcommand(auth)
}

pub(super) fn parse(matches: &ArgMatches) -> Result<AuthCommand, clap::Error> {
    let auth = matches
        .subcommand_matches("auth")
        .expect("matched auth command");
    let (name, args) = auth.subcommand().expect("required auth action");
    let action = match name {
        "login" => AuthAction::Login,
        "status" => AuthAction::Status,
        "logout" => AuthAction::Logout,
        _ => unreachable!("auth schema validates the action"),
    };
    Ok(AuthCommand {
        action,
        tenant: args.get_one::<String>("tenant").cloned(),
        account: args.get_one::<String>("account").cloned(),
        client_id: args
            .get_one::<String>("client-id")
            .expect("default client")
            .clone(),
        client_id_explicit: args.value_source("client-id")
            == Some(clap::parser::ValueSource::CommandLine),
        output_format: args
            .get_one::<String>("output_format")
            .cloned()
            .or_else(|| matches.get_one::<String>("output_format").cloned()),
        timeout_seconds: *args
            .get_one::<u64>("timeout-seconds")
            .expect("default timeout"),
        allow_interaction: action == AuthAction::Login && !args.get_flag("no-interactive"),
    })
}
