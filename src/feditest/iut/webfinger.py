"""
"""

from feditest.iut import IUT, IUTDriver
from feditest.iut.web import WebIUT, WebIUTDriver

class WebfingerServerIUT(WebIUT):
    """
    An IUT that acts as a Webfinger server.
    """
    def __init__(self, nickname: str, iut_driver: 'WebfingerServerIUTDriver') -> None:
        super().__init__(nickname, iut_driver)

    def obtainAccountIdentifier(self) -> str:
        """
        Return the identifier of an existing or newly created account on this
        IUT that the IUT is supposed to be able to perform webfinger discovery on.
        The identifier is of the form ``foo@bar.com``.
        return: the identifier
        """
        return self._iut_driver.prompt_user(
            'Please enter the identifier of an existing or new account at this WebfingerIUT (e.g. "testuser@example.local" )',
            account_id_validate )

    def obtainNonExistingAccountIdentifier(self) ->str:
        """
        Return the identifier of an account that does not exist on this IUT, but that
        nevertheless follows the rules for identifiers of this IUT.
        The identifier is of the form ``foo@bar.com``.
        return: the identifier
        """
        return self._iut_driver.prompt_user(
            'Please enter the identifier of an non-existing account at this WebfingerIUT (e.g. "does-not-exist@example.local" )',
            account_id_validate )


class WebfingerServerIUTDriver(WebIUTDriver):
    def __init__(self, name: str) -> None:
        super.__init__(name)

    # Python 3.12 @override
    def _provision_IUT(self, nickname: str) -> WebfingerServerIUT:
        return WebfingerServerIUT(nickname, self);


class WebfingerClientIUT(IUT):
    """
    An IUT that acts as a Webfinger client.
    """
    def __init__(self, nickname: str, iut_driver: 'WebfingerClientIUTDriver') -> None:
        super().__init__(nickname, iut_driver)


class WebfingerClientIUTDriver(IUTDriver):
    def __init__(self, name: str) -> None:
        super.__init__(name)

    # Python 3.12 @override
    def _provision_IUT(self, nickname: str) -> WebfingerClientIUT:
        return WebfingerClientIUT(nickname, self);
