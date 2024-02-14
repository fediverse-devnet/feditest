"""
UBOS facilities
"""

import json
import subprocess
from typing import Any

from feditest.protocols import Node, NodeDriver
from feditest.reporting import info

class UbosNode(Node):
    def __init__(self, site_id: str, rolename: str, node_driver: 'UbosDriver') -> None:
        """
        site_id: the UBOS SiteId
        rolename: name of the role in the constellation
        node_driver: the NodeDriver that provisioned this Node
        """
        super().__init__(rolename, node_driver)
    
        self.site_id = site_id

class UbosDriver(NodeDriver):
    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None) -> Node:
        """
        The factory method for Node. Any subclass of NodeDriver should also
        override this and return a more specific subclass of IUT.
        """
        if not parameters or not 'sitejsonfile' in parameters:
            raise Exception('UbosDriver needs parameter sitejsonfile')
        if not parameters or not 'siteid' in parameters:
            raise Exception('UbosDriver needs parameter siteid for now')
        
        self._execShell(f"sudo ubos-admin deploy --file {parameters['sitejsonfile']}")
        ret = self._instantiate_node(parameters['siteid'], rolename)
        return ret

    def _unprovision_node(self, node: Node) -> None:
        """
        Invoked when a Node gets unprovisioned, in case cleanup needs to be performed.
        This is here so subclasses of NodeDriver can override it.
        """
        self._execShell(f"sudo ubos-admin undeploy --siteid {node.site_id}")

    def _instantiate_node(self, site_id: str, rolename: str) -> None:
        return UbosNode(site_id, rolename, self) # FIXME: needs to be subclassed
    
    def _execShell(self, cmd: str):
        info( f"Executing '{cmd}'")
        ret = subprocess.run(cmd, shell=True)

        return ret.returncode
