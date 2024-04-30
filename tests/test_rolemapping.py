import logging
import pytest
from typing import Any, Callable

from feditest import all_node_drivers, all_tests, TestFromTestFunction, TestFromTestClass, TestStep
from feditest.protocols import Node, NodeDriver
from feditest.testplan import *
from feditest.testrun import TestRun


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    previous_level = logging.root.level
    logging.root.setLevel(logging.DEBUG)
    yield
    logging.root.setLevel(previous_level)


class StubNode(Node):
    pass


class StubNodeDriver(NodeDriver):
    def _provision_node(
        self, rolename: str, parameters: dict[str, Any]
    ) -> Node:
        return StubNode(rolename, parameters, self)

    def _unprovision_node(self, instance: Node): ...


recorded_calls : list[tuple[Callable[..., None], Any, dict[str,Any]]] | None = None

@pytest.fixture(autouse=True)
def setup_recorded_calls():
    global recorded_calls
    recorded_calls = []


def print_recorded_calls():
    """ For debugging """
    global recorded_calls
    print(f'Recorded calls ({ len(recorded_calls)})')
    for i, recorded_call in enumerate(recorded_calls):
        args_string = ",".join( [ f"{ key }={ value.rolename if value else 'NONE' }" for key, value in recorded_call[2].items() ] )
        # print(f'{ i }: { recorded_call[0].__name__}{ ( ' on ' + recorded_call[1] ) if recorded_call[1] else '' } ({ args_string })')
        if recorded_call[1] is None:
            print(f'{ i }: { recorded_call[0].__name__} ({ args_string })')
        else:
            print(f'{ i }: { recorded_call[0].__name__} on { recorded_call[1] } ({ args_string })')


def stub_test_function3(role_a: Node, role_b: Node, role_c: Node):
    global recorded_calls
    recorded_calls.append(
        (
            stub_test_function3,
            None,
            {
                'role_a' : role_a,
                'role_b' : role_b,
                'role_c' : role_c
            }
        )
    )


def stub_test_function3_needs_mapping(function_role_a: Node, function_role_b: Node, function_role_c: Node):
    global recorded_calls
    recorded_calls.append(
        (
            stub_test_function3_needs_mapping,
            None,
            {
                'function_role_a' : function_role_a,
                'function_role_b' : function_role_b,
                'function_role_c' : function_role_c
            }
        )
    )

class StubTest3:
    def __init__(self, role_a: Node, role_b: Node, role_c: Node):
        global recorded_calls
        recorded_calls.append(
            (
                StubTest3.__init__,
                self,
                {
                    'role_a' : role_a,
                    'role_b' : role_b,
                    'role_c' : role_c
                }
            )
        )
        self.role_a = role_a
        self.role_b = role_b
        self.role_c = role_c


    def step1(self):
        global recorded_calls
        recorded_calls.append(
            (
                StubTest3.step1,
                self,
                {}
            )
        )

    def step2(self):
        global recorded_calls
        recorded_calls.append(
            (
                StubTest3.step2,
                self,
                {}
            )
        )


class StubTest3NeedsMapping:
    def __init__(self, class_role_a: Node, class_role_b: Node, class_role_c: Node):
        global recorded_calls
        recorded_calls.append(
            (
                StubTest3NeedsMapping.__init__,
                self,
                {
                    'class_role_a' : class_role_a,
                    'class_role_b' : class_role_b,
                    'class_role_c' : class_role_c
                }
            )
        )
        self.class_role_a = class_role_a
        self.class_role_b = class_role_b
        self.class_role_c = class_role_c


    def step1(self):
        global recorded_calls
        recorded_calls.append(
            (
                StubTest3NeedsMapping.step1,
                self,
                {}
            )
        )

    def step2(self):
        global recorded_calls
        recorded_calls.append(
            (
                StubTest3NeedsMapping.step2,
                self,
                {}
            )
        )


@pytest.fixture(autouse=True)
def init_tests():
    """
    We register everything manually otherwise getting around the loading logic is convoluted
    """
    all_tests.clear()

    for f in [stub_test_function3, stub_test_function3_needs_mapping]:
        all_tests[f.__name__] = TestFromTestFunction(f.__name__, None, f)
    for c in [StubTest3, StubTest3NeedsMapping]:
        all_tests[c.__name__] = TestFromTestClass(c.__name__, None, c)
        all_tests[c.__name__].steps = []
        for s in ['step1', 'step2']:
            f = getattr(c, s)
            all_tests[c.__name__].steps.append(TestStep(f.__name__, None, all_tests[c.__name__], f))


@pytest.fixture(autouse=True)
def init_node_drivers():
    all_node_drivers.clear()

    all_node_drivers[StubNodeDriver.__name__] = StubNodeDriver


### tests for function-based tests ###

