"""
Nodes managed via UBOS https://ubos.net/
"""

import json
import subprocess
from typing import Any

from feditest.protocols import Node, NodeDriver
from feditest.reporting import info


class UbosNodeDriver(NodeDriver):
    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None) -> Node:
        """
        The UBOS driver knows how to provision a node either by deploying a UBOS Site JSON file
        with "ubos-admin deploy" or to restore a known state of a Site with "ubos-admin restore".
        """
        cmd = None
        if not parameters:
            raise Exception('UbosNodeDriver needs parameters')
        if 'siteid' not in parameters:
            raise Exception('UbosNodeDriver needs parameter siteid for now') # FIXME: should get it from the JSON file
        if 'adminid' not in parameters:
            raise Exception('UbosNodeDriver needs parameter adminid for now') # FIXME: should get it from the JSON file
        if 'sitejsonfile' in parameters:
            cmd = f"sudo ubos-admin deploy --file {parameters['sitejsonfile']}"
        elif 'backupfile' in parameters:
            cmd = f"sudo ubos-admin restore --in {parameters['backupfile']}"
        else:
            raise Exception('UbosNodeDriver needs parameter sitejsonfile or backupfile')

        self._execShell(cmd)
        ret = self._instantiate_node(parameters['siteid'], rolename, hostname, parameters['adminid'])
        return ret


    def _unprovision_node(self, node: Node) -> None:
        self._execShell(f"sudo ubos-admin undeploy --siteid {node._site_id}")


    def _instantiate_node(self, site_id: str, rolename: str, hostname: str, admin_id: str) -> None:
        """
        This needs to be subclassed to control/observe the running UBOS Node programmatically.
        """
        raise Exception('_instantiate_node must be overridden')


    def _execShell(self, cmd: str):
        info( f"Executing '{cmd}'")
        ret = subprocess.run(cmd, shell=True)

        return ret.returncode
