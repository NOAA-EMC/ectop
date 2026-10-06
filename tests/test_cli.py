# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
# .. note:: warning: "If you modify features, API, or usage, you MUST update the documentation immediately."
import os
from unittest.mock import MagicMock, patch

import pytest

from ectop.cli import create_parser, main


def test_cli_args():
    """Pass parsed CLI arguments to the application.

    Returns
    -------
    None
        The app factory and runner receive the parsed values.
    """
    with patch("argparse.ArgumentParser.parse_args") as mock_args:
        mock_args.return_value = MagicMock(host="otherhost", port=9999, refresh=5.0)
        with patch("ectop.cli.Ectop") as mock_app:
            main()
            mock_app.assert_called_once_with(host="otherhost", port=9999, refresh_interval=5.0)
            mock_app.return_value.run.assert_called_once()


def test_cli_env_vars():
    """Use environment values as parser defaults.

    Returns
    -------
    None
        The app factory receives the environment settings.
    """
    with patch.dict(os.environ, {"ECF_HOST": "envhost", "ECF_PORT": "8888", "ECTOP_REFRESH": "3.0"}):
        # We need to let argparse run normally to see if it picks up defaults from os.environ
        # but we don't want it to actually parse sys.argv
        with patch("sys.argv", ["ectop"]):
            with patch("ectop.cli.Ectop") as mock_app:
                main()
                mock_app.assert_called_once_with(host="envhost", port=8888, refresh_interval=3.0)


@pytest.mark.parametrize(
    ("arguments", "environment", "expected"),
    [
        ([], {}, ("localhost", 3141, 2.0)),
        (
            ["--host", "cli", "--port", "42", "--refresh", "0.5"],
            {"ECF_HOST": "env", "ECF_PORT": "80", "ECTOP_REFRESH": "3"},
            ("cli", 42, 0.5),
        ),
        ([], {"ECF_HOST": " envhost ", "ECF_PORT": "8888", "ECTOP_REFRESH": "3.0"}, ("envhost", 8888, 3.0)),
    ],
)
def test_valid_cli_and_environment_settings(arguments, environment, expected):
    """CLI values override validated environment defaults.

    Parameters
    ----------
    arguments : list[str]
        Command-line values for this case.
    environment : dict[str, str]
        Environment defaults for this case.
    expected : tuple[str, int, float]
        Expected parsed settings.

    Returns
    -------
    None
        Parsed values match the CLI and environment precedence.
    """
    defaults = {"ECF_HOST": "localhost", "ECF_PORT": "3141", "ECTOP_REFRESH": "2.0"}
    defaults.update(environment)
    with patch.dict(os.environ, defaults):
        args = create_parser().parse_args(arguments)
    assert (args.host, args.port, args.refresh) == expected


@pytest.mark.parametrize(
    ("option", "value", "message"),
    [
        ("--host", "   ", "hostname or IP address"),
        ("--host", "has space", "hostname or IP address"),
        ("--port", "abc", "TCP port from 1 to 65535"),
        ("--port", "0", "TCP port from 1 to 65535"),
        ("--port", "65536", "TCP port from 1 to 65535"),
        ("--refresh", "nope", "finite number greater than 0 seconds"),
        ("--refresh", "nan", "finite number greater than 0 seconds"),
        ("--refresh", "inf", "finite number greater than 0 seconds"),
        ("--refresh", "0", "finite number greater than 0 seconds"),
        ("--refresh", "-1", "finite number greater than 0 seconds"),
    ],
)
def test_invalid_cli_settings_have_setting_specific_errors(option, value, message, capsys):
    """Invalid CLI values produce concise argparse diagnostics.

    Parameters
    ----------
    option : str
        CLI setting name.
    value : str
        Invalid setting value.
    message : str
        Expected validation guidance.
    capsys : pytest.CaptureFixture[str]
        Captured parser output.

    Returns
    -------
    None
        Argparse exits with status 2 and names the setting constraint.
    """
    with pytest.raises(SystemExit) as error:
        create_parser().parse_args([option, value])
    assert error.value.code == 2
    assert message in capsys.readouterr().err


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("ECF_HOST", "", "hostname or IP address"),
        ("ECF_PORT", "bad", "TCP port from 1 to 65535"),
        ("ECF_PORT", "70000", "TCP port from 1 to 65535"),
        ("ECTOP_REFRESH", "nan", "finite number greater than 0 seconds"),
        ("ECTOP_REFRESH", "0", "finite number greater than 0 seconds"),
    ],
)
def test_invalid_environment_settings_have_setting_specific_errors(key, value, message, capsys):
    """Invalid environment defaults are validated through argparse.

    Parameters
    ----------
    key : str
        Environment variable name.
    value : str
        Invalid environment value.
    message : str
        Expected validation guidance.
    capsys : pytest.CaptureFixture[str]
        Captured parser output.

    Returns
    -------
    None
        Argparse exits with status 2 and names the setting constraint.
    """
    with patch.dict(os.environ, {key: value}):
        with pytest.raises(SystemExit) as error:
            create_parser().parse_args([])
    assert error.value.code == 2
    assert message in capsys.readouterr().err
