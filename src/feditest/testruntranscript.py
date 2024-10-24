import json
import os
import os.path
import traceback
from datetime import datetime
from typing import IO, Optional

import msgspec

import feditest
import feditest.testplan
from feditest.testplan import TestPlan
from feditest.utils import FEDITEST_VERSION


class TestRunNodeTranscript(msgspec.Struct):
    """
    Information about a node in a constellation in a transcript.
    """
    appdata: dict[str, str | None]
    node_driver: str
    """
    So far, contains:
    app: name of the app running at the node (required)
    app_version: version of the app running at the node (optional)
    """


class TestRunConstellationTranscript(msgspec.Struct):
    """
    Information about a constellation in a trranscript
    """
    nodes: dict[str,TestRunNodeTranscript]

    def __str__(self):
        return ', '.join( [ f'{ role }: { node.node_driver }' for role, node in self.nodes.items() ] )


_result_transcript_tracker : list['TestRunResultTranscript'] = []
"""
Helps with assigning unique instance identifiers without adding it to the instance itself.
"""


class TestRunResultTranscript(msgspec.Struct):
    """
    Captures the result of running a step, test, session, or plan if it ended with
    an Exception. The properties of this class are derived from that exception.
    """
    type: str
    spec_level: str
    interop_level: str
    stacktrace: list[tuple[str,int]]
    msg: str | None


    @staticmethod
    def create_if_present(exc: Exception | None):
        if exc is None:
            return None

        if isinstance(exc, feditest.AssertionFailure):
            spec_level = exc.spec_level.name
            interop_level = exc.interop_level.name
        else:
            spec_level = feditest.SpecLevel.UNSPECIFIED.name
            interop_level = feditest.InteropLevel.UNKNOWN.name

        # for the stack trace:
        # 1. remove bottom and top frames that contain site-packages"
        # 2. remove all path prefixes through the current directory

        stacktrace: list[tuple[str,int]] = []
        pwd = os.path.abspath(os.getcwd()) + '/'
        for filename, line, _, _ in traceback.extract_tb(exc.__traceback__):
            if filename.find( 'site-packages/') >= 0:
                continue
            if filename.startswith(pwd):
                stacktrace.append((filename[len(pwd):], line))
            else:
                stacktrace.append((filename, line))
        msg = str(exc).strip()
        if not msg: # Happens e.g. for NotImplementedError
            msg = type(exc).__name__
        return TestRunResultTranscript(str(exc.__class__.__name__), spec_level, interop_level, stacktrace, msg)


    def title(self):
        """
        Construct a single-line title for this result.
        """
        ret = f'{ self.spec_level } { self.interop_level }'
        if self.msg:
            msg_lines = self.msg.strip().split('\n', maxsplit=1)
            ret += f': { msg_lines[0] }' # If it's multi-line, only use the first line
        return ret


    def short_title(self):
        """
        Construct a short single-line title for this result.
        """
        if self.msg:
            msg_lines = self.msg.strip().split('\n', maxsplit=1)
            return msg_lines[0]
        return 'Unnamed failure.'


    def stacktrace_as_text(self):
        return '\n'.join( [ f'{frame[0]}:{frame[1]}' for frame in self.stacktrace ])


    def id(self):
        """
        Construct a stable id for this result. This is used, for example, for HTML cross-referencing.
        """
        global _result_transcript_tracker
        for i, result in enumerate(_result_transcript_tracker):
            if result is self:
                return i
        ret = len(_result_transcript_tracker)
        _result_transcript_tracker.append(self)
        return ret


    def css_classes(self):
        """
        return a space-separated list of CSS classes to mark up the result with in HTML
        """
        return f'failed { self.spec_level } { self.interop_level }'.lower()


    def __str__(self):
        ret = self.type
        if self.msg:
            ret += f': { self.msg.strip() }'
        for frame in self.stacktrace:
            ret += f'\n{frame[0]}:{frame[1]}'
        return ret


class TestStepMetaTranscript(msgspec.Struct):
    """
    Captures information about a step in a test in a transcript.
    """
    name: str
    description: str | None


class TestMetaTranscript(msgspec.Struct):
    """
    Captures information about a test in a transcript.
    """
    name: str
    roles: set[str]
    steps: list[TestStepMetaTranscript] | None
    description: str | None


