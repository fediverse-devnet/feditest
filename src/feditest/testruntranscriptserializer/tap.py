from typing import IO

from feditest.testruntranscript import TestRunTranscript
from feditest.testruntranscriptserializer import FileOrStdoutTestRunTranscriptSerializer


class TapTestRunTranscriptSerializer(FileOrStdoutTestRunTranscriptSerializer):
    """
    Knows how to serialize a TestRunTranscript into a report in TAP format.
    """
    def _write(self, transcript: TestRunTranscript, fd: IO[str]):
        plan = transcript.plan
        summary = transcript.build_summary()

        fd.write("TAP version 14\n")
        fd.write(f"# test plan: { plan }\n")
        for key in ['started', 'ended', 'platform', 'username', 'hostname']:
            value = getattr(transcript, key)
            if value:
                fd.write(f"# {key}: {value}\n")

        test_id = 0
        for session_transcript in transcript.sessions:
            plan_session_template = plan.session_template
            constellation = session_transcript.constellation

            fd.write(f"# session: { session_transcript }\n")
            fd.write(f"# constellation: { constellation }\n")
            fd.write("#   roles:\n")
            for role_name, node in constellation.nodes.items():
                if role_name in session_transcript.constellation.nodes:
                    transcript_role = session_transcript.constellation.nodes[role_name]
                    fd.write(f"#     - name: {role_name}\n")
                    if node:
                        fd.write(f"#       driver: {node.node_driver}\n")
                    fd.write(f"#       app: {transcript_role.appdata['app']}\n")
                    fd.write(f"#       app_version: {transcript_role.appdata['app_version'] or '?'}\n")
                else:
                    fd.write(f"#     - name: {role_name} -- not instantiated\n")

            for test_index, run_test in enumerate(session_transcript.run_tests):
                test_id += 1

                plan_test_spec = plan_session_template.tests[run_test.plan_test_index]
                test_meta = transcript.test_meta[plan_test_spec.name]

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
