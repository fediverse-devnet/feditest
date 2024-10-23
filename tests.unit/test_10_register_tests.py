"""
Test that @test and @step annotations register their functions/classes/methods correctly.
"""

import pytest

import feditest
from feditest import step, test
from feditest.tests import TestFromTestClass, TestFromTestFunction


@pytest.fixture(scope="module", autouse=True)
def init():
    """ Keep these isolated to this module """
    feditest.all_tests = {}
    feditest._registered_as_test = {}
    feditest._registered_as_test_step = {}
    feditest._loading_tests = True

    @test
    def test1() -> None:
        return

    @test
    def test2() -> None:
        return

    @test
    def test3() -> None:
        return

    @test
    class TestA():
        @step
        def testa1(self) -> None:
            return

        @step
        def testa2(self) -> None:
            return

    feditest._loading_tests = False
    feditest._load_tests_pass2()


def test_tests_registered() -> None:
    assert len(feditest.all_tests) == 4


def test_functions() -> None:
    functions = [ testInstance for testInstance in feditest.all_tests.values() if isinstance(testInstance, TestFromTestFunction) ]
    assert len(functions) == 3
    functions[0].name.endswith('test1')
    functions[1].name.endswith('test2')
    functions[2].name.endswith('test3')


def test_classes() -> None:
    classes = [ testInstance for testInstance in feditest.all_tests.values() if isinstance(testInstance, TestFromTestClass) ]
    assert len(classes) == 1

    singleClass = classes[0]
    assert singleClass.name.endswith('TestA')

    assert len(singleClass.steps) == 2
    singleClass.steps[0].name.startswith('testa')
    singleClass.steps[1].name.startswith('testa')
