from abc import ABC, abstractmethod
import io
import sys
from typing import IO

from feditest.testruntranscript import TestRunTranscript


class TestRunTranscriptSerializer(ABC):
    """
    An object that knows how to serialize a TestRunTranscript into some output format.
    """
    @abstractmethod
    def write(self, transcript: TestRunTranscript, dest: str | None):
        ...


class FileOrStdoutTestRunTranscriptSerializer(TestRunTranscriptSerializer):
    def write(self, transcript: TestRunTranscript, dest: str | None) -> None:
        """
        dest: name of the file to write to, or stdout
        """
        if dest and isinstance(dest,str):
            with open(dest, "w", encoding="utf8") as out:
                self._write(transcript, out)
        else:
            self._write(transcript, sys.stdout)


    def write_to_string(self, transcript: TestRunTranscript) -> str:
        """
        Return the written content as a string; this is for testing.
        """
        string_io = io.StringIO()
        self._write(transcript, string_io)
        return string_io.getvalue()


    @abstractmethod
    def _write(self, transcript: TestRunTranscript, fd: IO[str]) -> None:
        ...


