"""
Nodes managed via UBOS https://ubos.net/
"""

import subprocess
import shutil
from typing import Any

from feditest.protocols import Node, NodeDriver, NodeSpecificationInsufficientError, NodeSpecificationInvalidError
from feditest.reporting import info
from feditest.utils import hostname_validate, ssh_uri_validate

"""
There is no UbosNode: it only needs to carry sshuri and identity_file (both optional) and having an entire
separate class that needs to be woven into the rest of the class hierarchy as a mixin or as a second
supertype does not appear to be worth it.

Instead we keep those two values in the parameters dict, where they come from anyway.
"""


class UbosNodeDriver(NodeDriver):
    """
    A general-purpose NodeDriver for Nodes provisioned through UBOS Gears.
    """
    def _provision_node(self, rolename: str, parameters: dict[str,Any]) -> Node:
        """
        The UBOS driver knows how to provision a node either by deploying a UBOS Site JSON file
        with "ubos-admin deploy" or to restore a known state of a Site with "ubos-admin restore".
        It performs these operations locally, or if ssh information is provided, remotely over ssh.
        """
        if not parameters:
            raise NodeSpecificationInsufficientError(self, 'No parameters given')

        sshuri = parameters.get('sshuri')
        identity_file = parameters.get('identity_file')
        if sshuri:
            ssh_uri_validate(sshuri) # will raise
            if self._exec_shell('which ubos-admin', sshuri, identity_file):
                raise OSError(f'{ type(self).__name__ } with an sshuri requires UBOS Gears on the remote system (see ubos.net).')
        else:
            if not shutil.which('ubos-admin'):
                raise OSError(f'{ type(self).__name__ } without an sshuri requires a local system running UBOS Gears (see ubos.net).')

        # FIXME: reconcile provided hostname with what's in the site json / backup

        cmd = None
        if 'siteid' not in parameters:
            raise NodeSpecificationInsufficientError(self, 'Need parameter siteid for now') # FIXME: should get it from the JSON file
        if 'adminid' not in parameters:
            raise NodeSpecificationInsufficientError(self, 'Need parameter adminid for now') # FIXME: should get it from the JSON file
        if 'hostname' not in parameters:
            raise NodeSpecificationInsufficientError(self, 'Needs parameter hostname for now') # FIXME: should get it from the JSON file
        if not hostname_validate(parameters['hostname']):
            raise NodeSpecificationInvalidError(self, 'hostname', parameters['hostname'])
        if 'sitejsonfile' in parameters:
            cmd = f"sudo ubos-admin deploy --file {parameters['sitejsonfile']}"
        elif 'backupfile' in parameters:
            cmd = f"sudo ubos-admin restore --in {parameters['backupfile']}"
        else:
            raise NodeSpecificationInsufficientError(self, 'Need parameter sitejsonfile or backupfile')

        parameters = dict(parameters)
        parameters['existing-account-uri'] = f"acct:{ parameters['adminid'] }@{ parameters['hostname'] }"
        parameters['nonexisting-account-uri'] = f"acct:does-not-exist@{ parameters['hostname'] }"

        self._exec_shell(cmd)
        ret = self._instantiate_ubos_node(rolename, parameters)
        return ret


    def _instantiate_ubos_node(self, rolename: str, parameters: dict[str,Any]) -> Node:
        """
        This needs to be subclassed to control/observe the running UBOS Node programmatically.
        """
        raise Exception('_instantiate_ubos_node must be overridden') # pylint: disable=broad-exception-raised


    def _unprovision_node(self, node: Node) -> None:
        parameters = node._parameters
        sshuri = parameters.get('sshuri')
        identity_file = parameters.get('identity_file')

        self._exec_shell(
            f"sudo ubos-admin undeploy --siteid { node.parameter('siteid') }",
            sshuri,
            identity_file
        )


    def _exec_shell(self, cmd: str, sshuri: str | None = None, identity_file: str | None = None):
        """
        Invoke a shell command either locally or remotely over ssh.
        This is defiend on UbosNodeDriver, not UbosNode, so we can invoke it before attempting to
        instantiate the UbosNode.
        """
        if sshuri:
            fullcmd = 'ssh'
            if identity_file:
                fullcmd += f' -i "{ identity_file }"'
            fullcmd += f' "{ sshuri }"'
            fullcmd += cmd
        else:
            fullcmd = cmd

        info( f"Executing '{fullcmd}'")
        ret = subprocess.run(fullcmd, shell=True, check=False)

        return ret.returncode
