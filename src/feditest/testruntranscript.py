import json
import os.path
import re
import traceback
from abc import ABC, abstractmethod
from contextlib import redirect_stdout
from datetime import datetime
from typing import Optional

import jinja2
import msgspec

from feditest.reporting import fatal
from feditest.testplan import TestPlan, TestPlanTestSpec
from feditest.utils import FEDITEST_VERSION


class TestRunNodeTranscript(msgspec.Struct):
    appdata: dict[str,str | None]


class TestRunConstellationTranscript(msgspec.Struct):
    nodes: dict[str,TestRunNodeTranscript]


class TestRunResultTranscript(msgspec.Struct):
    type: str
    stacktrace: list[tuple[str,int]]
    msg: str | None

    @staticmethod
    def create_if_present(exc: Exception | None):
        if exc is None:
            return None

        stacktrace: list[tuple[str,int]] = []
        for filename, line, _, _ in traceback.extract_tb(exc.__traceback__):
            stacktrace.append((filename, line))
        return TestRunResultTranscript(str(exc.__class__.__name__), stacktrace, str(exc), )


    def __str__(self):
        return self.msg


class TestRunTranscriptSummary:
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
    plan_test_index : int
    started : datetime
    ended : datetime
    result : TestRunResultTranscript | None
    run_steps : list[TestRunTestStepTranscript] | None = None # This is None if it's a function rather than a class


    def build_summary(self, augment_this: TestRunTranscriptSummary | None = None ):
        ret = augment_this or TestRunTranscriptSummary()

        # We treat the steps differently. They don't get their extra entry in the summary, but are abstracted into it.
        if self.result:
            ret.add_result(self.result) # non-success result on the level of the Test overrides
        else:
            worst_result : TestRunResultTranscript | None = None
            # if no other issues occurred than SoftAssertionFailures or DegradeAssertionFailures,
            #    the first one of those is the result
            # else
            #    the last exception is the result
            if self.run_steps:
                for run_step in self.run_steps:
                    if worst_result is None:
                        worst_result = run_step.result # may be None assignment
                    elif run_step.result is not None and run_step.result.type not in ['SoftAssertionFailure', 'DegradeAssertionFailure']:
                        worst_result = run_step.result

                self.result = worst_result
                ret.add_result(self.result)

        return ret


    def __str__(self):
        return f"Test {self.plan_test_index}"


class TestRunSessionTranscript(msgspec.Struct):
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
    plan : TestPlan
    id: str
    started: datetime
    ended: datetime
    platform: str
    username: str
    hostname: str
    sessions: list[TestRunSessionTranscript]
    result : TestRunResultTranscript | None
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
    def _write(self):
        summary = self.transcript.build_summary()

        print(f'Test summary: total={ summary.n_total }, passed={ summary.n_passed }'
              + f', failed={ summary.n_failed } (hard={ summary.n_hard_failed }, soft={ summary.n_soft_failed }, degrade={ summary.n_degrade_failed })'
              + f', skipped={ summary.n_skipped }, errors={ summary.n_errored }.')


class TapTestRunTranscriptSerializer(TestRunTranscriptSerializer):
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
            for role in plan_session.constellation.roles:
                transcript_role = session_transcript.constellation.nodes[role.name]
                print(f"#     - name: {role.name}")
                print(f"#       driver: {role.nodedriver}")
                print(f"#       app: {transcript_role.appdata['app']}")
                print(f"#       app_version: {transcript_role.appdata['app_version'] or '?'}")

            for test in plan_session.tests:
                test_id += 1
                if problem := _get_problem(self.transcript, session_transcript, test):
                    print(f"not ok {test_id} - {test.name}")
                    print("  ---")
                    print(f"  problem: {problem.type}")
                    if problem.msg:
                        print("  message:")
                        print("\n".join( [ f"    { p }" for p in problem.msg.strip().split("\n") ] ))
                    print("  where:")
                    for loc in problem.stacktrace:
                        print(f"    {loc[0]} {loc[1]}")
                    print("  ...")

                else:
                    directives = f" # SKIP {test.disabled}" if test.disabled else ""
                    print(f"ok {test_id} - {test.name}{directives}")
        print(f"1..{test_id}")
        print("# test run summary:")
        print(f"#   total: {summary.n_total}")
        print(f"#   passed: {summary.n_passed}")
        print(f"#   failed: {summary.n_failed}")
        print(f"#   skipped: {summary.n_skipped}")
        print(f"#   errors: {summary.n_errored}")


class HtmlTestRunTranscriptSerializer(TestRunTranscriptSerializer):
    def __init__(self, transcript: TestRunTranscript, template_name: str | None = None ):
        super().__init__(transcript)
        self.template_name = template_name or 'report-standalone.jinja2'
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

        print(template.render(
                run=self.transcript,
                summary=self.transcript.build_summary(),
                all_tests = sorted(
                    {test.name: test for s in self.transcript.plan.sessions for test in s.tests}.values(),
                    key=lambda t: t.name,
                ),
                getattr=getattr,
                get_problem=_get_problem,
                remove_white=lambda s: re.sub('[ \t\n\a]', '_', str(s)),
                local_name_with_tooltip=lambda n: f'<span title="{ n }">{ n.split(".")[-1] }</span>'))


def _get_problem(run_transcript: TestRunTranscript, session_transcript: TestRunSessionTranscript, test: TestPlanTestSpec) -> TestRunResultTranscript | None:
    plan_session = run_transcript.plan.sessions[session_transcript.plan_session_index
                                                ]
    for test_transcript in session_transcript.run_tests:
        plan_test = plan_session.tests[test_transcript.plan_test_index]
        if plan_test.name == test.name and test_transcript.result:
            return test_transcript.result
    return None


class JsonTestRunTranscriptSerializer(TestRunTranscriptSerializer):
    """
    An object that knows how to serialize a TestRun into JSON format
    """
    def _write(self):
        self.transcript.print()
