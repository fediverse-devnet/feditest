"""
Define interfaces to interact with instances-under-test (IUTs)
"""

from abc import ABC
from collections.abc import Callable
from typing import Any

class IUT:
    def __init__(self, nickname: str, iut_driver: 'IUTDriver') -> None:
        self._nickname   = nickname
        self._iut_driver = iut_driver

    def getNickname(self) -> str :
        return self._nickname


class IUTDriver(ABC):
    def __init__(self, name: str) -> None:
        self._name = name

    def provision_IUT(self, nickname: str) -> IUT:
        """
        Instantiate an Instance-Under-Test.
        nickname: the nickname of this instance
        """
        if nickname in self._known_IUTs:
            raise Exception(f"Nickname { nickname } provisioned already")
        ret = self._provision_IUT(nickname)
        self._known_IUTs[nickname] = ret
        return ret;

    def unprovisionIUT(self, instance: IUT) -> None:
        """
        Deactivate an Instance-Under-Test.
        iut: the Instance-Under-Test
        """
        if not nickname in self._known_IUTs :
            raise Exception(f"Nickname { nickname } not known")
        if self._known_IUTs[nickname] != instance :
            raise Exception(f"Instance does not belong to this driver")
        self._unprovision_IUT(instance)
        del self._known_IUTs[nickname]

    def _provision_IUT(self, nickname: str) -> IUT:
        """
        The factory method for IUTs. Any subclass of IUTDriver should also
        override this and return a more specific subclass of IUT.
        """
        return IUT(nickname, self);

    def _unprovision_IUT(self, instance: IUT) -> None:
        """
        Invoked when an IUT gets unprovisioned, in case cleanup needs to be performed.
        This is here so subclasses of IUTDriver can override it.
        """
        pass

    def prompt_user(self, question: str, validation: Callable[[str],[bool]]=None) -> str:
        """
        If an IUTDriver does not natively implement support for a particular method,
        this method is invoked as a fallback. It prompts the user to enter information
        at the console.
        question: the text to be emitted to the user as a prompt
        validation: optional function that validates user input and returns True if valid
        return: the value entered by the user
        """

class NotImplementedByIUTError(RuntimeError):
    """
    This exception is raised when an IUT cannot perform a certain operation because it
    has not been implemented in this subtype of IUT.
    """
    def __init__(self, method: Callable[...,Any] ):
        super.__init__("Not implemented: " + str(method))