def test_function_unmapped() :
    global recorded_calls
    plan = TestPlan(
        [
            TestPlanSession(
                TestPlanConstellation(
                    [
                        TestPlanConstellationRole(
                            'role_a',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_b',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_c',
                            StubNodeDriver.__name__
                        )
                    ]
                ),
                [
                    TestPlanTestSpec(
                        stub_test_function3.__name__
                    )
                ]
            )
        ]
    )
    plan.check_can_be_executed()

    test_run = TestRun(plan)
    test_run.run()

    assert(len(recorded_calls) == 1)
    recorded_call = recorded_calls[0]
    assert(recorded_call[0] == stub_test_function3)
    assert(recorded_call[1] == None)
    assert(len(recorded_call[2]) == 3)
    assert(recorded_call[2]['role_a'].rolename == 'role_a')
    assert(recorded_call[2]['role_b'].rolename == 'role_b')
    assert(recorded_call[2]['role_c'].rolename == 'role_c')


def test_function_unmapped_incomplete() :
    global recorded_calls
    plan = TestPlan(
        [
            TestPlanSession(
                TestPlanConstellation(
                    [
                        TestPlanConstellationRole(
                            'role_a',
                            StubNodeDriver.__name__
                        ),
                        # role_b missin
                        TestPlanConstellationRole(
                            'role_c',
                            StubNodeDriver.__name__
                        )
                    ]
                ),
                [
                    TestPlanTestSpec(
                        stub_test_function3.__name__
                    )
                ]
            )
        ]
    )
    with pytest.raises(TestPlanError):
        plan.check_can_be_executed()


