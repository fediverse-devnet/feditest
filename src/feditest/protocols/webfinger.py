"""
"""

from httpx import Response
import json
from typing import Any

from feditest.protocols import NodeDriver, NotImplementedByDriverError
from feditest.protocols.web import WebClient,  WebServer
from feditest.utils import account_id_validate, http_https_uri_validate, http_https_acct_uri_validate

class WebFingerServer(WebServer):
    """
    A Node that acts as a WebFinger server.
    """
    def __init__(self, rolename: str, hostname: str, node_driver: 'NodeDriver') -> None:
        super().__init__(rolename, hostname, node_driver)

    def obtain_account_identifier(self, nickname: str = None) -> str:
        """
        Return the identifier of an existing or newly created account on this
        Node that a client is supposed to be able to perform WebFinger resolution on.
        The identifier is of the form ``acct:foo@bar.com``.
        nickname: refer to this account by this nickname; used to disambiguate multiple accounts on the same server
        return: the identifier
        """
        if nickname:
            return self.node_driver.prompt_user(
                    f'Please enter the URI of an existing or new account for {nickname} at this WebFingerServer (e.g. "acct:testuser@example.local" )',
                    account_id_validate )
        else:
            return self.node_driver.prompt_user(
                    'Please enter the URI of an existing or new account at this WebFingerServer (e.g. "acct:testuser@example.local" )',
                    account_id_validate )

    def obtain_non_existing_account_identifier(self, nickname: str = None ) ->str:
        """
        Return the identifier of an account that does not exist on this Node, but that
        nevertheless follows the rules for identifiers of this Node.
        The identifier is of the form ``foo@bar.com``.
        nickname: refer to this account by this nickname; used to disambiguate multiple accounts on the same server
        return: the identifier
        """
        if nickname:
            return self.node_driver.prompt_user(
                f'Please enter the URI of an non-existing account for {nickname} at this WebFingerServer (e.g. "acct:does-not-exist@example.local" )',
                account_id_validate )
        else:
            return self.node_driver.prompt_user(
                'Please enter the URI of an non-existing account at this WebFingerServer (e.g. "acct:does-not-exist@example.local" )',
                account_id_validate )


class WebFingerClient(WebClient):
    """
    A Node that acts as a WebFinger client.
    """
    def __init__(self, rolename: str, node_driver: 'NodeDriver') -> None:
        super().__init__(rolename, node_driver)

    def perform_webfinger_query_for(self, resource_uri: str) -> dict[str,Any]:
        """
        Make this Node perform a WebFinger query for the provided resource_uri.
        The resource_uri must be a valid, absolute URI, such as 'acct:foo@bar.com` or
        'https://example.com/aabc' (not escaped).
        Return a dict that is the parsed form of the JRD or throws an exception
        """
        raise NotImplementedByDriverError(WebFingerClient.perform_webfinger_query_for)

    class UnknownResourceException(RuntimeError):
        """
        Raised when a WebFinger query results in a 404 because the resource cannot be
        found by the server.
        resource_uri: URI of the resource
        http_response: the underlying Response object
        """
        def __init__(self, resource_uri: str, http_response: Response):
            self.resource_uri = resource_uri
            self.http_response = http_response

    class UnsupportedUriSchemeError(RuntimeError):
        def __init__(self, resource_uri: str):
            self.resource_uri = resource_uri

    class InvalidUriError(RuntimeError):
        def __init__(self, resource_uri: str):
            self.resource_uri = resource_uri

    class CannotDetermineWebfingerHost(RuntimeError):
        def __init__(self, resource_uri: str):
            self.resource_uri = resource_uri


