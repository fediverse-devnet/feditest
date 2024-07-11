from abc import ABC, abstractmethod
from datetime import datetime
import json
import os
import os.path
import re
import shutil
import sys
import traceback
from typing import IO, Iterator, Optional

import jinja2
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

        return TestRunResultTranscript(str(exc.__class__.__name__), spec_level, interop_level, stacktrace, str(exc))


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
        return len(self.errors)


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
        pass # FIXME


    def add_run_result(self, result: TestRunResultTranscript | None):
        pass # FIXME


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
    plan_session_index: int
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
               self._write(out)
        else:
            self._write(sys.stdout)


    @abstractmethod
    def _write(self, fd: IO[str]):
        ...


class SummaryTestRunTranscriptSerializer(TestRunTranscriptSerializer):
    """
    Knows how to serialize a TestRunTranscript into a single-line summary.
    """
    def _write(self, fd: IO[str]):
        summary = self.transcript.build_summary()

        print(f'Test summary: total={ summary.n_total }'
              + f', passed={ summary.n_passed }'
              + f', failed={ summary.n_failed }'
              + f', skipped={ summary.n_skipped }'
              + f', errors={ summary.n_errored }.',
              file=fd)


class TapTestRunTranscriptSerializer(TestRunTranscriptSerializer):
    """
    Knows how to serialize a TestRunTranscript into a report in TAP format.
    """
    def _write(self, fd: IO[str]):
        plan = self.transcript.plan
        summary = self.transcript.build_summary()

        fd.write("TAP version 14\n")
        fd.write(f"# test plan: { plan }\n")
        for key in ['started', 'ended', 'platform', 'username', 'hostname']:
            value = getattr(self.transcript, key)
            if value:
                fd.write(f"# {key}: {value}\n")

        test_id = 0
        for session_transcript in self.transcript.sessions:
            plan_session = plan.sessions[session_transcript.plan_session_index]
            constellation = plan_session.constellation

            fd.write(f"# session: { plan_session }\n")
            fd.write(f"# constellation: { constellation }\n")
            fd.write("#   roles:\n")
            for role_name, node in plan_session.constellation.roles.items():
                if role_name in session_transcript.constellation.nodes:
                    transcript_role = session_transcript.constellation.nodes[role_name]
                    fd.write(f"#     - name: {role_name}\n")
                    if node:
                        fd.write(f"#       driver: {node.nodedriver}\n")
                    fd.write(f"#       app: {transcript_role.appdata['app']}\n")
                    fd.write(f"#       app_version: {transcript_role.appdata['app_version'] or '?'}\n")
                else:
                    fd.write(f"#     - name: {role_name} -- not instantiated\n")

            for test_index, run_test in enumerate(session_transcript.run_tests):
                test_id += 1

                plan_test_spec = plan_session.tests[run_test.plan_test_index]
                test_meta = self.transcript.test_meta[plan_test_spec.name]

                result =  run_test.worst_result
                if result:
                    fd.write(f"not ok {test_id} - {test_meta.name}\n")
                    fd.write("  ---\n")
                    fd.write(f"  problem: {result.type} ({ result.spec_level }, { result.interop_level })\n")
                    if result.msg:
                        fd.write("  message:\n")
                        fd.write("\n".join( [ f"    { p }" for p in result.msg.strip().split("\n") ] ) + "\n")
                    fd.write("  where:\n")
                    for loc in result.stacktrace:
                        fd.write(f"    {loc[0]} {loc[1]}\n")
                    fd.write("  ...\n")
                else:
                    directives = "" # FIXME f" # SKIP {test.skip}" if test.skip else ""
                    fd.write(f"ok {test_id} - {test_meta.name}{directives}\n")

        fd.write(f"1..{test_id}\n")
        fd.write("# test run summary:\n")
        fd.write(f"#   total: {summary.n_total}\n")
        fd.write(f"#   passed: {summary.n_passed}\n")
        fd.write(f"#   failed: {summary.n_failed}\n")
        fd.write(f"#   skipped: {summary.n_skipped}\n")
        fd.write(f"#   errors: {summary.n_errored}\n")


