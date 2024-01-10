"""
"""

from feditest.iut.activitypub import ActivityPubIUT, ActivityPubIUTDriver
from feditest.iut.webfinger import WebFingerClientIUT, WebFingerServerIUT, WebFingerClientIUTDriver, WebFingerServerIUTDriver


class FediverseNodeIUT(WebFingerClientIUT, WebFingerServerIUT, ActivityPubIUT):
    ...

class FediverseNodeIUTDriver(WebFingerClientIUTDriver,WebFingerServerIUTDriver, ActivityPubIUTDriver):
    ...
