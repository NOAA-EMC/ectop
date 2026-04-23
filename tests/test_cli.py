# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Tests for the CLI entry point.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ectop.cli import main


def test_cli_args() -> None:
    """
    Test that CLI arguments are correctly passed to the App.
    """
    with patch("argparse.ArgumentParser.parse_args") as mock_args:
        mock_args.return_value = MagicMock(host="otherhost", port=9999, refresh=5.0)
        with patch("ectop.cli.Ectop") as mock_app:
            main()
            mock_app.assert_called_once_with(host="otherhost", port=9999, refresh_interval=5.0)