class MultifileRunTranscriptSerializer:
    """Generates the Feditest reports into a test matrix and a linked, separate
    file per session. It uses a template path (comma-delimited string)
    so variants of reports can be generated while sharing common templates. The file_ext
    can be specified to support generating other formats like MarkDown.

    The generation uses two primary templates. The 'test_matrix.jinja2' template is used for
    the matrix generation and 'test_session.jinja2' is used for session file generation.

    Any files in the a directory called "static" in a template folder will be copied verbatim
    to the output directory (useful for css, etc.). If a file exists in the static folder of more
    than one directory in the template path, earlier path entries will overwrite later ones.
    """

    def __init__(
        self,
        matrix_file: str | os.PathLike,
        template_path: str,
        file_ext: str = "html"
    ):
        self.matrix_file = matrix_file
        templates_base_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.template_path = [
            os.path.join(templates_base_dir, t) for t in template_path.split(",")
        ]
        self.file_ext = file_ext


    def write(self, transcript: TestRunTranscript):
        dir, base_matrix_file = os.path.split(self.matrix_file)
        self._copy_static_files_to(dir)

        jinja2_env = self._init_jinja2_env()

        def session_file_path(plan_session):
            last_dot = base_matrix_file.rfind('.')
            if last_dot > 0:
                ret = f'{ base_matrix_file[0:last_dot] }.{ plan_session.name }.{ self.file_ext }'
            else:
                ret = f'{ base_matrix_file }.{ plan_session.name }.{ self.file_ext }'
            return ret

        context = dict(
            feditest=feditest,
            run=transcript,
            summary=transcript.build_summary(),
            getattr=getattr,
            sorted=sorted,
            enumerate=enumerate,
            get_results_for=_get_results_for,
            remove_white=lambda s: re.sub("[ \t\n\a]", "_", str(s)),
            session_file_path=session_file_path,
            matrix_file_path=base_matrix_file,
            permit_line_breaks_in_identifier=lambda s: re.sub(
                r"(\.|::)", r"<wbr>\1", s
            ),
            local_name_with_tooltip=lambda n: f'<span title="{ n }">{ n.split(".")[-1] }</span>',
            format_timestamp=lambda ts: ts.isoformat() if ts else "",
            format_duration=lambda s: str(s), # makes it easier to change in the future
            len=len
        )

        with open(self.matrix_file, "w") as fp:
            matrix_template = jinja2_env.get_template("test_matrix.jinja2")
            fp.write(matrix_template.render(**context))

        session_template = jinja2_env.get_template("test_session.jinja2")
        for run_session in transcript.sessions:
            session_context = dict(context)
            session_context.update(
                run_session=run_session,
                summary=run_session.build_summary(),
            )
            plan_session = transcript.plan.sessions[run_session.plan_session_index]
            with open(os.path.join(dir, session_file_path(plan_session)), "w" ) as fp:
                fp.write(session_template.render(**session_context))


    def _init_jinja2_env(self) -> jinja2.Environment:
        templates = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_path)
        )
        templates.filters["regex_sub"] = lambda s, pattern, replacement: re.sub(
            pattern, replacement, s
        )
        return templates


    def _copy_static_files_to(self, dir: str | os.PathLike):
        for path in reversed(self.template_path):
            static_dir = os.path.join(path, "static")
            if os.path.exists(static_dir):
                for dirpath, _, filenames in os.walk(static_dir):
                    if len(filenames) == 0:
                        continue
                    filedir_to = os.path.join(
                        dir, os.path.relpath(dirpath, static_dir)
                    )
                    if not os.path.exists(filedir_to):
                        os.makedirs(filedir_to, exist_ok=True)
                    for filename in filenames:
                        filepath_from = os.path.join(dirpath, filename)
                        filepath_to = os.path.join(filedir_to, filename)
                        # Notusing copytree since it would copy static too
                        shutil.copyfile(filepath_from, filepath_to)


def _get_results_for(run_transcript: TestRunTranscript, session_transcript: TestRunSessionTranscript, test_meta: TestMetaTranscript) -> Iterator[TestRunResultTranscript | None]:
    """
    Determine the set of test results running test_meta within session_transcript, and return it as an Iterator.
    This is a set, not a single value, because we might run the same test multiple times (perhaps with differing role
    assignments) in the same session. The run_transcript is passed in because session_transcript does not have a pointer "up".
    """
    plan_session = run_transcript.plan.sessions[session_transcript.plan_session_index]
    for test_transcript in session_transcript.run_tests:
        plan_testspec = plan_session.tests[test_transcript.plan_test_index]
        if plan_testspec.name == test_meta.name:
            yield test_transcript.worst_result
    return None


class JsonTestRunTranscriptSerializer(TestRunTranscriptSerializer):
    """
    An object that knows how to serialize a TestRun into JSON format
    """
    def _write(self, fd: IO[str]):
        self.transcript.write(fd)
