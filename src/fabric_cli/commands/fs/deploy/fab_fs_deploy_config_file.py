# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
from argparse import Namespace

from fabric_cicd import FeatureFlag, append_feature_flag, configure_external_file_logging, deploy_with_config, disable_file_logging  # type: ignore

from fabric_cli.core import fab_constant, fab_state_config
from fabric_cli.core import fab_logger
from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.core.fab_msal_bridge import create_fabric_token_credential
from fabric_cli.utils import fab_ui
from fabric_cli.utils.fab_util import get_dict_from_params

# Feature flags the CLI always enables on the user's behalf, so they are skipped
# (not re-appended, not validated) if a user also passes them via --feature_flags:
# - disable_print_identity: avoids printing identity info in fabric-cicd logs.
# - enable_experimental_features: gate that must be on for any experimental
#   fabric-cicd feature flag to take effect; harmless on its own.
_ALWAYS_ON_FEATURE_FLAGS = {"disable_print_identity", "enable_experimental_features"}

# Valid fabric-cicd feature flag names, derived from the library's FeatureFlag enum.
# See https://microsoft.github.io/fabric-cicd/latest/how_to/optional_feature/
VALID_FEATURE_FLAGS = {flag.value for flag in FeatureFlag}


def deploy_with_config_file(args: Namespace) -> None:
    """deploy fabric items to a workspace using a configuration file and target environment - delegates to CICD library."""

    try:
        if fab_state_config.get_config(fab_constant.FAB_DEBUG_ENABLED) == "true":
            cli_logger = fab_logger.get_logger()
            # configure file logging for CICD library to use the same file handler as the CLI
            configure_external_file_logging(cli_logger)
        else:
            # prevent creation of a log file for fabric-cicd logs when debug mode is disabled
            disable_file_logging()

        # enable the always-on flags plus any opt-in fabric-cicd feature flags
        # passed via --feature_flags
        _apply_feature_flags(args)

        deploy_config_file = args.config
        deploy_parameters = get_dict_from_params(args.params, max_depth=1)

        for param in deploy_parameters:
            if isinstance(deploy_parameters[param], str):
                try:
                    deploy_parameters[param] = json.loads(
                        deploy_parameters[param])
                except json.JSONDecodeError:
                    # If it's not a valid JSON string, keep it as is
                    pass
        result = deploy_with_config(
            config_file_path=deploy_config_file,
            environment=args.target_env,
            token_credential=create_fabric_token_credential(),  # MSAL bridge TokenCredential
            **deploy_parameters
        )

        if result:
            fab_ui.print_output_format(
                args, message=result.message)

    except Exception as e:
        raise FabricCLIError(
            f"Deployment failed: {str(e)}",
            fab_constant.ERROR_IN_DEPLOYMENT)


def _apply_feature_flags(args: Namespace) -> None:
    """Enable fabric-cicd feature flags.

    Always enables the flags the CLI turns on by default (_ALWAYS_ON_FEATURE_FLAGS):
    - disable_print_identity keeps identity info out of fabric-cicd logs.
    - enable_experimental_features is the gate required for any experimental
      fabric-cicd feature flag to take effect; it has no effect on its own, so
      enabling it by default spares users from passing it alongside experimental
      flags.

    Also enables any opt-in flags passed via --feature_flags, which accepts a
    single comma-separated list of flag names
    (--feature_flags enable_shortcut_publish,enable_bulk_publish). Each is
    validated against the fabric-cicd supported feature flag list and enabled via
    append_feature_flag. Flags already enabled by default are skipped here if
    passed explicitly.
    """
    for flag in _ALWAYS_ON_FEATURE_FLAGS:
        append_feature_flag(flag)

    raw_flags = getattr(args, "feature_flags", None)
    if not raw_flags:
        return

    for flag in _parse_feature_flags(raw_flags):
        if flag in _ALWAYS_ON_FEATURE_FLAGS:
            # already enabled by the CLI; skip redundant handling
            continue
        if flag not in VALID_FEATURE_FLAGS:
            raise FabricCLIError(
                f"Unknown fabric-cicd feature flag: '{flag}'. Valid flags: "
                f"{', '.join(sorted(VALID_FEATURE_FLAGS))}. See "
                f"https://microsoft.github.io/fabric-cicd/latest/how_to/optional_feature/",
                fab_constant.ERROR_INVALID_INPUT,
            )
        append_feature_flag(flag)


def _parse_feature_flags(raw_flags: str) -> list:
    """Split the comma-separated --feature_flags value into a flat list of flag
    name strings.

    Surrounding '[' ']' brackets and whitespace are ignored and empty entries are
    dropped, so 'a,b', ' a , b ' and '[a,b]' all yield ['a', 'b'].
    """
    raw_flags = raw_flags.strip().strip("[]")
    return [name.strip() for name in raw_flags.split(",") if name.strip()]
