import json
import os.path
import re
import traceback
from abc import ABC, abstractmethod
from contextlib import redirect_stdout
from datetime import datetime
from typing import Any, Iterator, Optional

import jinja2
import msgspec

import feditest
from feditest.reporting import fatal
from feditest.testplan import TestPlan
from feditest.utils import FEDITEST_VERSION


class TestRunNodeTranscript(msgspec.Struct):
    """
    Information about a node in a constellation in a transcript.
    """
    appdata: dict[str, str | None]
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
    problem_category: str
    stacktrace: list[tuple[str,int]]
    msg: str | None


    @staticmethod
    def create_if_present(exc: Exception | None):
        if exc is None:
            return None

        stacktrace: list[tuple[str,int]] = []
        for filename, line, _, _ in traceback.extract_tb(exc.__traceback__):
            stacktrace.append((filename, line))
        if isinstance(exc, feditest.HardAssertionFailure):
            category = 'hard'
        elif isinstance(exc, feditest.SoftAssertionFailure):
            category = 'soft'
        elif isinstance(exc, feditest.DegradeAssertionFailure):
            category = 'degrade'
        elif isinstance(exc, feditest.SkipTestException):
            category = 'skip'
        else:
            category = 'error'
        return TestRunResultTranscript(str(exc.__class__.__name__), category, stacktrace, str(exc))


    def status(self):
        """
        Construct a status message
        """
        ret = self.type
        if self.msg:
            ret += f': { self.msg.strip() }'
        return ret


    def details(self):
        return str(self)


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


    def __str__(self):
        ret = self.type
        if self.msg:
            ret += f': { self.msg.strip() }'
        for frame in self.stacktrace:
            ret += f'\n    {frame[0]}:{frame[1]}'
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
        self.hard_failures : list[TestRunResultTranscript] = []
        self.soft_failures : list[TestRunResultTranscript] = []
        self.degrade_failures : list[TestRunResultTranscript] = []
        self.skips : list[TestRunResultTranscript] = []
        self.interaction_controls : list[TestRunResultTranscript] = []
        self.errors : list[TestRunResultTranscript] = []
        self.tests : list[TestRunTestTranscript] = []


    @property
    def n_total(self):
        return len(self.tests)


    @property
    def n_hard_failed(self):
        return len(self.hard_failures)


    @property
    def n_soft_failed(self):
        return len(self.soft_failures)


    @property
    def n_degrade_failed(self):
        return len(self.degrade_failures)


    @property
    def n_failed(self):
        return len(self.hard_failures) + len(self.soft_failures) + len(self.degrade_failures)


    @property
    def n_skipped(self):
        return len(self.skips)


    @property
    def n_errored(self):
        return len(self.errors)


    @property
    def n_passed(self):
        return self.n_total - self.n_hard_failed - self.n_soft_failed - self.n_degrade_failed - self.n_skipped - self.n_errored


    def add_result(self, result: TestRunResultTranscript | None):
        if result is None:
            return
        if result.type.endswith('HardAssertionFailure'):
            self.hard_failures.append(result)
        elif result.type.endswith('SoftAssertionFailure'):
            self.soft_failures.append(result)
        elif result.type.endswith('DegradeAssertionFailure'):
            self.degrade_failures.append(result)
        elif result.type.endswith('SkipTestException'):
            self.skips.append(result)
        elif result.type.endswith('AbortTestRunException') or result.type.endswith('AbortTestRunSessionException') or result.type.endswith('AbortTestException'):
            self.interaction_controls.append(result)
        else:
            self.errors.append(result)


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


    def build_summary(self, augment_this: TestRunTranscriptSummary | None = None ):
        ret = augment_this or TestRunTranscriptSummary()

        ret.add_result(self.worst_result)
        return ret


    def __str__(self):
        return f"Test {self.plan_test_index}"


