"""
UBOS facilities
"""

import json
import subprocess
from typing import Any

from feditest.protocols import Node, NodeDriver
from feditest.reporting import info

class UbosNode(Node):
    def __init__(self, site_id: str, rolename: str, hostname: str, admin_id: str, node_driver: 'UbosDriver') -> None:
        """
        site_id: the UBOS SiteId
        rolename: name of the role in the constellation
        node_driver: the NodeDriver that provisioned this Node
        """
        super().__init__(rolename, node_driver)
    
        self.site_id = site_id
        self.hostname = hostname
        self.admin_id = admin_id
        
    def obtain_account_identifier(self, nickname: str = None) -> str:
        return f"acct:{self.admin_id}@{self.hostname}"


    def obtain_non_existing_account_identifier(self, nickname: str = None ) ->str:
        return f"acct:undefined@{self.hostname}"


class UbosDriver(NodeDriver):
    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None) -> Node:
        """
        The factory method for Node. Any subclass of NodeDriver should also
        override this and return a more specific subclass of IUT.
        """
        cmd = None
        if not parameters:
            raise Exception('UbosDriver needs parameters')
        if not 'siteid' in parameters:
            raise Exception('UbosDriver needs parameter siteid for now')
        if not 'adminid' in parameters:
            raise Exception('UbosDriver needs parameter adminid for now')
        if 'sitejsonfile' in parameters:
            cmd = f"sudo ubos-admin deploy --file {parameters['sitejsonfile']}"
        elif 'backupfile' in parameters:
            cmd = f"sudo ubos-admin restore --in {parameters['backupfile']}"
        else:
            raise Exception('UbosDriver needs parameter sitejsonfile or backupfile')
        
        self._execShell(cmd)
        ret = self._instantiate_node(parameters['siteid'], rolename, hostname, parameters['adminid'])
        return ret

    def _unprovision_node(self, node: Node) -> None:
        """
        Invoked when a Node gets unprovisioned, in case cleanup needs to be performed.
        This is here so subclasses of NodeDriver can override it.
        """
        self._execShell(f"sudo ubos-admin undeploy --siteid {node.site_id}")

    def _instantiate_node(self, site_id: str, rolename: str, hostname: str, admin_id: str) -> None:
        return UbosNode(site_id, rolename, hostname, admin_id, self) # FIXME: needs to be subclassed
    
    def _execShell(self, cmd: str):
        info( f"Executing '{cmd}'")
        ret = subprocess.run(cmd, shell=True)

        return ret.returncode
