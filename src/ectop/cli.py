# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
CLI entry point for ectop.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

import argparse
import math
import os

from ectop.app import Ectop
from ectop.constants import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_REFRESH_INTERVAL


def _host(value: str) -> str:
    """Validate a server host value.

    Parameters
    ----------
    value : str
        Host name or IP address supplied by the CLI or environment.

    Returns
    -------
    str
        The stripped host value.

    Raises
    ------
    argparse.ArgumentTypeError
        If the host is empty or contains whitespace.
    """
    host = value.strip()
    if not host or any(char.isspace() for char in host):
        raise argparse.ArgumentTypeError("must be a non-empty hostname or IP address")
    return host


def _tcp_port(value: str) -> int:
    """Parse a valid TCP port.

    Parameters
    ----------
    value : str
        Port supplied by the CLI or environment.

    Returns
    -------
    int
        A TCP port in the range 1 through 65535.

    Raises
    ------
    argparse.ArgumentTypeError
        If the value is malformed or outside the TCP port range.
    """
    try:
        port = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer TCP port from 1 to 65535") from error
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("must be an integer TCP port from 1 to 65535")
    return port


def _positive_finite_float(value: str) -> float:
    """Parse a finite positive refresh interval.

    Parameters
    ----------
    value : str
        Refresh interval in seconds supplied by the CLI or environment.

    Returns
    -------
    float
        A finite interval greater than zero.

    Raises
    ------
    argparse.ArgumentTypeError
        If the value is malformed, non-finite, or not positive.
    """
    try:
        interval = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a finite number greater than 0 seconds") from error
    if not math.isfinite(interval) or interval <= 0:
        raise argparse.ArgumentTypeError("must be a finite number greater than 0 seconds")
    return interval


def create_parser() -> argparse.ArgumentParser:
    """Create the command-line parser with validated environment defaults.

    Returns
    -------
    argparse.ArgumentParser
        Parser configured for CLI and environment settings.
    """
    parser = argparse.ArgumentParser(description="ectop — High-performance TUI for ECMWF ecFlow")
    parser.add_argument(
        "--host",
        type=_host,
        default=os.environ.get("ECF_HOST", DEFAULT_HOST),
        help=f"ecFlow server hostname (default: {DEFAULT_HOST} or ECF_HOST)",
    )
    parser.add_argument(
        "--port",
        type=_tcp_port,
        default=str(os.environ.get("ECF_PORT", DEFAULT_PORT)),
        help=f"ecFlow server TCP port 1-65535 (default: {DEFAULT_PORT} or ECF_PORT)",
    )
    parser.add_argument(
        "--refresh",
        type=_positive_finite_float,
        default=str(os.environ.get("ECTOP_REFRESH", DEFAULT_REFRESH_INTERVAL)),
        help=f"Automatic refresh interval in finite seconds > 0 (default: {DEFAULT_REFRESH_INTERVAL} or ECTOP_REFRESH)",
    )
    return parser


def main() -> None:
    """
    Run the ectop application.

    Parses command-line arguments and environment variables for server configuration.
    """
    args = create_parser().parse_args()

    app = Ectop(host=args.host, port=args.port, refresh_interval=args.refresh)
    app.run()


if __name__ == "__main__":
    main()