class TestRunTranscriptSummary:
    """
    Summary information derived from a transcript.
    This class is here in the middle of the file because other XXXTranscript classes need
    to reference it.
    """
    def __init__(self) -> None:
        self.failures : list[TestRunResultTranscript] = []
        self.skips : list[TestRunResultTranscript] = []
        self.interaction_controls : list[TestRunResultTranscript] = []
        self.errors : list[TestRunResultTranscript] = []
        self.tests : list[TestRunTestTranscript] = []
        self.errors_outside_tests : list[TestRunResultTranscript] = []


    def count_failures_for(self, spec_level: feditest.SpecLevel | None, interop_level: feditest.InteropLevel | None):
        current = self.failures
        if spec_level is not None:
            current = [ f for f in current if f.spec_level == spec_level.name ]
        if interop_level is not None:
            current = [ f for f in current if f.interop_level == interop_level.name ]
        return len(current)


    @property
    def n_total(self):
        return len(self.tests)


    @property
    def n_failed(self):
        return len(self.failures)


    @property
    def n_skipped(self):
        return len(self.skips)


    @property
    def n_errored(self):
        return len(self.errors) + len(self.errors_outside_tests)


    @property
    def n_passed(self):
        return len(self.tests) - len(self.failures) - len(self.skips) - len(self.errors)


    def add_test_result(self, result: TestRunResultTranscript | None):
        if result is None:
            return
        if result.type.endswith('AssertionFailure'):
            self.failures.append(result)
        elif result.type.endswith('SkipTestException') or result.type.endswith('NotImplementedByNodeError') or result.type.endswith('NotImplementedByNodeDriverError'):
            self.skips.append(result)
        elif result.type.endswith('AbortTestRunException') or result.type.endswith('AbortTestRunSessionException') or result.type.endswith('AbortTestException'):
            self.interaction_controls.append(result)
        else:
            self.errors.append(result)


    def add_session_result(self, result: TestRunResultTranscript | None):
        if result is None:
            return
        self.errors_outside_tests.append(result)


    def add_run_result(self, result: TestRunResultTranscript | None):
        if result is None:
            return
        self.errors_outside_tests.append(result)


    def add_run_test(self, run_test: Optional['TestRunTestTranscript']):
        if run_test is None:
            return
        self.tests.append(run_test)


class TestRunTestStepTranscript(msgspec.Struct):
    plan_step_index: int
    started : datetime
    ended : datetime
    result : TestRunResultTranscript | None


    def __str__(self):
        return f"TestStep {self.plan_step_index}"


class TestRunTestTranscript(msgspec.Struct):
    """
    Captures information about the run of a single test in a transcript.
    """
    plan_test_index : int
    started : datetime
    ended : datetime
    result : TestRunResultTranscript | None
    run_steps : list[TestRunTestStepTranscript] | None = None # This is None if it's a function rather than a class


    @property
    def worst_result(self) -> TestRunResultTranscript | None:
        if self.result:
            return self.result

        # The steps don't get their extra entry in the summary, but are abstracted into it.
        ret : TestRunResultTranscript | None = None
        # if no other issues occurred than SoftAssertionFailures or DegradeAssertionFailures,
        #    the first one of those is the result
        # else
        #    the last exception is the result
        if self.run_steps:
            for run_step in self.run_steps:
                if ret is None:
                    ret = run_step.result # may be None assignment
                elif run_step.result is not None and run_step.result.type not in ['SoftAssertionFailure', 'DegradeAssertionFailure']:
                    ret = run_step.result

        return ret


    def build_summary(self, augment_this: TestRunTranscriptSummary | None = None ) -> TestRunTranscriptSummary:
        ret = augment_this or TestRunTranscriptSummary()

        ret.add_test_result(self.worst_result)
        return ret


    def __str__(self):
        return f"Test {self.plan_test_index}"


class TestRunSessionTranscript(msgspec.Struct):
    """
    Captures information about the run of a single session in a transcript.
    """
    run_session_index: int
    started : datetime
    ended : datetime
    constellation: TestRunConstellationTranscript
    run_tests : list[TestRunTestTranscript]
    result : TestRunResultTranscript | None


    def build_summary(self, augment_this: TestRunTranscriptSummary | None = None ):
        ret = augment_this or TestRunTranscriptSummary()
        ret.add_session_result(self.result)

        for run_test in self.run_tests:
            run_test.build_summary(ret)
            ret.add_run_test(run_test)

        return ret


    def __str__(self):
        return f"Session {self.run_session_index}"


class TestRunTranscript(msgspec.Struct):
    """
    Captures all information about a single test run in a transcript.
    """
    plan : TestPlan
    id: str
    started: datetime
    ended: datetime
    sessions: list[TestRunSessionTranscript]
    test_meta: dict[str,TestMetaTranscript] # key: name of the test
    result : TestRunResultTranscript | None # for interactive user input like abort
    platform: str | None
    username: str | None
    hostname: str | None
    type: str = 'feditest-testrun-transcript'
    feditest_version: str = FEDITEST_VERSION


    def build_summary(self, augment_this: TestRunTranscriptSummary | None = None ):
        ret = augment_this or TestRunTranscriptSummary()
        ret.add_run_result(self.result)

        for session in self.sessions:
            session.build_summary(ret)
        return ret


    def as_json(self) -> bytes:
        ret = msgspec.json.encode(self)
        ret = msgspec.json.format(ret, indent=4)
        return ret


    def save(self, filename: str) -> None:
        with open(filename, 'wb') as f:
            f.write(self.as_json())


    def write(self, fd: IO[str]) -> None:
        fd.write(self.as_json().decode('utf-8'))


    @staticmethod
    def load(filename: str) -> 'TestRunTranscript':
        """
        Read a file, and instantiate a TestRunTranscript from what we find.
        """
        with open(filename, 'r', encoding='utf-8') as f:
            transcript_json = json.load(f)

        return msgspec.convert(transcript_json, type=TestRunTranscript)


    def is_compatible_type(self):
        return self.type is None or self.type == 'feditest-testrun-transcript'


    def has_compatible_version(self):
        if not self.feditest_version:
            return True
        return self.feditest_version == FEDITEST_VERSION


    def __str__(self):
        if self.plan.name:
            return f'{ self.id } ({ self.plan.name })'
        return self.id

