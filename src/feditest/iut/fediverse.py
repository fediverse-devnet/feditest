"""
"""

from feditest.iut.activitypub import ActivityPubIUT, ActivityPubIUTDriver
from feditest.iut.webfinger import WebfingerIUT, WebfingerIUTDriver

class FediverseIUT(WebfingerIUT,ActivityPubIUT):
    ...

