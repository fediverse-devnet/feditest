"""
Registry and certificate authority for locally-allocated hostnames and their
certificates.
"""

import certifi
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, load_pem_private_key
from datetime import datetime, timedelta, UTC
import json
import msgspec
import os.path
import random
import re
import shutil
from typing import cast

from feditest.reporting import error, trace, warning
from feditest.utils import FEDITEST_VERSION


class RegistryRoot(msgspec.Struct):
    """
    What we know about the root certificate of the CA
    """
    domain: str
    key: str | None = None # PEM format
    cert: str | None = None # PEM format


class RegistryHostInfo(msgspec.Struct):
    """
    What we know about a particular host
    """
    host: str
    key: str | None = None # PEM format
    cert: str | None = None # PEM format


class Registry(msgspec.Struct):
    """
    Given a root domain (say '123.lan'), this manages hostnames
    and corresponding certificates.
    """
    ca: RegistryRoot
    hosts: dict[str,RegistryHostInfo] = {}
    type: str = 'feditest-registry'
    feditest_version: str = FEDITEST_VERSION


    @staticmethod
    def load(filename: str) -> 'Registry':
        """
        Read a file, and instantiate a Registry from what we find.
        """
        trace(f'Registry.load({ filename })')
        with open(filename, 'r', encoding='utf-8') as f:
            registry_json = json.load(f)

        ret = msgspec.convert(registry_json, type=Registry)
        return ret


    @staticmethod
    def create(rootdomain: str | None = None) -> 'Registry':
        trace(f'Registry.create({ rootdomain or "None" })')
        if not rootdomain:
            rootdomain = f'{ random.randint(10000, 99999) }.lan'

        ret = Registry(ca=RegistryRoot(domain=rootdomain))
        return ret


    def is_compatible_type(self):
        return self.type is None or self.type == 'feditest-registry'


    def has_compatible_version(self):
        if not self.feditest_version:
            return True
        return self.feditest_version == FEDITEST_VERSION


    def as_json(self) -> bytes:
        ret = msgspec.json.encode(self)
        ret = msgspec.json.format(ret, indent=4)
        return ret


    def save(self, filename: str) -> None:
        with open(filename, 'wb') as f:
            f.write(self.as_json())


    def root_cert_for_trust_root(self):
        if self.ca:
            return self.ca.cert
        return None


    def obtain_registry_root(self) -> RegistryRoot:
        ca_key: rsa.RSAPrivateKey
        if not self.ca.key:
            self.ca.cert = None # That is now invalid, too
            ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            self.ca.key = ca_key.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=NoEncryption()).decode('utf-8')

        if not self.ca.cert:
            ca_subject = x509.Name([
                x509.NameAttribute(x509.NameOID.COMMON_NAME, "feditest-local-ca." + self.ca.domain),
            ])
            if self.ca.key is None:
                raise Exception("No key for CA")
            ca_key = cast(rsa.RSAPrivateKey, load_pem_private_key(self.ca.key.encode('utf-8'), password=None))
            now = datetime.now(UTC)
            ca_cert = x509.CertificateBuilder().subject_name(ca_subject
                ).issuer_name(ca_subject
                ).public_key(ca_key.public_key()
                ).serial_number(x509.random_serial_number()
                ).not_valid_before(now
                ).not_valid_after(now + timedelta(days=365)
                ).add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True,
                ).sign(ca_key, hashes.SHA256())

            self.ca.cert = ca_cert.public_bytes(Encoding.PEM).decode('utf-8')

            # also erase all certs in case the user deleted the root cert but did not delete the host certs
            for host in self.hosts:
                self.hosts[host] = RegistryHostInfo(host=host)

        return self.ca


    def obtain_new_hostinfo(self, appname: str | None = None ) -> RegistryHostInfo:
        host = self.obtain_new_hostname(appname)
        return self.obtain_hostinfo(host)


    def obtain_new_hostname(self, appname: str | None = None) -> str:
        """
        Give out a new hostname in the root domain. Does not create a cert
        This implementation will return sequentially indexed hostnames for each app
        """
        trace(f'Registry.obtain_new_hostname( { appname or "None" }) with domain { self.ca.domain }')
        if not appname:
            safe_appname = 'unnamed'
        elif m := re.match('^([0-9A-Za-z]*)', appname):
            safe_appname = m.group(1).lower() # take the first word
        else:
            safe_appname = 'other'

        current = 0
        for host in self.hosts:
            if m := re.search(f'^{ safe_appname }-(\\d+)\\.{ self.ca.domain }$', host):
                index = int(m.group(1))
                current = max(current, index)

        new_hostname = f'{ safe_appname }-{ current+1 }.{ self.ca.domain }'
        self.hosts[new_hostname] = RegistryHostInfo(host=new_hostname)
        return new_hostname


    def obtain_hostinfo(self, host: str) -> RegistryHostInfo:
        trace(f'Registry.obtain_hostinfo({ host }) with domain { self.ca.domain }')
        ret = self.hosts.get(host)
        if ret is None:
            # An externally specified hostname: add to set of known hosts
            ret = RegistryHostInfo(host=host)
            self.hosts[host] = ret

        host_key: rsa.RSAPrivateKey
        if ret.key is None:
            ret.cert = None # That is now invalid, too
            host_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            ret.key = host_key.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=NoEncryption()).decode('utf-8')

        if ret.cert is None:
            self.obtain_registry_root() # make sure we have it
            ca_cert = x509.load_pem_x509_certificate(cast(str,self.ca.cert).encode('utf-8'))
            ca_key = cast(rsa.RSAPrivateKey, load_pem_private_key(cast(str,self.ca.key).encode('utf-8'), password=None))

            host_key =  cast(rsa.RSAPrivateKey, load_pem_private_key(ret.key.encode('utf-8'), password=None))
            host_subject = x509.Name([
                x509.NameAttribute(x509.NameOID.COMMON_NAME, host),
            ])
            host_san = x509.SubjectAlternativeName([
                x509.DNSName(host)
            ])
            now = datetime.now(UTC)
            host_cert = x509.CertificateBuilder().subject_name(host_subject
                ).issuer_name(ca_cert.subject
                ).add_extension(host_san, critical=False
                ).public_key(host_key.public_key()
                ).serial_number(x509.random_serial_number()
                ).not_valid_before(now
                ).not_valid_after(now + timedelta(days=365)  # Expires after 1 year
                ).sign(ca_key, hashes.SHA256())
            ret.cert = host_cert.public_bytes(Encoding.PEM).decode('utf-8')

        return ret


    def memoize_system_trust_root(self) -> None:
        """
        Turns out that Python virtual environments use their own snapshot of the trusted root certificates
        and ignore subsequent system updates.
        In non-virtual environments it appears to use the system store (at least on Arch
        it's a symlink: /usr/lib/python3.12/site-packages/certifi/cacert.pem -> /etc/ssl/certs/ca-certificates.crt)
        The heuristic to look for /usr/ at the start of the path may not work on all OSs (FIXME?)
        So this and the following methods are a way to get around this.
        """
        cacert_file = certifi.where()
        if cacert_file.startswith('/usr/'):
            return # Not in a venv, nothing to do

        cacert_backup = cacert_file + ".feditest-backup"
        if os.path.exists(cacert_backup):
            warning(f'cacert backup file exists already, not overwriting: { cacert_backup }')
            return
        shutil.copy2(cacert_file, cacert_backup)


    def add_to_system_trust_root(self, root_cert: str) -> None:
        cacert_file = certifi.where()
        if cacert_file.startswith('/usr/'):
            return # Not in a venv, nothing to do

        with open(cacert_file, 'a') as f:
            f.write(root_cert)


    def reset_system_trust_root_if_needed(self) -> None:
        if not self.ca.cert:
            return # Wasn't ever used

        cacert_file = certifi.where()
        if cacert_file.startswith('/usr/'):
            return # Not in a venv, nothing to do

        cacert_backup = cacert_file + ".feditest-backup"
        if os.path.exists(cacert_backup):
            shutil.move(cacert_backup, cacert_file)
            return
        error(f'No cacert backup file, cannot restore: { cacert_backup }')


_singleton = Registry.create()
"""
The global singleton. Only access with functions below.
By default, we use a random domain.
"""


def registry_singleton():
    """
    This needs to be a function, otherwise different modules may end up with old values.
    """
    return _singleton


def set_registry_singleton(new_singleton: Registry):
    global _singleton
    ret = _singleton
    _singleton = new_singleton
    return ret
