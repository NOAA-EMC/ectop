import asyncio
from functools import wraps

import textual


def mock_work(*args, **kwargs):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            if asyncio.iscoroutine(result):
                # Run the coroutine in the current loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We are already in a loop (pytest-asyncio)
                        # We can't use run_until_complete here.
                        # We return the task and let the test await it if needed,
                        # but most tests don't.
                        return asyncio.create_task(result)
                    else:
                        return loop.run_until_complete(result)
                except RuntimeError:
                    return asyncio.run(result)
            return result

        return wrapper

    if len(args) == 1 and callable(args[0]):
        return decorator(args[0])
    return decorator


textual.work = mock_work
