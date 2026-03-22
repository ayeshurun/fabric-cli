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

    args = parser.parse_args(["ls", "ws1.Workspace", "--sort_by", "type"])
    assert args.sort_by == "type"


def test_ls_sort_flag_defaults_to_name():
    parser = _build_parser()

    args = parser.parse_args(["ls", "ws1.Workspace"])
    assert args.sort_by == "name"


def test_job_run_no_cancel_on_timeout_flag_defaults_to_false():
    parser = _build_parser()

    args = parser.parse_args(["job", "run", "ws1.Workspace/p1.DataPipeline"])
    assert args.no_cancel_on_timeout is False


def test_job_run_no_cancel_on_timeout_flag_sets_true_when_passed():
    parser = _build_parser()

    args = parser.parse_args(
        ["job", "run", "ws1.Workspace/p1.DataPipeline", "--no_cancel_on_timeout"]
    )
    assert args.no_cancel_on_timeout is True
