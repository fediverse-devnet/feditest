from typing import IO

from feditest.testruntranscript import TestRunTranscript
from feditest.testruntranscriptserializer import FileOrStdoutTestRunTranscriptSerializer


class SummaryTestRunTranscriptSerializer(FileOrStdoutTestRunTranscriptSerializer):
    """
    Knows how to serialize a TestRunTranscript into a single-line summary.
    """
    def _write(self, transcript: TestRunTranscript, fd: IO[str]):
        summary = transcript.build_summary()

        print(f'Test summary: total={ summary.n_total }'
              + f', passed={ summary.n_passed }'
              + f', failed={ summary.n_failed }'
              + f', skipped={ summary.n_skipped }'
              + f', errors={ summary.n_errored }.',
              file=fd)


