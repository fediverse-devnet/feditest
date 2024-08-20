"""
Nodes managed via UBOS Gears https://ubos.net/
"""
from abc import abstractmethod
import hashlib
import json
import random
import secrets
import subprocess
import shutil
import string
from typing import Any

from feditest import registry
from feditest.protocols import Node, NodeDriver, NodeSpecificationInsufficientError, NodeSpecificationInvalidError
from feditest.reporting import error, info, trace, warning
from feditest.testplan import TestPlanConstellationNode
from feditest.utils import hostname_validate

"""
There is no UbosNode: it only needs to carry rshcmd (optional) and having an entire
separate class that needs to be woven into the rest of the class hierarchy as a mixin or as a second
supertype does not appear to be worth it.

Instead we keep this value in the parameters dict, where it comes from anyway.
"""

ADMIN_USER = 'feditestadmin' # Note: 'admin' is not permitted by Mastodon
DOES_NOT_EXIST_USER = 'does-not-exist'

class UbosAdminException(Exception):
    """
    Thrown if a `ubos-admin` operation failed.
    """
    def __init__(self, node_driver: 'UbosNodeDriver', cmd: str, indata: str | None = None, out: str | None = None):
        msg = f'node_driver: { node_driver }, cmd: "{ cmd }"'
        if indata:
            msg += f'\ninput data: { indata }'
        if out:
            msg += f'\nout: { out }'
        super().__init__(msg)


