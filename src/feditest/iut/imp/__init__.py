"""
"""
import urllib.parse

from feditest.iut.fediverse import FediverseNodeIUT, FediverseNodeIUTDriver

class Imp(FediverseNodeIUT):
    def __init__(self, nickname: str, iut_driver: 'FediverseNodeIUTDriver') -> None:
        super().__init__(nickname, iut_driver)


class ImpDriver(FediverseNodeIUTDriver):
    def __init__(self, name: str) -> None:
        super.__init__(name)

    # Python 3.12 @override
    def _provision_IUT(self, nickname: str) -> Imp:
        return Imp(nickname, self);




def construct_webfinger_uri(domain_name: str, resource_identifier: str) -> str
    """
    Helper method to construct the WebFinger URI from a domain name and
    the identifier of the resource.
    """
    resource_schemes : list[str] = ( 'acct', 'http', 'https' )

    for scheme in resource_schemes :
        if resource_identifier.startswith(scheme + ':'):
            return f"https://{domain_name}/.well-known/webfinger?resource={urllib.parse.quote(resource_identifier)}"

    else :
        raise Exception( 'Unsupported resource_identifier: ' + resource_identifier )

