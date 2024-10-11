from feditest.protocols.activitypub.diag import ActivityPubDiagNode
from feditest.protocols.fediverse import FediverseNode
from feditest.protocols.webfinger.diag import WebFingerDiagClient, WebFingerDiagServer


class FediverseDiagNode(WebFingerDiagClient, WebFingerDiagServer,ActivityPubDiagNode,FediverseNode):
    """
    FIXME
    """
