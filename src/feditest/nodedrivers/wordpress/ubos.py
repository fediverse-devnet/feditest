"""
"""

from typing import Any, cast

from feditest.nodedrivers.mastodon import NoUserRecord, UserRecord
from feditest.nodedrivers.wordpress import WordPressPlusActivityPubPluginNode
from feditest.testplan import TestPlanConstellationNode
from feditest.ubos import UbosNodeDriver


class WordPressPlusActivityPubPluginUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate WordPress with the ActivityPub plugin via UBOS.
    """
    # Python 3.12 @override
    def _fill_in_parameters(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, test_plan_node, parameters)
        parameters['app'] = 'WordPress + ActivityPub plugin'
        parameters['backupfile'] = 'ubos-sites/wordpress.123.lan.ubos-backup'
        parameters['backup-appconfigid'] = 'a192b3184d2a08e1e3620804cfacd0af151425374' # determine with `ubos-admin backupinfo --ids --in wordpress.123.lan.ubos-backup`


    # Python 3.12 @override
    def _instantiate_ubos_node(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str, Any]) -> WordPressPlusActivityPubPluginNode:
        existing_users_by_role: dict[str | None, UserRecord] = {
            None : UserRecord(
                userid=cast(str, parameters.get('adminid')),
                email=cast(str, parameters.get('adminemail')),
                passwd=cast(str, parameters.get('adminpass')),
                oauth_token=None,
                role=None)
        }
        non_existing_users_by_role: dict[str | None, NoUserRecord] = {
            None: NoUserRecord(
                userid=cast(str, parameters.get('doesnotexistid')),
                role=None)
        }

        return WordPressPlusActivityPubPluginNode(
            rolename,
            parameters,
            self,
            existing_users_by_role,
            non_existing_users_by_role)
