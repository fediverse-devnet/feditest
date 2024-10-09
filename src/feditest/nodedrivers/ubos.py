"""
Nodes managed via UBOS Gears https://ubos.net/
"""
from abc import abstractmethod
import hashlib
import json
import os.path
import random
import re
import secrets
import subprocess
import shutil
import string
from typing import Any, cast

from feditest.nodedrivers import (
    APP_PAR,
    APP_VERSION_PAR,
    HOSTNAME_PAR,
    AccountManager,
    Node,
    NodeConfiguration,
    NodeDriver
)
from feditest.registry import registry_singleton
from feditest.reporting import error, trace, warning
from feditest.testplan import TestPlanConstellationNode, TestPlanNodeParameter, TestPlanNodeParameterMalformedError, TestPlanNodeParameterRequiredError
from feditest.utils import email_validate

"""
There is no UbosNode: all relevant info is in the UbosNodeConfiguration.
"""

SITEID_PAR = TestPlanNodeParameter(
    'siteid',
    """The UBOS SiteId to use for the app.""",
    validate = lambda s: re.fullmatch('s[0-9a-f]{40}', s)
)

APPCONFIGID_PAR = TestPlanNodeParameter(
    'appconfigid',
    """The UBOS AppConfigId to use for the app.""",
    validate = lambda s: re.fullmatch('a[0-9a-f]{40}', s)
)

ADMIN_USERID_PAR = TestPlanNodeParameter(
    'admin_userid',
    """User identifier for the administrator of the UBOS Site.""",
    default = 'feditestadmin', # Note: 'admin' is not permitted by Mastodon
    validate = lambda s: re.fullmatch('[-a-zA-Z0-9_]+', s)
)

ADMIN_USERNAME_PAR = TestPlanNodeParameter(
    'admin_username',
    """Human-readable name for the administrator of the UBOS Site.""",
    default = 'feditestadmin', # Note: 'admin' is not permitted by Mastodon
    validate = lambda s: len(s)
)

ADMIN_CREDENTIAL_PAR = TestPlanNodeParameter(
    'admin_credential',
    """Password for the administrator of the UBOS Site.""",
    validate = lambda s: len(s)
)

ADMIN_EMAIL_PAR = TestPlanNodeParameter(
    'admin_email',
    """Contact e-mail for the administrator of the UBOS Site.""",
    validate = email_validate
)

BACKUPFILE_PAR = TestPlanNodeParameter(
    'backupfile',
    '''If the app is to be instantiated by restoring from a .ubos-backup, specify its file name.
    You must also specify parameter "backup_appconfigid".''',
    validate = lambda s: os.path.isfile(s)
)

BACKUP_APPCONFIGID_PAR = TestPlanNodeParameter(
    'backup_appconfigid',
    f'''If the app is to be instantiated by restoring from a .ubos-backup, specify the AppConfigId to be restored.
    You must also specify parameter "{ BACKUPFILE_PAR }".''',
    validate = lambda s: re.fullmatch('a[0-9a-f]{40}', s)
)

TLSKEY_PAR = TestPlanNodeParameter(
    'tlskey',
    '''Use this TLS key for the webserver instead of automatically provisioning one locally.'''
    # FIXME: should be valdiated
)

TLSCERT_PAR = TestPlanNodeParameter(
    'tlscert',
    '''Use this TLS certificate chain for the webserver instead of a local certificate authority's.'''
    # FIXME: should be valdiated
)

START_DELAY_PAR = TestPlanNodeParameter(
    'start_delay',
    """Specify, in seconds, for how long feditest should wait until it considers the newly provisioned Node operational.""",
    validate = lambda s: isinstance(s, int) and s>=0
)

RSH_CMD_PAR = TestPlanNodeParameter(
    'rshcmd',
    """The ssh or other command to run to perform UBOS administration commands at a remote Node."""
    # Cannot validate, can be all sorts of things
)


