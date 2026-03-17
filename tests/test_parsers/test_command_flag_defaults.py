# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from fabric_cli.core.fab_parser_setup import CustomArgumentParser
from fabric_cli.parsers.fab_fs_parser import register_ls_parser
from fabric_cli.parsers.fab_jobs_parser import register_parser as register_jobs_parser


def _build_parser() -> CustomArgumentParser:
    parser = CustomArgumentParser()
    subparsers = parser.add_subparsers()
    register_ls_parser(subparsers)
    register_jobs_parser(subparsers)
    return parser


def test_ls_sort_flag_accepts_name_and_type():
    parser = _build_parser()

    args = parser.parse_args(["ls", "ws1.Workspace", "--sort_by", "name"])
    assert args.sort_by == "name"

    args = parser.parse_args(["ls", "ws1.Workspace", "--sort", "type"])
    assert args.sort_by == "type"


def test_job_run_cancel_on_timeout_flag_accepts_true_false():
    parser = _build_parser()

    args = parser.parse_args(
        ["job", "run", "ws1.Workspace/p1.DataPipeline", "--cancel_on_timeout", "true"]
    )
    assert args.cancel_on_timeout == "true"

    args = parser.parse_args(
        ["job", "run", "ws1.Workspace/p1.DataPipeline", "--cancel_on_timeout", "false"]
    )
    assert args.cancel_on_timeout == "false"
