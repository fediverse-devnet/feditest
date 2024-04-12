"""
Nodes managed via UBOS https://ubos.net/
"""

import subprocess
import shutil
from typing import Any

from feditest.protocols import Node, NodeDriver
from feditest.reporting import info
from feditest.utils import hostname_validate


class UbosNodeDriver(NodeDriver):
    """
    A general-purpose NodeDriver for Nodes provisioned through UBOS Gears.
    """
    def _provision_node(self, rolename: str, parameters: dict[str,Any] | None) -> Node:
        """
        The UBOS driver knows how to provision a node either by deploying a UBOS Site JSON file
        with "ubos-admin deploy" or to restore a known state of a Site with "ubos-admin restore".
        """
        if not shutil.which('ubos-admin'):
            raise Exception(f'UbosNodeDriver ({ type(self)}) can only be used on UBOS.')
        
        # FIXME: reconcile provided hostname with what's in the site json / backup
        cmd = None
        if not parameters:
            raise Exception('UbosNodeDriver needs parameters')
        if 'siteid' not in parameters:
            raise Exception('UbosNodeDriver needs parameter siteid for now') # FIXME: should get it from the JSON file
        if 'adminid' not in parameters:
            raise Exception('UbosNodeDriver needs parameter adminid for now') # FIXME: should get it from the JSON file
        if 'hostname' not in parameters:
            raise Exception('UbosNodeDriver needs parameter hostname for now') # FIXME: should get it from the JSON file
        if not hostname_validate(parameters['hostname']):
            raise Exception(f'Invalid hostname: "{ parameters["hostname"] }"')
        if 'sitejsonfile' in parameters:
            cmd = f"sudo ubos-admin deploy --file {parameters['sitejsonfile']}"
        elif 'backupfile' in parameters:
            cmd = f"sudo ubos-admin restore --in {parameters['backupfile']}"
        else:
            raise Exception('UbosNodeDriver needs parameter sitejsonfile or backupfile')

        parameters = dict(parameters)
        parameters['existing-account-uri'] = f"acct:{ parameters['adminid'] }@{ parameters['hostname'] }"
        parameters['nonexisting-account-uri'] = f"acct:does-not-exist@{ parameters['hostname'] }"

        self._exec_shell(cmd)
        ret = self._instantiate_node(parameters['siteid'], rolename, parameters)
        return ret


    def _instantiate_node(self, site_id: str, rolename: str, parameters: dict[str,Any] | None) -> Node:
        """
        This needs to be subclassed to control/observe the running UBOS Node programmatically.
        """
        raise Exception('_instantiate_node must be overridden')


    def _exec_shell(self, cmd: str):
        info( f"Executing '{cmd}'")
        ret = subprocess.run(cmd, shell=True, check=False)

        return ret.returncode
