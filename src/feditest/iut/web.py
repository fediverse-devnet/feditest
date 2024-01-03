"""
"""

from feditest.iut import IUT, IUTDriver
from feditest.utils import http_https_root_uri_validate

class WebIUT(IUT):
    def __init__(self, nickname: str, iut_driver: 'WebIUTDriver') -> None:
        super().__init__(nickname, iut_driver)

    def getRootURI(self) -> str:
        """
        Return the fully-qualified top-level URI at which this WebIUT serves HTTP or HTTPS.
        The identifier is of the form ``http[s]://example.com/``. It does contain scheme
        and resolvable hostname, but does not contain path, fragment, or query elements.
        return: the URI
        """
        return self._iut_driver.prompt_user(
            'Please enter the WebIUT\' root URI (e.g. "https://example.local/" )',
            http_https_root_uri_validate )


class WebIUTDriver(IUTDriver):
    def __init__(self, name: str) -> None:
        super.__init__(name)

    # Python 3.12 @override
    def _provision_IUT(self, nickname: str) -> WebIUT:
        return WebIUT(nickname, self);
