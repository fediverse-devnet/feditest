# def pytest_pycollect_makeitem(collector, name, obj):
#     module_name = getattr(obj, "__module__") if hasattr(obj, "__module__") else None
#     if module_name and module_name.startswith("feditest."):
#         print("@@@@@ Not collecting", obj, module_name)
#         return None

import inspect

import pytest


@pytest.hookimpl(wrapper=True)
def pytest_pycollect_makeitem(collector, name, obj):
    # Ignore all feditest classes and function using
    # pytest naming conventions.
    if isinstance(obj, type) or inspect.isfunction(obj) or inspect.ismethod(obj):
        m = obj.__module__.split(".")
        if len(m) > 0 and m[0] == "feditest":
            yield
            return None
    result = yield
    return result
