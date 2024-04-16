"""
Nodes managed via UBOS https://ubos.net/
"""

import subprocess
import shutil
from typing import Any

from feditest.protocols import Node, NodeDriver, NodeSpecificationInsufficientError, NodeSpecificationInvalidError
from feditest.reporting import info

class UbosNodeDriver(NodeDriver):
    """
    A general-purpose NodeDriver for Nodes provisioned through UBOS Gears.
    """
    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None) -> Node:
        """
        The UBOS driver knows how to provision a node either by deploying a UBOS Site JSON file
        with "ubos-admin deploy" or to restore a known state of a Site with "ubos-admin restore".
        """
        if not shutil.which('ubos-admin'):
            raise NodeSpecificationInvalidError(self, type(self), 'can only be used on UBOS.')

        # FIXME: reconcile provided hostname with what's in the site json / backup

        cmd = None
        if not parameters:
            raise NodeSpecificationInsufficientError(self, 'No parameters given')
        if 'siteid' not in parameters:
            raise NodeSpecificationInsufficientError(self, 'Need parameter siteid for now') # FIXME: should get it from the JSON file
        if 'adminid' not in parameters:
<<<<<<< Updated upstream
            raise Exception('UbosNodeDriver needs parameter adminid for now') # FIXME: should get it from the JSON file
=======
            raise NodeSpecificationInsufficientError(self, 'Need parameter adminid for now') # FIXME: should get it from the JSON file
        if 'hostname' not in parameters:
            raise NodeSpecificationInsufficientError(self, 'Needs parameter hostname for now') # FIXME: should get it from the JSON file
        if not hostname_validate(parameters['hostname']):
            raise NodeSpecificationInvalidError(self, 'hostname', parameters['hostname'])
>>>>>>> Stashed changes
        if 'sitejsonfile' in parameters:
            cmd = f"sudo ubos-admin deploy --file {parameters['sitejsonfile']}"
        elif 'backupfile' in parameters:
            cmd = f"sudo ubos-admin restore --in {parameters['backupfile']}"
        else:
            raise NodeSpecificationInsufficientError(self, 'Need parameter sitejsonfile or backupfile')

        self._exec_shell(cmd)
<<<<<<< Updated upstream
        ret = self._instantiate_node(parameters['siteid'], rolename, hostname, parameters['adminid'])
        return ret


    def _instantiate_node(self, site_id: str, rolename: str, hostname: str, admin_id: str) -> None:
=======
        ret = self._instantiate_node(rolename, parameters)
        return ret


    def _instantiate_node(self, rolename: str, parameters: dict[str,Any] | None) -> Node:
>>>>>>> Stashed changes
        """
        This needs to be subclassed to control/observe the running UBOS Node programmatically.
        """
        raise Exception('_instantiate_node must be overridden') # pylint: disable=broad-exception-raised


    def _exec_shell(self, cmd: str):
        info( f"Executing '{cmd}'")
        ret = subprocess.run(cmd, shell=True, check=False)

        return ret.returncode
