"""
Classes that represent tests.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from inspect import getfullargspec
from typing import Any


class Test(ABC):
    """
    Captures the notion of a Test, such as "see whether a follower is told about a new post".
    """
    def __init__(self, name: str, description: str | None, builtin: bool) -> None:
        self.name: str = name
        self.description: str | None = description
        self._builtin: bool = builtin


    def __str__(self):
        return self.name


    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        ...


    @abstractmethod
    def needed_local_role_names(self) -> set[str]:
        """
        Determines the local names of the constellation roles this test needs. These may be mapped to
        constellation roles in the test definition.
        """
        ...


    @property
    def builtin(self):
        """
        If true, do not add this test to a test session when the session is created by collecting tests.
        """
        return self._builtin


class TestFromTestFunction(Test):
    """
    A test that is defined as a single function.
    """
    def __init__(self, name: str, description: str | None, test_function: Callable[..., None], builtin: bool = False) -> None:
        super().__init__(name, description, builtin)

        self.test_function = test_function


    # Python 3.12 @override
    def metadata(self) -> dict[str, Any]:
        return {
            'Name:' : self.name,
            'Description:' : self.description
        }


    # Python 3.12 @override
    def needed_local_role_names(self) -> set[str]:
        ret = {}
        function_spec = getfullargspec(self.test_function)
        for arg in function_spec.args:
            ret[arg] = 1
        return set(ret)



class TestStepInTestClass:
    """
    A step in a TestFromTestClass. TestSteps for the same Test are all declared with @step in the same class,
    and will be executed in sequence unless specified otherwise.
    """
    def __init__(self, name: str, description: str | None, test: 'TestFromTestClass', test_step_function: Callable[[Any],None]) -> None:
        self.name: str = name
        self.description: str | None = description
        self.test = test
        self.test_step_function: Callable[[Any], None] = test_step_function


    def __str__(self):
        return self.name


class TestFromTestClass(Test):
    def __init__(self, name: str, description: str | None, clazz: type, builtin: bool = False) -> None:
        super().__init__(name, description, builtin)

        self.clazz = clazz
        self.steps : list[TestStepInTestClass] = []


    # Python 3.12 @override
    def metadata(self) -> dict[str, Any]:
        return {
            'Name:' : self.name,
            'Description:' : self.description,
            'Steps:' : len(self.steps)
        }


    # Python 3.12 @override
    def needed_local_role_names(self) -> set[str]:
        """
        Determines the names of the constellation roles this test step needs.
        It determines that by creating the union of the parameter names of all the TestSteps in the Test
        """
        ret = {}
        function_spec = getfullargspec(self.clazz.__init__) # type: ignore [misc]
        for arg in function_spec.args[1:]: # first is self
            ret[arg] = 1
        return set(ret)
