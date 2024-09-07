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
from typing import Any, cast

from feditest import registry
from feditest.protocols import (
    Account,
    AccountManager,
    Node,
    NodeConfiguration,
    NodeDriver,
    NodeSpecificationInsufficientError,
    NonExistingAccount
)

from feditest.reporting import error, info, trace, warning
from feditest.testplan import TestPlanConstellationNode
from feditest.utils import hostname_validate

"""
There is no UbosNode: all relevant info is in the UbosNodeConfiguration.
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


class UbosNodeConfiguration(NodeConfiguration):
    """
    Adds configuration information specific to UBOS. This is an abstract superclass.
    """
    def __init__(self,
        node_driver: 'UbosNodeDriver',
        siteid: str,
        appconfigid: str,
        appconfigjson: dict[str,Any],
        admin_email: str,
        admin_username: str,
        admin_userid: str,
        admin_credential: str,
        app: str,
        app_version: str | None = None,
        hostname: str | None = None,
        tlskey: str | None = None,
        tlscert: str | None = None,
        start_delay: float = 0.0,
        rshcmd: str | None = None,
    ):
        super().__init__(node_driver, app, app_version, hostname, start_delay)
        self._siteid = siteid
        self._appconfigid = appconfigid
        self._appconfigjson = appconfigjson
        self._admin_email = admin_email
        self._admin_username = admin_username
        self._admin_userid = admin_userid
        self._admin_credential = admin_credential
        self._tlskey = tlskey
        self._tlscert = tlscert
        self._rshcmd = rshcmd


    @property
    def rshcmd(self) -> str | None:
        return self._rshcmd


    @property
    def siteid(self) -> str:
        return self._siteid


    @property
    def appconfigid(self) -> str:
        return self._appconfigid


    # @property
    # def admin_email(self) -> str:
    #     return self._admin_email


    # @property
    # def admin_username(self) -> str:
    #     return self._admin_username


    # @property
    # def admin_userid(self) -> str:
    #     return self._admin_userid


    # @property
    # def admin_credential(self) -> str:
    #     return self._admin_credential


class UbosNodeDeployConfiguration(UbosNodeConfiguration):
    """
    Configuration of a UBOS Node that is instantiated with 'ubos-admin deploy'
    """
    def obtain_site_json(self) -> str:
        tlskey = self._tlskey
        tlscert = self._tlscert
        if tlskey is None or tlscert is None:
            # Obtain these as late as possible, so all hostnames etc in the constellation are known
            info = registry.obtain_new_hostinfo(self._app)
            if tlskey is None:
                tlskey = info.key
            if tlscert is None:
                tlscert = info.cert

        appconfigjson = self._appconfigjson
        appconfigjson['appconfigid'] = self._appconfigid
        almost = {
            'hostname' : self._hostname,
            'siteid' : self._siteid,
            'admin' : {
                'email' : self._admin_email,
                'username' : self._admin_username,
                'userid' : self._admin_userid,
                'credential' : self._admin_credential
            },
            'tls' : {
                'key' : tlskey,
                'crt' : tlscert
            },
            'appconfigs' : [
                appconfigjson
            ]
        }
        return json.dumps(almost)


class UbosNodeFromBackupConfiguration(UbosNodeConfiguration):
    """
    Configuration of a UBOS Node that is instantiated from a backup file with 'ubos-admin restore'
    """
    def __init__(self,
        node_driver: 'UbosNodeDriver',
        siteid: str,
        appconfigid: str,
        appconfigjson: dict[str, Any],
        admin_email: str,
        admin_username: str,
        admin_userid: str,
        admin_credential: str,
        backupfile: str,
        backup_appconfigid: str,
        app: str,
        app_version: str | None = None,
        hostname: str | None = None,
        tlskey: str | None = None,
        tlscert: str | None = None,
        start_delay: float = 0.0,
        rshcmd: str | None = None,
    ):
        super().__init__(node_driver, siteid, appconfigid, appconfigjson, admin_email, admin_username, admin_userid, admin_credential, app, app_version, hostname, tlskey, tlscert, start_delay, rshcmd)

        self._backupfile = backupfile
        self._backup_appconfigid = backup_appconfigid


    def obtain_empty_site_json(self) -> str:
        tlskey = self._tlskey
        tlscert = self._tlscert
        if tlskey is None or tlscert is None:
            # Obtain these as late as possible, so all hostnames etc in the constellation are known
            info = registry.obtain_new_hostinfo(self._app)
            if tlskey is None:
                tlskey = info.key
            if tlscert is None:
                tlscert = info.cert

        almost = {
            'hostname' : self._hostname,
            'siteid' : self._siteid,
            'admin' : {
                'email' : self._admin_email,
                'username' : self._admin_username,
                'userid' : self._admin_userid,
                'credential' : self._admin_credential
            },
            'tls' : {
                'key' : tlskey,
                'crt' : tlscert
            }
        }
        return json.dumps(almost)


    @property
    def backupfile(self):
        return self._backupfile


    @property
    def backup_appconfigid(self):
        return self._backup_appconfigid


class UbosNodeDriver(NodeDriver):
    """
    A general-purpose NodeDriver for Nodes provisioned through UBOS Gears.
    """
    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) -> Node:
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
        config = cast(UbosNodeConfiguration, config)

        if config._rshcmd:
            if self._exec_shell('which ubos-admin', config._rshcmd).returncode:
                raise OSError(f'{ type(self).__name__ } with an rshcmd requires UBOS Gears on the remote system (see ubos.net).')
        else:
            if not shutil.which('ubos-admin'):
                raise OSError(f'{ type(self).__name__ } without an rshcmd requires a local system running UBOS Gears (see ubos.net).')

        if account_manager is None:
            raise RuntimeError(f'No AccountManager set for rolename { rolename } with UbosNodeDriver { self }')

        # We currently have 2 modes
        if isinstance(config,UbosNodeFromBackupConfiguration):
            self._provision_node_from_backupfile(config, account_manager)
        elif isinstance(config, UbosNodeDeployConfiguration):
            self._provision_node_with_generated_sitejson(config, account_manager)
        else:
            raise RuntimeError(f'Unexpected type of config: { config }')

        try:
            ret = self._instantiate_ubos_node(rolename, config, account_manager)
            return ret

        except Exception as e:
            warning('Something went wrong during instantiation of UbosNode, undeploying', e)
            self._cleanup_node(config)
            raise e


    def _provision_node_from_backupfile(self, config: UbosNodeFromBackupConfiguration, account_manager: AccountManager) -> None:
        """
        We deploy a new, empty site.
        Then we add one AppConfig to it from backup.
        With this approach, we get to specify our own TLS data.
        """
        emptySiteJson = config.obtain_empty_site_json()

        if self._exec_shell('sudo ubos-admin deploy --stdin', config.rshcmd, emptySiteJson).returncode:
            raise UbosAdminException(self, 'sudo ubos-admin deploy --stdin', emptySiteJson)

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
        cmd += f' --appconfigid "{ config.backup_appconfigid }"'
        cmd += f' --tositeid "{ config.siteid }"'
        cmd += ' --createnew'
        cmd += f' --newappconfigid "{ config.appconfigid }"'
        cmd += ' --newcontext ""'
        cmd += f' --in "{ config.backupfile }"'

        if self._exec_shell(cmd).returncode:
            raise UbosAdminException(self, cmd)


    def _provision_node_with_generated_sitejson(self, config: UbosNodeDeployConfiguration, account_manager: AccountManager) -> None:
        siteJson = config.obtain_site_json()

        if self._exec_shell('sudo ubos-admin deploy --stdin', config.rshcmd, siteJson).returncode:
            raise UbosAdminException(self, 'sudo ubos-admin deploy --stdin', siteJson)


    def _getAppConfigJson(self, config: UbosNodeDeployConfiguration) -> dict[str,Any]:
        raise Exception( 'AppConfig fragment for the Site JSON file must be defined in a subclass')


    @abstractmethod
    def _instantiate_ubos_node(self, rolename: str, config: UbosNodeConfiguration, account_manager: AccountManager) -> Node:
        """
        This needs to be subclassed to control/observe the running UBOS Node programmatically.
        """
        raise Exception('_instantiate_ubos_node must be overridden') # pylint: disable=broad-exception-raised


    def _unprovision_node(self, node: Node) -> None:
        trace(f'UbosNodeDriver unprovision node { node.rolename }')
        config = cast(UbosNodeConfiguration, node.config)
        if self._exec_shell( f"sudo ubos-admin undeploy --siteid { config.siteid }", config.rshcmd).returncode:
            raise UbosAdminException(self, f"sudo ubos-admin undeploy --siteid { config.siteid }")


    def _cleanup_node(self, config: UbosNodeConfiguration):
        trace('Cleaning up UbosNode')
        self._exec_shell( f"sudo ubos-admin undeploy --siteid { config.siteid }", config.rshcmd ) # ignore errors


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