class UbosAdminException(Exception):
    """
    Thrown if a `ubos-admin` operation failed.
    """
    def __init__(self, node_driver: 'UbosNodeDriver', cmd: str, indata: str | None = None, stdout: str | None = None, stderr: str | None = None):
        msg = f'node_driver: { node_driver }, cmd: "{ cmd }"'
        if indata:
            msg += f'\ninput data: { indata }'
        if stdout:
            msg += f'\nstdout: { stdout }'
        if stderr:
            msg += f'\nstderr: { stderr }'
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
        admin_userid: str,
        admin_username: str,
        admin_credential: str,
        admin_email: str,
        app: str,
        hostname: str, # Note: switched positions with app_version as it is required here
        app_version: str | None = None,
        tlskey: str | None = None,
        tlscert: str | None = None,
        start_delay: float = 0.0,
        rshcmd: str | None = None,
    ):
        super().__init__(node_driver, app, app_version, hostname, start_delay)
        self._siteid = siteid
        self._appconfigid = appconfigid
        self._appconfigjson = appconfigjson
        self._admin_userid = admin_userid
        self._admin_username = admin_username
        self._admin_credential = admin_credential
        self._admin_email = admin_email
        self._tlskey = tlskey
        self._tlscert = tlscert
        self._rshcmd = rshcmd


    @staticmethod
    def _generate_siteid():
        ret = 's'
        for i in range(40):
            ret += format(secrets.randbelow(16), 'x')
        return ret


    @staticmethod
    def _generate_appconfigid():
        ret = 'a'
        for i in range(40):
            ret += format(secrets.randbelow(16), 'x')
        return ret


    @staticmethod
    def _generate_credential():
        chars = string.ascii_letters + string.digits + "_-%"
        ret = ''.join(random.choice(chars) for i in range(16))
        return ret


    @staticmethod
    def create_from_node_in_testplan(
        test_plan_node: TestPlanConstellationNode,
        node_driver: 'UbosNodeDriver',
        appconfigjson: dict[str, Any],
        defaults: dict[str, str | None] | None = None
    ) -> 'UbosNodeConfiguration':
        """
        Parses the information provided in the "parameters" dict of TestPlanConstellationNode
        """
        siteid = test_plan_node.parameter(SITEID_PAR, defaults=defaults) or UbosNodeConfiguration._generate_siteid()
        appconfigid = test_plan_node.parameter(APPCONFIGID_PAR, defaults=defaults) or UbosNodeConfiguration._generate_appconfigid()
        app = test_plan_node.parameter_or_raise(APP_PAR, defaults=defaults)
        hostname = test_plan_node.parameter(HOSTNAME_PAR) or registry_singleton().obtain_new_hostname(app)
        admin_userid = test_plan_node.parameter(ADMIN_USERID_PAR, defaults=defaults) or 'feditestadmin'
        admin_username = test_plan_node.parameter(ADMIN_USERNAME_PAR, defaults=defaults) or 'feditestadmin'
        admin_credential = test_plan_node.parameter(ADMIN_CREDENTIAL_PAR, defaults=defaults) or UbosNodeConfiguration._generate_credential()
        admin_email = test_plan_node.parameter(ADMIN_EMAIL_PAR, defaults=defaults) or f'{ admin_userid }@{ hostname }'
        start_delay_1 = test_plan_node.parameter(START_DELAY_PAR, defaults=defaults)
        if start_delay_1:
            if isinstance(float, start_delay_1):
                start_delay = cast(float, start_delay_1)
            else:
                start_delay = float(start_delay_1)
        else:
            start_delay = 0.0

        backupfile = test_plan_node.parameter(BACKUPFILE_PAR)
        if backupfile:
            backup_appconfigid = test_plan_node.parameter(BACKUP_APPCONFIGID_PAR)
            if not backup_appconfigid:
                raise TestPlanNodeParameterRequiredError(BACKUP_APPCONFIGID_PAR, f' when "{ BACKUP_APPCONFIGID_PAR }" is given')

            return UbosNodeFromBackupConfiguration(
                node_driver = node_driver,
                siteid = siteid,
                appconfigid = appconfigid,
                appconfigjson = appconfigjson,
                admin_userid = admin_userid,
                admin_username = admin_username,
                admin_credential = admin_credential,
                admin_email = admin_email,
                backupfile = backupfile,
                backup_appconfigid = backup_appconfigid,
                app = app,
                hostname = hostname,
                app_version = test_plan_node.parameter(APP_VERSION_PAR, defaults=defaults),
                tlskey = test_plan_node.parameter(TLSKEY_PAR, defaults=defaults),
                tlscert = test_plan_node.parameter(TLSCERT_PAR, defaults=defaults),
                start_delay = start_delay,
                rshcmd = test_plan_node.parameter(RSH_CMD_PAR, defaults=defaults)
            )

        else:
            backup_appconfigid = test_plan_node.parameter(BACKUP_APPCONFIGID_PAR)
            if backup_appconfigid:
                raise TestPlanNodeParameterMalformedError(BACKUP_APPCONFIGID_PAR, f' must not be given unless "{ BACKUP_APPCONFIGID_PAR }" is given as well')

            return UbosNodeDeployConfiguration(
                node_driver = node_driver,
                siteid = siteid,
                appconfigid = appconfigid,
                appconfigjson = appconfigjson,
                admin_userid = admin_userid,
                admin_username = admin_username,
                admin_credential = admin_credential,
                admin_email = admin_email,
                app = app,
                hostname = hostname,
                app_version = test_plan_node.parameter(APP_VERSION_PAR, defaults=defaults),
                tlskey = test_plan_node.parameter(TLSKEY_PAR, defaults=defaults),
                tlscert = test_plan_node.parameter(TLSCERT_PAR, defaults=defaults),
                start_delay = start_delay,
                rshcmd = test_plan_node.parameter(RSH_CMD_PAR, defaults=defaults)
            )


    @property
    def rshcmd(self) -> str | None:
        return self._rshcmd


    @property
    def siteid(self) -> str:
        return self._siteid


    @property
    def appconfigid(self) -> str:
        return self._appconfigid


    @property
    def admin_email(self) -> str:
        return self._admin_email


    @property
    def admin_username(self) -> str:
        return self._admin_username


    @property
    def admin_userid(self) -> str:
        return self._admin_userid


    @property
    def admin_credential(self) -> str:
        return self._admin_credential


