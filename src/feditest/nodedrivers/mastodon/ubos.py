"""
"""

import re
import secrets
import string
from typing import Any, cast

from feditest.nodedrivers.mastodon import MastodonNode, NoUserRecord, UserRecord
from feditest.reporting import error, trace
from feditest.testplan import TestPlanConstellationNode
from feditest.ubos import UbosNodeConfiguration, UbosNodeDriver


class MastodonUbosNode(MastodonNode):
    """
    A Mastodon Node running on UBOS. This means we know how to interact with it exactly.
    """
    # Python 3.12 @override
    @property
    def start_delay(self):
        return 10000


    # Python 3.12 @override
    def _provision_new_user(self, rolename: str) -> UserRecord:
        trace('Provisioning new user')
        chars = string.ascii_letters + string.digits
        userid = ''.join(secrets.choice(chars) for i in range(8))
        useremail = f'{ userid }@localhost' # Mastodon checks that the host exists, so we pick localhost

        appconfigid = self.parameter('appconfigid')
        cmd = f'cd /ubos/lib/mastodon/{ appconfigid }/mastodon'
        cmd += ' && sudo RAILS_ENV=production bin/tootctl' # This needs to be run as root, because .env.production is not world-readable
        cmd += f' accounts create { userid } --email { useremail }'

        node_driver = cast(MastodonUbosNodeDriver, self._node_driver)
        result = node_driver._exec_shell(cmd, self.parameter('rshcmd' ), capture_output=True)
        if result.returncode:
            error(f'Provisioniong new user { userid } on Mastodon Node { self._rolename } failed.')

        m = re.search( r'password:\s+([a-z0-9]+)', result.stdout )
        if m:
            passwd = m.group(1)
            return UserRecord(userid=userid, email=useremail, passwd=passwd, oauth_token=None, role=rolename)

        raise Exception('Failed to parse tootctl accounts create output:' + result.stdout)


    # Python 3.12 @override
    def add_cert_to_trust_store(self, root_cert: str) -> None:
        # We ask our UbosNodeDriver, so we don't have to have a UbosNode class
        config = cast(UbosNodeConfiguration, self._config)
        real_node_driver = cast(MastodonUbosNodeDriver, config.node_driver)
        real_node_driver.add_cert_to_trust_store(root_cert, config.rshcmd)


    # Python 3.12 @override
    def remove_cert_from_trust_store(self, root_cert: str) -> None:
        config = cast(UbosNodeConfiguration, self._config)
        real_node_driver = cast(MastodonUbosNodeDriver, config.node_driver)
        real_node_driver.remove_cert_from_trust_store(root_cert, config.rshcmd)


class MastodonUbosNodeDriver(UbosNodeDriver):
    """
    Knows how to instantiate Mastodon via UBOS.
    """
    # Python 3.12 @override
    def check_plan_node(self,rolename: str, test_plan_node: TestPlanConstellationNode) -> None:
        super().check_plan_node(rolename, test_plan_node)
        MastodonNode.check_plan_node(test_plan_node, 'MastodonUbosNodeDriver:')


    # Python 3.12 @override
    def _fill_in_parameters(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]):
        super()._fill_in_parameters(rolename, test_plan_node, parameters)
        parameters['app'] = 'Mastodon'
        parameters['start-delay'] = 10


    # Python 3.12 @override
    def _instantiate_ubos_node(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str, Any]) -> MastodonNode:
        trace('Instantiating MastodonUbosNode')

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

        return MastodonUbosNode(
            rolename,
            parameters,
            self,
            existing_users_by_role,
            non_existing_users_by_role)


    # Python 3.12 @override
    def _getAppConfigsJson(self, parameters: dict[str,Any]) -> list[dict[str,Any]]:
        return [{
            "appid" : "mastodon",
            "appconfigid" : parameters['appconfigid'],
            "context" : "",
            "customizationpoints" : {
                "mastodon" : {
                    "singleusermode" : {
                        "value" : False
                    }
                }
            }
        }]
