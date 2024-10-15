# This is a little hack, but useful.
# The problem:
# You have a file that contains some @tests and maybe some @steps inside @tests. You want to temporarily disable them.
# You can go through the file, and change all the @test and @step annotations.
# Or, you can change the import statement from something like:
#     from feditest import AssertionFailure, InteropLevel, SpecLevel, step, test
# to
#     from feditest.disabled import AssertionFailure, InteropLevel, SpecLevel, step, test
#

from typing import Callable

from feditest import AssertionFailure, InteropLevel, SpecLevel, all_node_drivers, all_tests, assert_that, nodedriver  # noqa: F401

def test(to_register: Callable[..., None] | type) -> Callable[..., None] | type:
    """
    Disabled: do nothing
    """
    return to_register


def step(to_register: Callable[..., None]) -> Callable[..., None]:
    """
    Disabled: do nothing
    """
    return to_register