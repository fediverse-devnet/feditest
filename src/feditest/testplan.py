"""
"""

class TestPlan:
    """
    A series of steps that can be run to perform one or more tests
    """
    pass


# Tests are contained in their respective TestSets, and in addition also in the all_tests TestSet
all_tests = TestSet('all-tests', 'Collects all available tests', None)
all_test_sets: dict[str,TestSet] = {}

def register_test(to_register: Callable[[Any], None], name: str | None = None, description: str | None = None) -> None:

    if not isinstance(to_register,FunctionType):
        fatal('Cannot register a non-function test')

    module = getmodule(to_register)
    if module :
        package_name = '.'.join( module.__name__.split('.')[0:-1])
        if package_name in all_test_sets:
            test_set = all_test_sets[package_name]
        else:
            package = resolve_name(package_name)
            test_set = TestSet(package_name, package.__doc__, package)
            all_test_sets[package_name] = test_set
    else :
        test_set = None

    if not name:
        name = f"{to_register.__module__}::{to_register.__qualname__}"
        # This is the same convention as pytest's I believe
    if not description:
        description = to_register.__doc__

    sig = signature(to_register)

    match len(sig.parameters):
        case 1:
            test = Constallation1Test(name, description, test_set, to_register)
        case 2:
            test = Constallation2Test(name, description, test_set, to_register)
        case _:
            fatal("FIXME: not implemented")

    all_tests.add_test(test)
    if test_set:
        test_set.add_test(test)
