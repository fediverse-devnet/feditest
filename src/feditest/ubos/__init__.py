"""
Nodes managed via UBOS https://ubos.net/
"""
import json
import secrets
import subprocess
import shutil
from typing import Any

from feditest.protocols import Node, NodeDriver, NodeSpecificationInsufficientError, NodeSpecificationInvalidError
from feditest.reporting import info
from feditest.utils import hostname_validate

"""
There is no UbosNode: it only needs to carry rshcmd (optional) and having an entire
separate class that needs to be woven into the rest of the class hierarchy as a mixin or as a second
supertype does not appear to be worth it.

Instead we keep this value in the parameters dict, where it comes from anyway.
"""

ADMIN_USER = 'feditestadmin' # Note: 'admin' is not permitted by Mastodon
ADMIN_CREDENTIAL = 'secret'
DOES_NOT_EXIST_USER = 'does-not-exist'


class UbosNodeDriver(NodeDriver):
    """
    A general-purpose NodeDriver for Nodes provisioned through UBOS Gears.
    """
    def _provision_node(self, rolename: str, parameters: dict[str,Any]) -> Node:
        """
        The UBOS driver knows how to provision a node either by deploying a UBOS Site JSON file
        with "ubos-admin deploy" or to restore a known state of a Site with "ubos-admin restore".
        It performs these operations locally, or if rshcmd information is provided, remotely.
        rshcmd is simply prepended to the ubos-admin command, so it could be something like:
        * `ssh user@host`
        * `ssh -i identity-file user@host`
        * `sudo machinectl shell ubosdev@container`
        * Because of its generality, the syntax of this parameter is not validated.
        """
        if not parameters:
            raise NodeSpecificationInsufficientError(self, 'No parameters given')

        if 'hostname' not in parameters:
            raise NodeSpecificationInsufficientError(self, 'Needs parameter hostname for now') # FIXME: should get it from the JSON file
        if not hostname_validate(parameters['hostname']):
            raise NodeSpecificationInvalidError(self, 'hostname', parameters['hostname'])

        rshcmd = parameters.get('rshcmd')
        if rshcmd:
            if self._exec_shell('which ubos-admin', rshcmd):
                raise OSError(f'{ type(self).__name__ } with an rshcmd requires UBOS Gears on the remote system (see ubos.net).')
        else:
            if not shutil.which('ubos-admin'):
                raise OSError(f'{ type(self).__name__ } without an rshcmd requires a local system running UBOS Gears (see ubos.net).')

        parameters = dict(parameters)

        # We currently have 3 modes. We want to get rid of the sitejsonfile one
        if 'backupfile' in parameters:
            self._provision_node_from_backupfile(rolename, parameters)
        elif 'sitejsonfile' in parameters:
            self._provision_node_from_sitejson(rolename, parameters)
        else:
            self._provision_node_with_generated_sitejson(rolename, parameters)

        ret = self._instantiate_ubos_node(rolename, parameters)
        return ret


    def _provision_node_from_backupfile(self,  rolename: str, parameters: dict[str,Any]) -> None:
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
        if 'backupfile' in parameters:
            cmd = f"sudo ubos-admin restore --in {parameters['backupfile']}"
        else:
            raise NodeSpecificationInsufficientError(self, 'Need parameter sitejsonfile or backupfile')

        parameters['existing-account-uri'] = f"acct:{ parameters['adminid'] }@{ parameters['hostname'] }"
        parameters['nonexisting-account-uri'] = f"acct:does-not-exist@{ parameters['hostname'] }"

        self._exec_shell(cmd)


    def _provision_node_from_sitejson(self,  rolename: str, parameters: dict[str,Any]) -> None:
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
        else:
            raise NodeSpecificationInsufficientError(self, 'Need parameter sitejsonfile or backupfile')

        parameters['existing-account-uri'] = f"acct:{ parameters['adminid'] }@{ parameters['hostname'] }"
        parameters['nonexisting-account-uri'] = f"acct:does-not-exist@{ parameters['hostname'] }"

        self._exec_shell(cmd, parameters.get('rshcmd'))


    def _provision_node_with_generated_sitejson(self,  rolename: str, parameters: dict[str,Any]) -> None:
            parameters['existing-account-uri'] = f"acct:{ ADMIN_USER }@{ parameters['hostname'] }"
            parameters['nonexisting-account-uri'] = f"acct:{ DOES_NOT_EXIST_USER }@{ parameters['hostname'] }"
            parameters['siteid'] = self._generate_siteid()
            parameters['appconfigid'] = self._generate_appconfigid()

            siteJson = {
                'hostname' : parameters['hostname'],
                'siteid' : parameters['siteid'],
                'admin' : {
                    'email' : f'{ ADMIN_USER }@{ parameters["hostname"] }',
                    'username' : ADMIN_USER,
                    'userid' : ADMIN_USER,
                    'credential' : ADMIN_CREDENTIAL
                },
                # 'tls' : { FIXME
                # },
            }
            siteJson['appconfigs'] = self._getAppConfigsJson()
            if self._exec_shell('sudo ubos-admin deploy --stdin', parameters.get('rshcmd'), json.dumps(siteJson)):
                raise NodeSpecificationInsufficientError(self, 'ubos-admin deploy failed')


    def _getAppConfigsJson(self):
        raise Exception( 'AppConfigs fragment for the Site JSON file must be defined in a subclass')


    def _instantiate_ubos_node(self, rolename: str, parameters: dict[str,Any]) -> Node:
        """
        This needs to be subclassed to control/observe the running UBOS Node programmatically.
        """
        raise Exception('_instantiate_ubos_node must be overridden') # pylint: disable=broad-exception-raised


    def _unprovision_node(self, node: Node) -> None:
        self._exec_shell( f"sudo ubos-admin undeploy --siteid { node.parameter('siteid') }", node.parameter('rshcmd'))


    def _exec_shell(self, cmd: str, rshcmd: str | None = None, stdin_content: str | None = None):
        """
        Invoke a shell command either locally or remotely over rshcmd.
        This is defiend on UbosNodeDriver, not UbosNode, so we can invoke it before attempting to
        instantiate the UbosNode.
        """
        if rshcmd:
            fullcmd = rshcmd
            fullcmd += cmd
        else:
            fullcmd = cmd

        if stdin_content:
            info( f"Executing '{fullcmd}' with some stdin content")
            ret = subprocess.run(fullcmd, shell=True, check=False, text=True, input=stdin_content)
        else:
            info( f"Executing '{fullcmd}'")
            ret = subprocess.run(fullcmd, shell=True, check=False, text=True)

        return ret.returncode


    def _generate_siteid(self):
        ret = 's'
        for i in range(40):
            ret += format(secrets.randbelow(16), 'x')
        return ret


    def _generate_appconfigid(self):
        ret = 'a'
        for i in range(40):
            ret += format(secrets.randbelow(16), 'x')
        return ret
