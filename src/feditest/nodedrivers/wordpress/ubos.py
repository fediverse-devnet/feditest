"""
"""

from typing import Any

from feditest.nodedrivers.wordpress import WordPressPlusActivityPubPluginNode
from feditest.ubos import UbosNodeDriver


class WordPressPlusActivityPubPluginUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate WordPress with the ActivityPub plugin via UBOS.
    """
    def _instantiate_ubos_node(self, rolename: str, parameters: dict[str, Any]) -> WordPressPlusActivityPubPluginNode:
        parameters['app'] = 'WordPress + ActivityPub plugin'
        parameters['backupfile'] = 'ubos-sites/wordpress.123.lan.ubos-backup'
        parameters['backup-appconfigid'] = 'a192b3184d2a08e1e3620804cfacd0af151425374' # determine with `ubos-admin backupinfo --ids --in wordpress.123.lan.ubos-backup`

        return WordPressPlusActivityPubPluginNode(rolename, parameters, self)
