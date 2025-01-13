"""Tests for the invariant_runner module."""

import os
from unittest.mock import patch

import pytest

from invariant.__main__ import create_config, main, parse_args


def test_create_config_with_push_and_api_key_env_var():
    """Test create_config when API key is provided via env variable."""
    test_args = ["runner.py", "--push"]

    with patch.dict(os.environ, {"INVARIANT_API_KEY": "env_api_key"}):
        invariant_runner_args, _ = parse_args(test_args[1:])
        config = create_config(invariant_runner_args)

        assert config.dataset_name.startswith("tests-")
        assert config.push is True
        assert config.api_key == "env_api_key"


def test_create_config_with_timestamp_dataset_name():
    """Test create_config when dataset_name defaults to a timestamp-based name."""
    test_args = ["runner.py", "--push"]

    with (
        patch.dict(os.environ, {"INVARIANT_API_KEY": "env_api_key"}),
        patch("time.time", return_value=1234567890),
    ):
        invariant_runner_args, _ = parse_args(test_args[1:])
        config = create_config(invariant_runner_args)

        assert config.dataset_name == "tests-1234567890"
        assert config.push is True
        assert config.api_key == "env_api_key"


def test_create_config_with_no_api_key_and_push_true_fails():
    """Test create_config when INVARIANT_API_KEY is not set and push is set to True."""
    test_args = ["runner.py", "--push"]

    with patch.dict(os.environ, {}, clear=True):
        invariant_runner_args, _ = parse_args(test_args[1:])

        with pytest.raises(ValueError) as exc_info:
            create_config(invariant_runner_args)

        assert "`INVARIANT_API_KEY` is required if `push` is set to true" in str(exc_info.value)


def test_main_execution_with_pytest_args():
    """Test main execution flow, ensuring correct pytest args are passed."""
    test_args = [
        "runner.py",
        "--dataset_name",
        "test_dataset",
        "--push",
        "-s",
        "-v",
    ]

    with (
        patch.dict(os.environ, {"INVARIANT_API_KEY": "env_api_key"}),
        patch("time.time", return_value=1234567890),
        patch("pytest.main") as mock_pytest_main,
    ):
        # Parse args and create config
        invariant_runner_args, pytest_args = parse_args(test_args[1:])
        config = create_config(invariant_runner_args)

        # Assert the Config object is correctly populated
        assert config.dataset_name == "test_dataset-1234567890"
        assert config.push is True
        assert config.api_key == "env_api_key"
        assert config.result_output_dir == ".invariant/test_results"

        # Simulate calling pytest with remaining arguments
        pytest.main(pytest_args)
        mock_pytest_main.assert_called_once_with(["-s", "-v"])


def test_main_via_command():
    """On top of the test command tests above, this case ensure that also passing the arguments
    via the invariant cli `invariant test --dataset_name test_dataset --push -s -v` works.
    """
    test_args = [
        "invariant",
        "test",
        "--dataset_name",
        "test_dataset",
        "--push",
        "-s",
        "-v",
    ]

    with (
        patch.dict(os.environ, {"INVARIANT_API_KEY": "env_api_key"}),
        patch("time.time", return_value=1234567890),
        patch("sys.argv", test_args),
        patch("pytest.main") as mock_pytest_main,
    ):
        # Parse args and create config
        main()
        mock_pytest_main.assert_called_once_with(["-s", "-v"])
