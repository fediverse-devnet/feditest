"""
Classes that know how to control a TestRun.
"""

from abc import ABC, abstractmethod

import feditest.testrun


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
    def determine_next_session_index(self, last_session_index: int = -1) -> int:
        """
        last_session_index: -1 means: we haven't started yet
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
    def determine_next_session_index(self, last_session_index: int = -1) -> int:
        return last_session_index+1


    def determine_next_test_index(self, last_test_index: int = -1) -> int:
        return last_test_index+1


    def determine_next_test_step_index(self, last_test_step_index: int = -1) -> int:
        return last_test_step_index+1


class InteractiveTestRunController(TestRunController):
    def determine_next_session_index(self, last_session_index: int = -1) -> int:
        """
        A TestRunSession has just completed. Which TestRunSession should we run next?
        """
        if last_session_index >= 0:
            prompt = 'Which TestSession to run next? n(ext session), r(repeat just completed session), (session number), q(uit): '
        else:
            prompt = 'Which TestSession to run first? n(ext/first session), (session number), q(uit): '
        while True:
            answer = self._prompt_user(prompt)
            match answer:
                case 'n':
                    return last_session_index+1
                case 'r':
                    return last_session_index
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
        ret = input(f'Interactive: { question }')
        return ret
