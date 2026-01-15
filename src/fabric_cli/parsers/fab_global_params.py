# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.


def add_global_flags(parser) -> None:
    """
    Add global flags that apply to all commands.

    Args:
        parser: The argparse parser to add flags to.
    
    Note: argparse automatically adds -h/--help, so we don't need to add it manually.
    """
    # Note: -h/--help is automatically added by argparse by default
    # We don't need to explicitly add it
    
    # Add format flag to override output format
    parser.add_argument(
        "--output_format",
        required=False,
        choices=["json", "text"],
        help="Override output format type. Optional",
    )
