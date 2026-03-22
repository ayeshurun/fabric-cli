# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from argparse import Namespace

from fabric_cli.core import fab_constant, fab_state_config
from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.errors import ErrorMessages
from fabric_cli.utils import fab_ui as utils_ui


def exec_command(args: Namespace) -> None:
    key = args.key.lower()

    # Backward compatibility: 'mode' is no longer a configurable setting.
    # Phase 1: warn but still return the runtime mode so existing scripts don't break.
    if key == fab_constant.FAB_MODE:
        utils_ui.print_warning(
            "The 'mode' setting is deprecated and will be removed in a future release. "
            "Run 'fab' without arguments to enter REPL mode, "
            "or use 'fab <command>' for command-line mode."
        )
        from fabric_cli.core.fab_context import Context

        utils_ui.print_output_format(args, data=Context().get_runtime_mode())
        return

    if key not in fab_constant.FAB_CONFIG_KEYS_TO_VALID_VALUES:
        raise FabricCLIError(
            ErrorMessages.Config.unknown_configuration_key(key),
            fab_constant.ERROR_INVALID_INPUT,
        )
    else:
        value = fab_state_config.get_config(key)
        if value:
            utils_ui.print_output_format(args, data=value)
