# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.


def add_global_flags(parser) -> None:
    """
    Add global flags that apply to all commands.

    Args:
        parser: The argparse parser to add flags to.
    """
    # Add help flag (POSIX compliant: -h for short, --help for long)
    parser.add_argument("-h", "--help", action="help")
    
    # Add format flag to override output format
    parser.add_argument(
        "--output_format",
        required=False,
        choices=["json", "text"],
        help="Override output format type. Optional",
    )
