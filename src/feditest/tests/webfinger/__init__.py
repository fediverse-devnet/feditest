"""
Tests the WebFinger standard
"""

import urllib.parse

def construct_webfinger_uri(domain_name: str, resource_identifier: str) -> str
    """
    Helper method to construct the Webfinger URI from a domain name and
    the identifier of the resource.
    """
    resource_schemes : list[str] = ( 'acct', 'http', 'https' )

    for scheme in resource_schemes :
        if resource_identifier.startswith(scheme + ':'):
            return f"https://{domain_name}/.well-known/webfinger?resource={urllib.parse.quote(resource_identifier)}"

    else :
        error( 'Unsupported resource_identifier', resource_identifier )
        return None

