# #############################################################################
# WARNING: If you modify features, API, or usage, you MUST update the
# documentation immediately.
# #############################################################################
"""
Utility functions for the ectop application.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


def safe_call_app(app: Any, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Safely call a function from the app's loop.

    Parameters
    ----------
    app : Any
        The Textual app instance.
    callback : Callable
        The function to call.
    *args : Any
        Positional arguments for the callback.
    **kwargs : Any
        Keyword arguments for the callback.

    Returns
    -------
    Any
        The result of the callback.
    """
    try:
        if app._thread_id == threading.get_ident():
            return callback(*args, **kwargs)
    except (AttributeError, RuntimeError):
        pass
    return app.call_from_thread(callback, *args, **kwargs)