class TestRunSessionTranscript(msgspec.Struct):
    """
    Captures information about the run of a single session in a transcript.
    """
    plan_session_index: int
    started : datetime
    ended : datetime
    constellation: TestRunConstellationTranscript
    run_tests : list[TestRunTestTranscript]
    result : TestRunResultTranscript | None


    def build_summary(self, augment_this: TestRunTranscriptSummary | None = None ):
        ret = augment_this or TestRunTranscriptSummary()
        ret.add_result(self.result)

        for run_test in self.run_tests:
            run_test.build_summary(ret)
            ret.add_run_test(run_test)

        return ret


    def __str__(self):
        return f"Session {self.plan_session_index}"


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
    result : TestRunResultTranscript | None
    platform: str | None
    username: str | None
    hostname: str | None
    type: str = 'feditest-testrun-transcript'
    feditest_version: str = FEDITEST_VERSION


    def build_summary(self, augment_this: TestRunTranscriptSummary | None = None ):
        ret = augment_this or TestRunTranscriptSummary()
        ret.add_result(self.result)

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


    def print(self) -> None:
        print(self.as_json().decode('utf-8'))


    @staticmethod
    def load(filename: str) -> 'TestRunTranscript':
        """
        Read a file, and instantiate a TestRunTranscript from what we find.
        """
        with open(filename, 'r', encoding='utf-8') as f:
            transcript_json = json.load(f)

        return msgspec.convert(transcript_json, type=TestRunTranscript)


    def has_compatible_version(self):
        if not self.feditest_version:
            return True
        return self.feditest_version == FEDITEST_VERSION


    def __str__(self):
        if self.plan.name:
            return f'{ self.id } ({ self.plan.name })'
        return self.id


class TestRunTranscriptSerializer(ABC):
    """
    An object that knows how to serialize a TestRunTranscript into some output format.
    """
    def __init__(self, transcript: TestRunTranscript ):
        self.transcript = transcript


    def write(self, dest: str | None = None):
        """
        dest: name of the file to write to, or stdout
        """
        if dest and isinstance(dest,str):
            with open(dest, "w", encoding="utf8") as out:
                with redirect_stdout(out):
                    self._write()
        else:
            self._write()


    @abstractmethod
    def _write(self):
        ...


class SummaryTestRunTranscriptSerializer(TestRunTranscriptSerializer):
    """
    Knows how to serialize a TestRunTranscript into a single-line summary.
    """
    def _write(self):
        summary = self.transcript.build_summary()

        print(f'Test summary: total={ summary.n_total }, passed={ summary.n_passed }'
              + f', failed={ summary.n_failed } (hard={ summary.n_hard_failed }, soft={ summary.n_soft_failed }, degrade={ summary.n_degrade_failed })'
              + f', skipped={ summary.n_skipped }, errors={ summary.n_errored }.')


class TapTestRunTranscriptSerializer(TestRunTranscriptSerializer):
    """
    Knows how to serialize a TestRunTranscript into a report in TAP format.
    """
    def _write(self):
        plan = self.transcript.plan
        summary = self.transcript.build_summary()

        print("TAP version 14")
        print(f"# test plan: { plan }")
        for key in ['started', 'ended', 'platform', 'username', 'hostname']:
            value = getattr(self.transcript, key)
            if value:
                print(f"# {key}: {value}")

        test_id = 0
        for session_transcript in self.transcript.sessions:
            plan_session = plan.sessions[session_transcript.plan_session_index]
            constellation = plan_session.constellation

            print(f"# session: { plan_session }")
            print(f"# constellation: { constellation }")
            print("#   roles:")
            for role_name, node in plan_session.constellation.roles.items():
                transcript_role = session_transcript.constellation.nodes[role_name]
                print(f"#     - name: {role_name}")
                print(f"#       driver: {node.nodedriver}")
                print(f"#       app: {transcript_role.appdata['app']}")
                print(f"#       app_version: {transcript_role.appdata['app_version'] or '?'}")


            for test_index, run_test in enumerate(session_transcript.run_tests):
                test_id += 1

                plan_test_spec = plan_session.tests[run_test.plan_test_index]
                test_meta = self.transcript.test_meta[plan_test_spec.name]

                result = _get_result_for_test(self.transcript, session_transcript, test_index, run_test)
                if result:
                    print(f"not ok {test_id} - {test_meta.name}")
                    print("  ---")
                    print(f"  problem: {result.type} ({result.problem_category})")
                    print("  message:")
                    print("\n".join( [ f"    { p }" for p in result.msg.strip().split("\n") ] ))
                    print("  where:")
                    for loc in result.stacktrace:
                        print(f"    {loc[0]} {loc[1]}")
                    print("  ...")
                else:
                    directives = "" # FIXME f" # SKIP {test.disabled}" if test.disabled else ""
                    print(f"ok {test_id} - {test_meta.name}{directives}")

        print(f"1..{test_id}")
        print("# test run summary:")
        print(f"#   total: {summary.n_total}")
        print(f"#   passed: {summary.n_passed}")
        print(f"#   failed: {summary.n_failed}")
        print(f"#   skipped: {summary.n_skipped}")
        print(f"#   errors: {summary.n_errored}")