class UbosNodeDeployConfiguration(UbosNodeConfiguration):
    """
    Configuration of a UBOS Node that is instantiated with 'ubos-admin deploy'
    """
    def obtain_site_json(self) -> str:
        tlskey = self._tlskey
        tlscert = self._tlscert
        if tlskey is None or tlscert is None:
            # Obtain these as late as possible, so all hostnames etc in the constellation are known
            hostname = cast(str, self.hostname) # In the UbosNodeConfiguration it is mandatory
            info = registry_singleton().obtain_hostinfo(hostname)
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
        admin_userid: str,
        admin_username: str,
        admin_credential: str,
        admin_email: str,
        backupfile: str,
        backup_appconfigid: str,
        app: str,
        hostname: str,
        app_version: str | None = None,
        tlskey: str | None = None,
        tlscert: str | None = None,
        start_delay: float = 0.0,
        rshcmd: str | None = None,
    ):
        super().__init__(
            node_driver = node_driver,
            siteid = siteid,
            appconfigid = appconfigid,
            appconfigjson = appconfigjson,
            admin_userid = admin_userid,
            admin_username = admin_username,
            admin_credential = admin_credential,
            admin_email = admin_email,
            app = app,
            hostname = hostname,
            app_version = app_version,
            tlskey = tlskey,
            tlscert = tlscert,
            start_delay = start_delay,
            rshcmd = rshcmd)

        self._backupfile = backupfile
        self._backup_appconfigid = backup_appconfigid


    def obtain_empty_site_json(self) -> str:
        tlskey = self._tlskey
        tlscert = self._tlscert
        if tlskey is None or tlscert is None:
            # Obtain these as late as possible, so all hostnames etc in the constellation are known
            hostname = cast(str, self.hostname) # In the UbosNodeConfiguration it is mandatory
            info = registry_singleton().obtain_hostinfo(hostname)
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
    @staticmethod
    def test_plan_node_parameters() -> list[TestPlanNodeParameter]:
        return [ SITEID_PAR, APPCONFIGID_PAR, APP_PAR, HOSTNAME_PAR, ADMIN_USERID_PAR, ADMIN_USERNAME_PAR, ADMIN_CREDENTIAL_PAR, ADMIN_EMAIL_PAR, START_DELAY_PAR, BACKUPFILE_PAR, BACKUP_APPCONFIGID_PAR ]


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
        if isinstance(config, UbosNodeFromBackupConfiguration):
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

        cmd = 'sudo ubos-admin deploy --stdin'
        result = self._exec_shell(cmd, config.rshcmd, emptySiteJson, capture_output=True)
        if result.returncode:
            raise UbosAdminException(self, cmd, emptySiteJson, result.stdout, result.stderr)

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

        result = self._exec_shell(cmd, config.rshcmd, capture_output=True)
        if result.returncode:
            raise UbosAdminException(self, cmd, result.stdout, result.stderr)


    def _provision_node_with_generated_sitejson(self, config: UbosNodeDeployConfiguration, account_manager: AccountManager) -> None:
        siteJson = config.obtain_site_json()

        cmd = 'sudo ubos-admin deploy --stdin'
        result = self._exec_shell(cmd, config.rshcmd, siteJson, capture_output=True)
        if result.returncode:
            raise UbosAdminException(self, cmd, siteJson, result.stdout, result.stderr)


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
        cmd = f"sudo ubos-admin undeploy --siteid { config.siteid }"
        result = self._exec_shell(cmd, config.rshcmd, capture_output=True)
        if result.returncode:
            raise UbosAdminException(self, cmd, result.stdout, result.stderr)


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
            trace( f"Executing '{fullcmd}' with some stdin content" )
            ret = subprocess.run(fullcmd, shell=True, check=False, text=True, input=stdin_content, capture_output=capture_output)
        else:
            trace( f"Executing '{fullcmd}'")
            ret = subprocess.run(fullcmd, shell=True, check=False, text=True, capture_output=capture_output)

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


    def add_cert_to_trust_store_via(self, root_cert: str, rshcmd: str | None) -> None:
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


    def remove_cert_from_trust_store_via(self, root_cert: str, rshcmd: str | None) -> None:
        """
        Note: This may be invoked more than once on the same Device with the same data. We are
        lazy, delete it the first time and silently do nothing after.
        """
        filename = self._generate_unique_cert_filename(root_cert)
        trace(f'Remove cert from trust store with filename {filename}')
        cmd = f'sudo bash -c "[[ ! -e { filename } ]] || rm { filename } && update-ca-trust refresh"'
        if self._exec_shell(cmd, rshcmd, root_cert).returncode:
            error(f'Failed to execute cmd {cmd}')
