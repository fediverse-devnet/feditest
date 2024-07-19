"""
Hostname registry and certificate authority on UBOS.
"""

import random

from feditest.ca import CertificateAuthority
from feditest.dns import DnsRegistry

class UbosLocalRegistry(CertificateAuthority, DnsRegistry):
    """
    Given a root domain (say '123.lan'), this manages hostnames
    and corresponding certificates.

    UBOS Gears already appends hostnames of locally deployed sites to /etc/hosts,
    so we don't need to do this.
    """

    def __init__(self, root_domain: str | None = None):
        if root_domain:
            self._root_domain = root_domain
        else:
            self.root_domain = f'{ random.randint(1000, 9999) }.lan'
        self._index_by_app = {}


    def obtain_new_hostname(self, appname: str | None = None) -> str:
        """
        Give out sequentially indexed hostnames for each app
        """
        if not appname:
            appname = 'unnamed'

        index = self._index_by_app.get(appname)
        if not index:
            index = 1
        self._index_by_app[appname] = index+1

        return f'{ appname }-{ index }.{ self.root_domain }'


    def obtain_keys_and_cert(self, hostname: str) -> tuple[str,str]:
        pass

