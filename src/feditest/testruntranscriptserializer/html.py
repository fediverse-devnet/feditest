# import contextlib
import html
import os.path
import re
import shutil
from typing import Any, Iterator

import jinja2

import feditest
from feditest.reporting import fatal
from feditest.testruntranscript import TestMetaTranscript, TestRunResultTranscript, TestRunSessionTranscript, TestRunTranscript
from feditest.testruntranscriptserializer import TestRunTranscriptSerializer


def _get_results_for(run_transcript: TestRunTranscript, session_transcript: TestRunSessionTranscript, test_meta: TestMetaTranscript) -> Iterator[TestRunResultTranscript | None]:
    """
    Determine the set of test results running test_meta within session_transcript, and return it as an Iterator.
    This is a set, not a single value, because we might run the same test multiple times (perhaps with differing role
    assignments) in the same session. The run_transcript is passed in because session_transcript does not have a pointer "up".
    """
    plan_session_template = run_transcript.plan.session_template
    for test_transcript in session_transcript.run_tests:
        plan_testspec = plan_session_template.tests[test_transcript.plan_test_index]
        if plan_testspec.name == test_meta.name:
            yield test_transcript.worst_result
    return None


def _derive_full_and_local_filename(base: str, suffix: str) -> tuple[str,str]:
    """
    Given a base filename, derive another filename (e.g. generate a .css filename from an .html filename).
    Return the full filename with path, and the local filename
    """
    dir = os.path.dirname(base)
    local = os.path.basename(base)
    last_dot = local.rfind('.')
    if last_dot > 0:
        derived = f'{ local[0:last_dot] }{ suffix }'
    else:
        derived = f'{ local }.{ suffix }'
    return (os.path.join(dir, derived), derived)


class HtmlRunTranscriptSerializer(TestRunTranscriptSerializer):
    """
    Generates the Feditest reports as HTML.
    If the transcript contains one session, it will generate one HTML file to the provided destination.

    If the transcript contains multiple sessions, it will generate one HTML file per session and
    an overview test matrix. The test matrix will be at the provided destination, and the session
    files will have longer file names starting with the filename of the destination.

    A CSS file will be written to the provided destination with an extra extension.
    """

    def __init__(self, template_path: str):
        if template_path:
            self.template_path = [ t.strip() for t in template_path.split(",") ]
        else:
            self.template_path = [ os.path.join(os.path.dirname(__file__), "templates/testplantranscript_default") ]

        self.jinja2_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_path)
        )
        self.jinja2_env.filters["regex_sub"] = lambda s, pattern, replacement: re.sub(
            pattern, replacement, s
        )


    # Python 3.12 @override
    def write(self, transcript: TestRunTranscript, dest: str | None):
        if dest is None:
            fatal('Cannot write --html to stdout.')
            return # make linter happy
        if len(transcript.sessions) == 0:
            fatal('No session in transcript: cannot transcribe')

        ( cssfile, local_cssfile ) = _derive_full_and_local_filename(dest, '.css')
        base_context = dict(
            feditest=feditest,
            cssfile = local_cssfile,
            getattr=getattr,
            sorted=sorted,
            enumerate=enumerate,
            get_results_for=_get_results_for,
            remove_white=lambda s: re.sub("[ \t\n\a]", "_", str(s)),
            permit_line_breaks_in_identifier=lambda s: re.sub(
                r"(\.|::)", r"<wbr>\1", s
            ),
            local_name_with_tooltip=lambda n: f'<span title="{ n }">{ n.split(".")[-1] }</span>',
            format_timestamp=lambda ts: ts.strftime("%Y:%m:%d-%H:%M:%S.%fZ") if ts else "",
            format_duration=lambda s: str(s), # makes it easier to change in the future
            len=len,
            html_escape=lambda s: html.escape(str(s))
        )

        try:
            if len(transcript.sessions) == 1:
                self.write_single_session(transcript, base_context, dest)
            else:
                self.write_matrix_and_sessions(transcript, base_context, dest)

        except jinja2.exceptions.TemplateNotFound as ex:
            msg = f"ERROR: template '{ex}' not found.\n"
            msg += "Searched in the following directories:"
            for entry in self.template_path:
                msg += f"\n  {entry}"
            fatal(msg)

        # One this worked, we can add the CSS file
        for path in self.template_path:
            css_candidate = os.path.join(path, 'static', 'feditest.css')
            if os.path.exists(css_candidate):
                shutil.copyfile(css_candidate, cssfile)
                break


    def write_single_session(self, transcript: TestRunTranscript, context: dict[str, Any], dest: str):
        run_session = transcript.sessions[0]
        context.update(
            transcript=transcript,
            run_session=run_session,
            summary=run_session.build_summary() # if we use 'summary', we can use shared/summary.jinja2
        )
        with open(dest, "w") as fp:
            session_template = self.jinja2_env.get_template("session_single.jinja2")
            fp.write(session_template.render(**context))


    def write_matrix_and_sessions(self, transcript: TestRunTranscript, context: dict[str, Any], dest: str):
        matrix_context = dict(context)
        matrix_context.update(
            transcript=transcript,
            session_file_path=lambda session: _derive_full_and_local_filename(dest, f'.{ session.run_session_index }.html')[1],
            summary=transcript.build_summary() # if we use 'summary', we can use shared/summary.jinja2
        )
        with open(dest, "w") as fp:
            matrix_template = self.jinja2_env.get_template("matrix.jinja2")
            fp.write(matrix_template.render(**matrix_context))

        for run_session in transcript.sessions:
            session_context = dict(context)
            session_context.update(
                transcript=transcript,
                run_session=run_session,
                summary=run_session.build_summary(), # if we use 'summary', we can use shared/summary.jinja2
                matrix_file_path=os.path.basename(dest)
            )
            session_dest = _derive_full_and_local_filename(dest, f'.{ run_session.run_session_index }.html')[0]
            with open(session_dest, "w") as fp:
                session_template = self.jinja2_env.get_template("session_with_matrix.jinja2")
                fp.write(session_template.render(**session_context))