class UbosNodeDriver(NodeDriver):
    """
    A general-purpose NodeDriver for Nodes provisioned through UBOS Gears.
    """
    # Python 3.12 @override
    def _provision_node(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]) -> Node:
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
        trace(f'UbosNodeDriver provision node {rolename}')
        rshcmd = parameters.get('rshcmd')
        if rshcmd:
            if self._exec_shell('which ubos-admin', rshcmd).returncode:
                raise OSError(f'{ type(self).__name__ } with an rshcmd requires UBOS Gears on the remote system (see ubos.net).')
        else:
            if not shutil.which('ubos-admin'):
                raise OSError(f'{ type(self).__name__ } without an rshcmd requires a local system running UBOS Gears (see ubos.net).')

        if parameters.get('hostname') and not hostname_validate(parameters['hostname']):
            raise NodeSpecificationInvalidError(self, 'hostname', parameters['hostname'])

        # We currently have 2 modes
        if parameters and 'backupfile' in parameters:
            self._provision_node_from_backupfile(parameters)
        else:
            self._provision_node_with_generated_sitejson(parameters)

        try:
            ret = self._instantiate_ubos_node(rolename, test_plan_node, parameters)
            return ret

        except Exception as e:
            warning('Something went wrong during instantiation of UbosNode, undeploying', e)
            self._cleanup_node(parameters['siteid'], parameters.get('rshcmd'))
            raise e


    def _provision_node_from_backupfile(self, parameters: dict[str,Any]) -> None:
        """
        We deploy a new, empty site.
        Then we add one AppConfig to it from backup.
        With this approach, we get to specify our own TLS data.
        """
        if 'backup-appconfigid' not in parameters:
            raise NodeSpecificationInsufficientError(self, 'Need parameter "backup-appconfigid" to identify the to-be-restored AppConfigId in the backup file')

        if 'hostname' in parameters:
            info = registry.obtain_hostinfo(parameters['hostname'])
        else:
            info = registry.obtain_new_hostinfo(parameters.get('app'))
            parameters['hostname'] = info.host

        parameters['siteid'] = self._generate_siteid()
        parameters['appconfigid'] = self._generate_appconfigid()
        parameters['adminid'] = ADMIN_USER
        parameters['adminemail'] = f'{ ADMIN_USER }@{ parameters["hostname"] }'
        parameters['adminpass'] = self._generate_credential()

        emptySiteJson = {
            'hostname' : parameters['hostname'],
            'siteid' : parameters['siteid'],
            'admin' : {
                'email' : parameters['adminemail'],
                'username' : parameters['adminid'],
                'userid' : parameters['adminid'],
                'credential' : parameters['adminpass']
            },
            'tls' : {
                'key' : info.key,
                'crt' : info.cert
            },
        }
        if self._exec_shell('sudo ubos-admin deploy --stdin', parameters.get('rshcmd'), json.dumps(emptySiteJson)).returncode:
            raise UbosAdminException(self, 'sudo ubos-admin deploy --stdin', json.dumps(emptySiteJson))

        # From `ubos-admin restore --help`:
        #    ubos-admin restore --appconfigid <appconfigid> --tositeid <tositeid> --createnew [--newappconfigid <newid>] [--newcontext <context>] --in <backupfile>
        #         Restore only one AppConfiguration identified by its appconfigid
        #         <appconfigid> from local UBOS backup file <backupfile>, or from the
        #         UBOS backup file downloaded from URL <backupurl>, by adding it as a
        #         new AppConfiguration to a currently deployed site identified by its
        #         site id <tositeid>. However, use new appconfigid <newid> for it (or,
        #         if not provided, generate a new one). Optionally, if --newcontext
        #         <context> is provided, deploy the AppConfiguration to a different
        #         context path.

        cmd = 'sudo ubos-admin restore'
        cmd += f' --appconfigid "{ parameters["backup-appconfigid"] }"'
        cmd += f' --tositeid "{ parameters["siteid"] }"'
        cmd += ' --createnew'
        cmd += f' --newappconfigid "{ parameters["appconfigid"] }"'
        cmd += ' --newcontext ""'
        cmd += f' --in "{ parameters["backupfile"] }"'

        if self._exec_shell(cmd).returncode:
            raise UbosAdminException(self, cmd)


    def _provision_node_with_generated_sitejson(self, parameters: dict[str,Any]) -> None:
        if 'hostname' in parameters:
            info = registry.obtain_hostinfo(parameters['hostname'])
        else:
            info = registry.obtain_new_hostinfo(parameters.get('app'))
            parameters['hostname'] = info.host

        parameters['siteid'] = self._generate_siteid()
        parameters['appconfigid'] = self._generate_appconfigid()
        parameters['adminid'] = ADMIN_USER
        parameters['adminemail'] = f'{ ADMIN_USER }@{ parameters["hostname"] }'
        parameters['adminpass'] = self._generate_credential()
        parameters['doesnotexistid'] = DOES_NOT_EXIST_USER

        siteJson = {
            'hostname' : parameters['hostname'],
            'siteid' : parameters['siteid'],
            'admin' : {
                'email' : parameters['adminemail'],
                'username' : parameters['adminid'],
                'userid' : parameters['adminid'],
                'credential' : parameters['adminpass']
            },
            'tls' : {
                'key' : info.key,
                'crt' : info.cert
            },
        }
        siteJson['appconfigs'] = self._getAppConfigsJson(parameters)
        if self._exec_shell('sudo ubos-admin deploy --stdin', parameters.get('rshcmd'), json.dumps(siteJson)).returncode:
            raise UbosAdminException(self, 'sudo ubos-admin deploy --stdin', json.dumps(siteJson))


    def _getAppConfigsJson(self, parameters: dict[str,Any]) -> list[dict[str,Any]]:
        raise Exception( 'AppConfigs fragment for the Site JSON file must be defined in a subclass')


    @abstractmethod
    def _instantiate_ubos_node(self, rolename: str, test_plan_node: TestPlanConstellationNode, parameters: dict[str,Any]) -> Node:
        """
        This needs to be subclassed to control/observe the running UBOS Node programmatically.
        """
        raise Exception('_instantiate_ubos_node must be overridden') # pylint: disable=broad-exception-raised


    def _unprovision_node(self, node: Node) -> None:
        trace(f'UbosNodeDriver unprovision node { node.rolename }')
        if self._exec_shell( f"sudo ubos-admin undeploy --siteid { node.parameter('siteid') }", node.parameter('rshcmd')).returncode:
            raise UbosAdminException(self, f"sudo ubos-admin undeploy --siteid { node.parameter('siteid') }")


    def _cleanup_node(self, siteid: str, rshcmd: str | None = None):
        trace('Cleaning up UbosNode')
        self._exec_shell( f"sudo ubos-admin undeploy --siteid { siteid }", rshcmd ) # ignore errors


    def _exec_shell(self, cmd: str, rshcmd: str | None = None, stdin_content: str | None = None, capture_output : bool = False) -> subprocess.CompletedProcess:
        """
        Invoke a shell command either locally or remotely over rshcmd.
        This is defiend on UbosNodeDriver, not UbosNode, so we can invoke it before attempting to
        instantiate the UbosNode.
        This returns the Python CompletedProcess type
        """
        if rshcmd:
            fullcmd = rshcmd
            fullcmd += cmd
        else:
            fullcmd = cmd

        if stdin_content:
            info( f"Executing '{fullcmd}' with some stdin content" )
            ret = subprocess.run(fullcmd, shell=True, check=False, text=True, input=stdin_content, capture_output=capture_output)
        else:
            info( f"Executing '{fullcmd}'")
            ret = subprocess.run(fullcmd, shell=True, check=False, text=True, capture_output=capture_output)

        return ret


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


    def _generate_credential(self):
        chars = string.ascii_letters + string.digits + string.punctuation
        ret = ''.join(random.choice(chars) for i in range(16))
        return ret


    def _generate_unique_cert_filename(self,root_cert: str) -> str:
        """
        Helper to generate a unique filename for a cert.
        """
        alg = hashlib.sha256()
        alg.update(root_cert.encode('utf-8'))
        unique = alg.hexdigest()[:8] # just take a few bytes, good enough
        ret = f'/etc/ca-certificates/trust-source/anchors/feditest-{ unique }.pem'
        return ret


    def add_cert_to_trust_store(self, root_cert: str, rshcmd: str | None = None) -> None:
        """
        On behalf of the UbosNode (which isn't a class, by conceptually is a thing), save this
        root_cert in PEM format to the Device's trust store.

        Note: This may be invoked more than once on the same Device with the same data. We are
        lazy and simply overwrite.

        From "man update-ca-trust":
         • add it as a new file to directory /etc/ca-certificates/trust-source/anchors/
         • run update-ca-trust extract
        """
        filename = self._generate_unique_cert_filename(root_cert)
        trace(f'Add cert to trust store with filename {filename}')
        # Sorry for the trickery, this allows us to avoid having to have an extra parameter for scp-equivalent or such
        cmd = f'sudo bash -c "cat > { filename } && update-ca-trust refresh"'
        if self._exec_shell(cmd, rshcmd, root_cert).returncode:
            error(f'Failed to execute cmd {cmd}')


    def remove_cert_from_trust_store(self, root_cert: str, rshcmd: str | None = None) -> None:
        """
        Note: This may be invoked more than once on the same Device with the same data. We are
        lazy, delete it the first time and silently do nothing after.
        """
        filename = self._generate_unique_cert_filename(root_cert)
        trace(f'Remove cert from trust store with filename {filename}')
        cmd = f'sudo bash -c "[[ ! -e { filename } ]] || rm { filename } && update-ca-trust refresh"'
        if self._exec_shell(cmd, rshcmd, root_cert).returncode:
            error(f'Failed to execute cmd {cmd}')
