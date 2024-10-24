from typing import IO

from feditest.testruntranscript import TestRunTranscript
from feditest.testruntranscriptserializer import FileOrStdoutTestRunTranscriptSerializer


class JsonTestRunTranscriptSerializer(FileOrStdoutTestRunTranscriptSerializer):
    """
    An object that knows how to serialize a TestRun into JSON format
    """
    def _write(self, transcript: TestRunTranscript, fd: IO[str]):
        transcript.write(fd)