class Jrd:
    """
    Captures the content of a WebFinger result. This is basically just a wrapper around a JSON structure.
    """
    def __init__(self, json_string: str):
        self.json = json.loads(json_string)
    
    class JrdError(RuntimeError):
        pass

    class InvalidTypeError(JrdError):
        pass
    
    def is_registered_relation_type(value: str) -> bool:
        """
        Return True if the provided value is a registered relation type in
        https://www.iana.org/assignments/link-relations/link-relations.xhtml
        """

        # copy-pasted from the CSV file at https://www.iana.org/assignments/link-relations/link-relations.xhtml
        defined = """about
acl
alternate
amphtml
appendix
apple-touch-icon
apple-touch-startup-image
archives
author
blocked-by
bookmark
canonical
chapter
cite-as
collection
contents
convertedfrom
copyright
create-form
current
describedby
describes
disclosure
dns-prefetch
duplicate
edit
edit-form
edit-media
enclosure
external
first
glossary
help
hosts
hub
icon
index
intervalafter
intervalbefore
intervalcontains
intervaldisjoint
intervalduring
intervalequals
intervalfinishedby
intervalfinishes
intervalin
intervalmeets
intervalmetby
intervaloverlappedby
intervaloverlaps
intervalstartedby
intervalstarts
item
last
latest-version
license
linkset
lrdd
manifest
mask-icon
me
media-feed
memento
micropub
modulepreload
monitor
monitor-group
next
next-archive
nofollow
noopener
noreferrer
opener
openid2.local_id
openid2.provider
original
p3pv1
payment
pingback
preconnect
predecessor-version
prefetch
preload
prerender
prev
preview
previous
prev-archive
privacy-policy
profile
publication
related
restconf
replies
ruleinput
search
section
self
service
service-desc
service-doc
service-meta
sip-trunking-capability
sponsored
start
status
stylesheet
subsection
successor-version
sunset
tag
terms-of-service
timegate
timemap
type
ugc
up
version-history
via
webmention
working-copy
working-copy-of"""
        return value in defined.split()

    def is_valid_media_type(value: str) -> bool:
        """
        This should check for a valid media type per RFC 6838.
        FIXME
        """
        return value.find('/') > 0

    def validate(self) -> None:
        """
        Validate the correctness of the JRD. Throw Exceptions if it is not valid.
        """
        if not type(self.json) is dict:
            raise Jrd.InvalidTypeError(self, 'Must be a JSON object')
        
        if 'subject' in self.json:
            # is optional
    
            if not type(self.json['subject']) is str:
                raise Jrd.InvalidTypeError(self, 'Member subject must be a string')
        
            if not http_https_acct_uri_validate(self.json['subject']):
                raise Jrd.InvalidUriError(self, 'Member subject must be an absolute URI')
    
        
        if 'aliases' in self.json:
            # is optional
            
            if not type(self.json['aliases']) is list:
                raise Jrd.InvalidTypeError(self, 'Member aliases must be a JSON array')

            for alias in self.json['aliases'] :
                if not type(alias) is str:
                    raise Jrd.InvalidTypeError(self, 'Members of the aliases array must be strings')

                if not http_https_acct_uri_validate(alias):
                    raise Jrd.InvalidUriError(self, 'Members of aliases array must be absolute URIs')

        if 'properties' in self.json:
            # is optional
            
            if not type(self.json['properties']) is dict:
                raise Jrd.InvalidTypeError(self, 'Member properties must be a JSON object')

            for key, value in self.json['properties']:
                if not type(key) is str:
                    raise Jrd.InvalidTypeError(self, 'Names in the properties object must be strings')

                if value is not None and type(value) is not str:
                    raise Jrd.InvalidTypeError(self, 'Values in the properties object must be strings or null')
        
        if 'links' in self.json:
            # is optional

            if not type(self.json['links']) is list:
                raise Jrd.InvalidTypeError(self, 'Member links must be a JSON array')
            
            for link in self.json['links']:
                if not type(link) is dict:
                    raise Jrd.InvalidTypeError(self, 'Members of the links array must be JSON objects')

                if not 'rel' in link:
                    raise Jrd.MissingMemberError(self, 'All members of the links array must have a rel property')
                
                if not type(link['rel']) is str:
                    raise Jrd.InvalidTypeError(self, 'Values for the rel member in the links array must be strings')

                if not http_https_acct_uri_validate(link['rel']) and not Jrd.is_registered_relation_type(link['rel']):
                    raise Jrd.InvalidRelError(self, 'All rel entries in the links array must be a URI or a registered relation type')
                
                if 'type' in link:
                    # is optional
                    
                    if not type(link['type']) is str:
                        raise Jrd.InvalidTypeError(self, 'Values for the type member in the links array must be strings')

                    if not Jrd.is_valid_media_type(link['type']):
                        raise Jrd.InvalidMediaTypeError(self, 'Values for the type member in the links array must be valid media types')

                if 'href' in link:
                    # is optional
                    
                    if not type(link['href']) is str:
                        raise Jrd.InvalidTypeError(self, 'Values for the type member in the links array must be strings')

                    if not http_https_uri_validate(link['href']):
                        raise Jrd.InvalidUriError(self, 'Values for the href member in the links array must be URIs')

                # FIXME: also need to check titles
                # FIXME: also need to check properties
