# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Utility functions for ectop.

.. note::
    If you modify features, API, or usage, you MUST update the documentation immediately.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


def safe_call_app(app: Any, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a callback only through the active Textual app thread.

    Parameters
    ----------
    app : Any
        The Textual App instance.
    callback : Callable[..., Any]
        The callback to deliver on the app thread.
    *args : Any
        Positional callback arguments.
    **kwargs : Any
        Keyword callback arguments.

    Returns
    -------
    Any
        The callback result when already on the UI thread, the result of
        ``call_from_thread`` when dispatched, or ``None`` if the app is stopped.
    """
    try:
        if not app.is_running:
            return None
        app_thread_id = app._thread_id
    except (AttributeError, RuntimeError):
        return None

    if app_thread_id is None:
        return None

    try:
        if app_thread_id == threading.get_ident():
            return callback(*args, **kwargs)
    except (AttributeError, RuntimeError):
        return None

    try:
        return app.call_from_thread(callback, *args, **kwargs)
    except (AttributeError, RuntimeError):
        return None
