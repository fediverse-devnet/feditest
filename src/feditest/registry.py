"""
Registry and certificate authority for locally-allocated hostnames and their
certificates.
"""

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, load_pem_private_key
from datetime import datetime, timedelta, UTC
import json
import msgspec
import random
import re
from typing import cast

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
        with open(filename, 'r', encoding='utf-8') as f:
            registry_json = json.load(f)

        ret = msgspec.convert(registry_json, type=Registry)
        return ret


    @staticmethod
    def create(rootdomain: str | None = None) -> 'Registry':
        if not rootdomain:
            rootdomain = f'{ random.randint(1000, 9999) }.lan'

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
                x509.NameAttribute(x509.NameOID.COMMON_NAME, "feditest-user.example"),
            ])
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
        if not appname:
            safe_appname = 'unnamed'
        elif m := re.match('^([0-9A-Za-z]*)', appname):
            safe_appname = m.group(1).lower()
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
        ret = self.hosts.get(host)
        if ret is None:
            raise Exception(f'Unknown host: {host}')

        host_key: rsa.RSAPrivateKey
        if ret.key is None:
            ret.cert = None # That is now invalid, too
            host_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            ret.key = host_key.private_bytes(
                encoding=Encoding.PEM,
                format=PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=NoEncryption()).decode('utf-8')

        if ret.cert is None:
            host_key =  cast(rsa.RSAPrivateKey, load_pem_private_key(ret.key.encode('utf-8'), password=None))
            host_subject = x509.Name([
                x509.NameAttribute(x509.NameOID.COMMON_NAME, host),
            ])
            host_csr = x509.CertificateSigningRequestBuilder().subject_name(host_subject
                ).sign(host_key, hashes.SHA256())

            self.obtain_registry_root() # make sure we have it
            ca_cert = x509.load_pem_x509_certificate(cast(str,self.ca.cert).encode('utf-8'))
            ca_key = cast(rsa.RSAPrivateKey, load_pem_private_key(cast(str,self.ca.key).encode('utf-8'), password=None))
            now = datetime.now(UTC)
            host_cert = x509.CertificateBuilder().subject_name(host_csr.subject
                ).issuer_name(ca_cert.subject
                ).public_key(host_csr.public_key()
                ).serial_number(x509.random_serial_number()
                ).not_valid_before(now
                ).not_valid_after(now + timedelta(days=365)  # Expires after 1 year
                ).sign(ca_key, hashes.SHA256())
            ret.cert = host_cert.public_bytes(Encoding.PEM).decode('utf-8')

        return ret
