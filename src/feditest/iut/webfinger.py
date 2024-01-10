"""
"""

from httpx import Response
from typing import Any

from feditest.iut import NotImplementedByIUTError
from feditest.iut.web import WebClientIUT, WebClientIUTDriver, WebServerIUT, WebServerIUTDriver

class WebFingerServerIUT(WebServerIUT):
    """
    An IUT that acts as a WebFinger server.
    """
    def __init__(self, nickname: str, iut_driver: 'WebFingerServerIUTDriver') -> None:
        super().__init__(nickname, iut_driver)

    def obtain_account_identifier(self) -> str:
        """
        Return the identifier of an existing or newly created account on this
        IUT that the IUT is supposed to be able to perform webfinger discovery on.
        The identifier is of the form ``foo@bar.com``.
        return: the identifier
        """
        return self._iut_driver.prompt_user(
            'Please enter the identifier of an existing or new account at this WebFingerIUT (e.g. "testuser@example.local" )',
            account_id_validate )

    def obtain_non_existing_account_identifier(self) ->str:
        """
        Return the identifier of an account that does not exist on this IUT, but that
        nevertheless follows the rules for identifiers of this IUT.
        The identifier is of the form ``foo@bar.com``.
        return: the identifier
        """
        return self._iut_driver.prompt_user(
            'Please enter the identifier of an non-existing account at this WebfFngerIUT (e.g. "does-not-exist@example.local" )',
            account_id_validate )


class WebFingerServerIUTDriver(WebServerIUTDriver):
    def __init__(self, name: str) -> None:
        super.__init__(name)

    # Python 3.12 @override
    def _provision_IUT(self, nickname: str) -> WebFingerServerIUT:
        return WebFingerServerIUT(nickname, self);


class WebFingerUnknownResourceException(RuntimeError):
    """
    Raised when a WebFinger query results in a 404 because the resource cannot be
    found by the server.
    resource_uri: URI of the resource
    http_response: the underlying Response object
    """
    def __init__(self, resource_uri: str, http_response: Response):
        self.resource_uri = resource_uri
        self.http_response = http_response


class WebFingerClientIUT(WebClientIUT):
    """
    An IUT that acts as a WebFinger client.
    """
    def __init__(self, nickname: str, iut_driver: 'WebFingerClientIUTDriver') -> None:
        super().__init__(nickname, iut_driver)


    def perform_webfinger_query_on_resource(self, resource_uri: str) -> dict[str,Any]:
        """
        Make the client perform a WebFinger query for the provided resource_uri.
        The resource_uri must be a valid, absolute URI, such as 'acct:foo@bar.com` or
        'https://example.com/aabc' (not escaped).
        Return a dict that is the parsed form of the JRD or throws an exception
        """
        raise NotImplementedByIUTError(WebFingerClientIUT.perform_webfinger_query_on_resource)


class WebFingerClientIUTDriver(WebClientIUTDriver):
    def __init__(self, name: str) -> None:
        super.__init__(name)

    # Python 3.12 @override
    def _provision_IUT(self, nickname: str) -> WebFingerClientIUT:
        return WebFingerClientIUT(nickname, self);
