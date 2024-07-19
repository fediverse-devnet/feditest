"""
A DNS registry abstraction
"""

from abc import ABC


class DnsRegistry(ABC):
    """
    DNS registry abstraction.
    """

    def obtain_new_hostname(self, appname: str | None = None) -> str:
        """
        Obtain a DNS hostname that:
        1. can be resolved
        2. has not been handed out within the scope of this TestRun
        This abstraction can be implemented in several ways, such as:
        1. it has a list of enumerated hostnames that have been provisioned already and can be resolved with the default system DNS resolve
        2. it creates a new hostname and makes it resolvable by adding it to /etc/hosts or a locally running DNS resolver

        Param appname can be used to provide a hint (no requirement on the DnsRegistry to
        pay attention to the hint, however) what application is running, so debugging becomes easier.
        """
        pass


class PreallocatedStaticDnsRegistry(DnsRegistry):
    """
    A simple DNS registry implementation that hands out DNS names from a predefined list.
    """
    @staticmethod
    def read_from_file(filename: str) -> 'PreallocatedStaticDnsRegistry':
        with open(filename, 'r') as file:
            return file.readlines()


    def __init__(self, names: list[str]):
        self.names = names
        self.index = 0


    def obtain_new_hostname(self, appname: str | None = None) -> str:
        ret = self.names[self.index]
        self.index += 1
        return ret