def test_function_unmapped_surplus() :
    global recorded_calls
    plan = TestPlan(
        [
            TestPlanSession(
                TestPlanConstellation(
                    [
                        TestPlanConstellationRole(
                            'role_a',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole( # insert in the middle
                            'role_d',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_b',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_c',
                            StubNodeDriver.__name__
                        )
                    ]
                ),
                [
                    TestPlanTestSpec(
                        stub_test_function3.__name__
                    )
                ]
            )
        ]
    )
    plan.check_can_be_executed()

    test_run = TestRun(plan)
    test_run.run()

    assert(len(recorded_calls) == 1)
    recorded_call = recorded_calls[0]
    assert(recorded_call[0] == stub_test_function3)
    assert(recorded_call[1] == None )
    assert(len(recorded_call[2]) == 3)
    assert(recorded_call[2]['role_a'].rolename == 'role_a')
    assert(recorded_call[2]['role_b'].rolename == 'role_b')
    assert(recorded_call[2]['role_c'].rolename == 'role_c')


def test_function_mapped_complete() :
    global recorded_calls
    plan = TestPlan(
        [
            TestPlanSession(
                TestPlanConstellation(
                    [
                        TestPlanConstellationRole(
                            'role_a',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_b',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_c',
                            StubNodeDriver.__name__
                        )
                    ]
                ),
                [
                    TestPlanTestSpec(
                        stub_test_function3_needs_mapping.__name__,
                        {
                            'function_role_a' : 'role_a',
                            'function_role_b' : 'role_b',
                            'function_role_c' : 'role_c',
                        }
                    )
                ]
            )
        ]
    )
    plan.check_can_be_executed()

    test_run = TestRun(plan)
    test_run.run()

    print_recorded_calls()

    assert(len(recorded_calls) == 1)
    recorded_call = recorded_calls[0]
    assert(recorded_call[0] == stub_test_function3_needs_mapping)
    assert(recorded_call[1] == None )
    assert(len(recorded_call[2]) == 3)
    assert(recorded_call[2]['function_role_a'].rolename == 'role_a')
    assert(recorded_call[2]['function_role_b'].rolename == 'role_b')
    assert(recorded_call[2]['function_role_c'].rolename == 'role_c')


def test_function_mapped_incomplete() :
    global recorded_calls
    plan = TestPlan(
        [
            TestPlanSession(
                TestPlanConstellation(
                    [
                        TestPlanConstellationRole(
                            'role_a',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_b',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_c',
                            StubNodeDriver.__name__
                        )
                    ]
                ),
                [
                    TestPlanTestSpec(
                        stub_test_function3_needs_mapping.__name__
                    )
                ]
            )
        ]
    )
    with pytest.raises(TestPlanError):
        plan.check_can_be_executed()


### tests for class-based tests ###

def test_class_unmapped() :
    global recorded_calls
    plan = TestPlan(
        [
            TestPlanSession(
                TestPlanConstellation(
                    [
                        TestPlanConstellationRole(
                            'role_a',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_b',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_c',
                            StubNodeDriver.__name__
                        )
                    ]
                ),
                [
                    TestPlanTestSpec(
                        StubTest3.__name__
                    )
                ]
            )
        ]
    )
    plan.check_can_be_executed()

    test_run = TestRun(plan)
    test_run.run()

    assert(len(recorded_calls) == 3)

    recorded_call0 = recorded_calls[0]
    assert(recorded_call0[0] == StubTest3.__init__)
    assert(recorded_call0[1] != None)
    assert(len(recorded_call0[2]) == 3)
    assert(recorded_call0[2]['role_a'].rolename == 'role_a')
    assert(recorded_call0[2]['role_b'].rolename == 'role_b')
    assert(recorded_call0[2]['role_c'].rolename == 'role_c')

    recorded_call1 = recorded_calls[1]
    assert(recorded_call1[0] == StubTest3.step1)
    assert(recorded_call1[1] == recorded_call0[1]) # same instance
    assert(len(recorded_call1[2]) == 0)

    recorded_call2 = recorded_calls[2]
    assert(recorded_call2[0] == StubTest3.step2)
    assert(recorded_call2[1] == recorded_call0[1]) # same instance
    assert(len(recorded_call2[2]) == 0)



def test_class_unmapped_incomplete() :
    global recorded_calls
    plan = TestPlan(
        [
            TestPlanSession(
                TestPlanConstellation(
                    [
                        TestPlanConstellationRole(
                            'role_a',
                            StubNodeDriver.__name__
                        ),
                        # role_b missin
                        TestPlanConstellationRole(
                            'role_c',
                            StubNodeDriver.__name__
                        )
                    ]
                ),
                [
                    TestPlanTestSpec(
                        StubTest3.__name__
                    )
                ]
            )
        ]
    )
    with pytest.raises(TestPlanError):
        plan.check_can_be_executed()


def test_class_unmapped_surplus() :
    global recorded_calls
    plan = TestPlan(
        [
            TestPlanSession(
                TestPlanConstellation(
                    [
                        TestPlanConstellationRole(
                            'role_a',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole( # insert in the middle
                            'role_d',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_b',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_c',
                            StubNodeDriver.__name__
                        )
                    ]
                ),
                [
                    TestPlanTestSpec(
                        StubTest3.__name__
                    )
                ]
            )
        ]
    )
    plan.check_can_be_executed()

    test_run = TestRun(plan)
    test_run.run()

    assert(len(recorded_calls) == 3)

    recorded_call0 = recorded_calls[0]
    assert(recorded_call0[0] == StubTest3.__init__)
    assert(recorded_call0[1] != None)
    assert(len(recorded_call0[2]) == 3)
    assert(recorded_call0[2]['role_a'].rolename == 'role_a')
    assert(recorded_call0[2]['role_b'].rolename == 'role_b')
    assert(recorded_call0[2]['role_c'].rolename == 'role_c')

    recorded_call1 = recorded_calls[1]
    assert(recorded_call1[0] == StubTest3.step1)
    assert(recorded_call1[1] == recorded_call0[1]) # same instance
    assert(len(recorded_call1[2]) == 0)

    recorded_call2 = recorded_calls[2]
    assert(recorded_call2[0] == StubTest3.step2)
    assert(recorded_call2[1] == recorded_call0[1]) # same instance
    assert(len(recorded_call2[2]) == 0)



def test_class_mapped_complete() :
    global recorded_calls
    plan = TestPlan(
        [
            TestPlanSession(
                TestPlanConstellation(
                    [
                        TestPlanConstellationRole(
                            'role_a',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_b',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_c',
                            StubNodeDriver.__name__
                        )
                    ]
                ),
                [
                    TestPlanTestSpec(
                        StubTest3NeedsMapping.__name__,
                        {
                            'class_role_a' : 'role_a',
                            'class_role_b' : 'role_b',
                            'class_role_c' : 'role_c',
                        }
                    )
                ]
            )
        ]
    )
    plan.check_can_be_executed()

    test_run = TestRun(plan)
    test_run.run()

    assert(len(recorded_calls) == 3)

    recorded_call0 = recorded_calls[0]
    assert(recorded_call0[0] == StubTest3NeedsMapping.__init__)
    assert(recorded_call0[1] != None)
    assert(len(recorded_call0[2]) == 3)
    assert(recorded_call0[2]['class_role_a'].rolename == 'role_a')
    assert(recorded_call0[2]['class_role_b'].rolename == 'role_b')
    assert(recorded_call0[2]['class_role_c'].rolename == 'role_c')

    recorded_call1 = recorded_calls[1]
    assert(recorded_call1[0] == StubTest3NeedsMapping.step1)
    assert(recorded_call1[1] == recorded_call0[1]) # same instance
    assert(len(recorded_call1[2]) == 0)

    recorded_call2 = recorded_calls[2]
    assert(recorded_call2[0] == StubTest3NeedsMapping.step2)
    assert(recorded_call2[1] == recorded_call0[1]) # same instance
    assert(len(recorded_call2[2]) == 0)


def test_class_mapped_incomplete() :
    global recorded_calls
    plan = TestPlan(
        [
            TestPlanSession(
                TestPlanConstellation(
                    [
                        TestPlanConstellationRole(
                            'role_a',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_b',
                            StubNodeDriver.__name__
                        ),
                        TestPlanConstellationRole(
                            'role_c',
                            StubNodeDriver.__name__
                        )
                    ]
                ),
                [
                    TestPlanTestSpec(
                        StubTest3NeedsMapping.__name__
                    )
                ]
            )
        ]
    )
    with pytest.raises(TestPlanError):
        plan.check_can_be_executed()
