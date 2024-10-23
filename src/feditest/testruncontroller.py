"""
Classes that know how to control a TestRun.
"""

from abc import ABC, abstractmethod

import feditest.testrun
from feditest.reporting import is_trace_active

class TestRunControlException(Exception,ABC):
    """
    Superclass of all exceptions we use to control test run execution.
    """
    pass


class AbortTestRunException(TestRunControlException):
    """
    Stop executing this test run as quickly as possible.
    Don't run any more test steps and tests. Shut down the current constellation and don't run any more sessions.
    """
    pass


class AbortTestRunSessionException(TestRunControlException):
    """
    Stop executing this test run session as quickly as possible, and continue with the next test run session.
    """
    pass


class AbortTestException(TestRunControlException):
    """
    Stop executing this test as quickly as possible, and continue with the next test in the current test run session.
    """
    pass


class TestRunController(ABC):
    def __init__(self, run: 'feditest.testrun.TestRun' ):
        self.run = run


    @abstractmethod
    def determine_next_constellation_index(self, last_constellation_index: int = -1) -> int:
        """
        last_constellation_index: -1 means: we haven't started yet
        """
        ...


    @abstractmethod
    def determine_next_test_index(self, last_test_index: int = -1) -> int:
        """
        last_test_index: -1 means: we haven't started yet
        """
        ...


    @abstractmethod
    def determine_next_test_step_index(self, last_test_step_index: int = -1) -> int:
        """
        last_test_step_index: -1 means: we haven't started yet
        """
        ...


class AutomaticTestRunController(TestRunController):
    def determine_next_constellation_index(self, last_constellation_index: int = -1) -> int:
        return last_constellation_index+1


    def determine_next_test_index(self, last_test_index: int = -1) -> int:
        return last_test_index+1


    def determine_next_test_step_index(self, last_test_step_index: int = -1) -> int:
        return last_test_step_index+1


class InteractiveTestRunController(TestRunController):
    def determine_next_constellation_index(self, last_constellation_index: int = -1) -> int:
        """
        A TestRunSession with a certain TestRunConstellation has just completed. Which TestRunConstellation should
        we run it with next?
        """
        if last_constellation_index >= 0:
            prompt = 'Which Constellation to run tests with next? n(ext constellation), r(repeat just completed constellation), (constellation number), q(uit): '
        else:
            prompt = 'Which Constellation to run first? n(ext/first constellation), (constellation number), q(uit): '
        while True:
            answer = self._prompt_user(prompt)
            match answer:
                case 'n':
                    return last_constellation_index+1
                case 'r':
                    return last_constellation_index
                case 'q':
                    raise AbortTestRunException()
            try:
                parsed = int(answer)
                if parsed >= 0:
                    return parsed
            except ValueError:
                pass
            print('Command not recognized, try again.')


    def determine_next_test_index(self, last_test_index: int = -1) -> int:
        """
        A Test has just completed. Which Test should we run next?
        """
        if last_test_index >= 0:
            prompt = 'Which Test to run next? n(ext test), r(repeat just completed test), a(bort current session), q(uit): '
        else:
            prompt = 'Which Test to run first? n(ext/first test), (test number), a(bort current session), q(uit): '
        while True:
            answer = self._prompt_user(prompt)
            match answer:
                case 'n':
                    return last_test_index+1
                case 'r':
                    return last_test_index
                case 'a':
                    raise AbortTestRunSessionException()
                case 'q':
                    raise AbortTestRunException()
            try:
                parsed = int(answer)
                if parsed >= 0:
                    return parsed
            except ValueError:
                pass
            print('Command not recognized, try again.')


    def determine_next_test_step_index(self, last_test_step_index: int = -1) -> int:
        """
        A Test Step as just completed. Which Test Step should we run next?
        """
        if last_test_step_index >= 0:
            prompt = 'Which Test Step to run next? n(ext test step), r(repeat just completed test test), c(ancel current test), a(bort current session), q(uit): '
        else:
            prompt = 'Which Test Step to run first? n(ext/first test step), (test step number), c(ancel current test), a(bort current session), q(uit): '
        while True:
            answer = self._prompt_user(prompt)
            match answer:
                case 'n':
                    return last_test_step_index+1
                case 'r':
                    return last_test_step_index
                case 'c':
                    raise AbortTestException()
                case 'a':
                    raise AbortTestRunSessionException()
                case 'q':
                    raise AbortTestRunException()
            try:
                parsed = int(answer)
                if parsed >= 0:
                    return parsed
            except ValueError:
                pass
            print('Command not recognized, try again.')


    def _prompt_user(self, question: str) -> str:
        # In case of debugging, there's a lot of output, and it can be hard to tell where the steps end
        if is_trace_active():
            print()

        ret = input(f'Interactive: { question }')

        if is_trace_active():
            print()

        return ret
