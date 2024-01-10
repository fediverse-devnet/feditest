"""
"""

from feditest.iut.web import WebIUT, WebIUTDriver


class ActivityPubFederationIUT(WebIUT):
    def __init__(self, nickname: str, iut_driver: 'ActivityPubIUTDriver') -> None:
        super().__init__(nickname, iut_driver)

    def obtain_actor_document_URI(self) -> str:
        """
        Return the URI that leads to an Actor document that either exists already or is
        newly created.
        return: the URI
        """
        return self._iut_driver.prompt_user(
            'Please enter an URI at this ActivityPubIUT that serves an ActivityPub Actor document:',
            http_https_uri_validate )

    def create_actor_document_URI(self) -> str:
        """
        Return the URI that leads to an Actor document that is newly created as part of
        this invocation. This method acts as a factory.
        return: the URI
        """
        return self._iut_driver.prompt_user(
            'Please create a new Actor at this ActivityPubIUT and enter the URI at which'
            + 'its ActivityPub Actor document is served:',
            http_https_uri_validate )

    def make_a_follow_b(self, a: str, b: str) -> None:
        ...

class ActivityPubFederationIUTDriver(WebIUTDriver):
    def __init__(self, name: str) -> None:
        super.__init__(name)

    # Python 3.12 @override
    def _provision_IUT(self, nickname: str) -> ActivityPubIUT:
        return ActivityPubIUT(nickname, self);
