from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


def safe_call_app(app: Any, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Safely call a function from the app's loop, checking if we are already in the main thread.
    """
    try:
        if app._thread_id == threading.get_ident():
            return callback(*args, **kwargs)
    except (AttributeError, RuntimeError):
        pass
    return app.call_from_thread(callback, *args, **kwargs)