class HtmlTestRunTranscriptSerializer(TestRunTranscriptSerializer):
    """
    Knows how to serialize a TestRunTrascript into HTML using any Jinja2 template.
    """
    def __init__(self, transcript: TestRunTranscript, template_name: str | None = None ):
        super().__init__(transcript)
        self.template_name = template_name or 'testrun-report-testmatrix-standalone.jinja2'
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.templates = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir)
        )

    def _write(self):
        try:
            template = self.templates.get_template(self.template_name)
        except jinja2.TemplateNotFound:
            try:
                template = self.templates.get_template(self.template_name + '.jinja2')
            except jinja2.TemplateNotFound:
                fatal('jinja2 template not found:', self.template_name)

        print(  template.render(
                run=self.transcript,
                summary=self.transcript.build_summary(),
                getattr=getattr,
                sorted=sorted,
                enumerate=enumerate,
                get_results_for=_get_results_for,
                get_result_for_test=_get_result_for_test,
                get_result_for_test_step=_get_result_for_test_step,
                remove_white=lambda s: re.sub('[ \t\n\a]', '_', str(s)),
                local_name_with_tooltip=lambda n: f'<span title="{ n }">{ n.split(".")[-1] }</span>',
                format_timestamp=lambda ts, format='%Y-%m-%dT%H-%M-%S.%fZ': ts.strftime(format) if ts else ''))


def _get_result_for_test(run_transcript: TestRunTranscript, session_transcript: TestRunSessionTranscript, test_index: int, test_transcript: TestRunTestTranscript) -> dict[str,Any]:
    return test_transcript.worst_result


def _get_result_for_test_step(run_transcript: TestRunTranscript, session_transcript: TestRunSessionTranscript, test_index: int, test_step_index: int, test_step_transcript: TestRunTestStepTranscript) -> dict[str,Any]:
    return test_step_transcript.result


def _get_results_for(run_transcript: TestRunTranscript, session_transcript: TestRunSessionTranscript, test_meta: TestMetaTranscript) -> Iterator[dict[str,Any]]:
    """
    Determine the set of test results running test_meta within session_transcript, and return it as an Iterator.
    This is a set, not a single value, because we might run the same test multiple times (perhaps with differing role
    assignments) in the same session. The run_transcript is passed in because session_transcript does not have a pointer "up".
    """
    plan_session = run_transcript.plan.sessions[session_transcript.plan_session_index]
    for test_index, test_transcript in enumerate(session_transcript.run_tests):
        plan_testspec = plan_session.tests[test_transcript.plan_test_index]
        if plan_testspec.name == test_meta.name:
            yield test_transcript.worst_result
    return None


class JsonTestRunTranscriptSerializer(TestRunTranscriptSerializer):
    """
    An object that knows how to serialize a TestRun into JSON format
    """
    def _write(self):
        self.transcript.print()
