"""
An in-process Node implementation for now.
"""

import json
import random
import string
from datetime import datetime
from typing import Any, Callable, Iterable

import httpx

from feditest import nodedriver
from feditest.protocols import NodeDriver
from feditest.protocols.fediverse import FediverseNode
from feditest.protocols.web import (
    HttpRequestResponsePair,
    ParsedUri,
    WebClient,
    WebServerLog,
)
from feditest.protocols.webfinger import WebFingerClient
from feditest.reporting import info
from feditest.utils import (
    account_id_validate,
    http_https_acct_uri_validate,
    http_https_uri_validate,
)


class Jrd:
    """
    Captures the content of a WebFinger result. This is basically just a wrapper around a JSON structure.
    """
    def __init__(self, json_string: str):
        self._json = json.loads(json_string)


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
        if not isinstance(self._json, dict):
            raise Jrd.InvalidTypeError(self, 'Must be a JSON object')

        if 'subject' in self._json:
            # is optional

            if not isinstance(self._json['subject'], str):
                raise Jrd.InvalidTypeError(self, 'Member subject must be a string')

            if not http_https_acct_uri_validate(self._json['subject']):
                raise Jrd.InvalidUriError(self, 'Member subject must be an absolute URI')


        if 'aliases' in self._json:
            # is optional

            if not isinstance(self._json['aliases'], list):
                raise Jrd.InvalidTypeError(self, 'Member aliases must be a JSON array')

            for alias in self._json['aliases'] :
                if not isinstance(alias, str):
                    raise Jrd.InvalidTypeError(self, 'Members of the aliases array must be strings')

                if not http_https_acct_uri_validate(alias):
                    raise Jrd.InvalidUriError(self, 'Members of aliases array must be absolute URIs')

        if 'properties' in self._json:
            # is optional

            if not isinstance(self._json['properties'], dict):
                raise Jrd.InvalidTypeError(self, 'Member properties must be a JSON object')

            for key, value in self._json['properties']:
                if not isinstance(key, str):
                    raise Jrd.InvalidTypeError(self, 'Names in the properties object must be strings')

                if value is not None and not isinstance(value, str):
                    raise Jrd.InvalidTypeError(self, 'Values in the properties object must be strings or null')

        if 'links' in self._json:
            # is optional

            if not isinstance(self._json['links'], list):
                raise Jrd.InvalidTypeError(self, 'Member links must be a JSON array')

            for link in self._json['links']:
                if not isinstance(link, dict):
                    raise Jrd.InvalidTypeError(self, 'Members of the links array must be JSON objects')

                if 'rel' not in link:
                    raise Jrd.MissingMemberError(self, 'All members of the links array must have a rel property')

                if not isinstance(link['rel'], str):
                    raise Jrd.InvalidTypeError(self, 'Values for the rel member in the links array must be strings')

                if not http_https_acct_uri_validate(link['rel']) and not Jrd.is_registered_relation_type(link['rel']):
                    raise Jrd.InvalidRelError(self, 'All rel entries in the links array must be a URI or a registered relation type')

                if 'type' in link:
                    # is optional

                    if not isinstance(link['type'], str):
                        raise Jrd.InvalidTypeError(self, 'Values for the type member in the links array must be strings')

                    if not Jrd.is_valid_media_type(link['type']):
                        raise Jrd.InvalidMediaTypeError(self, 'Values for the type member in the links array must be valid media types')

                if 'href' in link:
                    # is optional

                    if not isinstance(link['href'], str):
                        raise Jrd.InvalidTypeError(self, 'Values for the type member in the links array must be strings')

                    if not http_https_uri_validate(link['href']):
                        raise Jrd.InvalidUriError(self, 'Values for the href member in the links array must be URIs')

                # FIXME: also need to check titles
                # FIXME: also need to check properties


class Imp(WebFingerClient):
    # use superclass constructor

    # @override # from WebClient
    def http_get(self, uri: str) -> httpx.Response:
        # Do not follow redirects automatically, we need to know whether there are any
        info( f'http_get of {uri}')
        return httpx.get(uri, follow_redirects=False, verify=False) # FIXME: disable TLS cert verification for now

    # @override # from WebFingerClient
    def perform_webfinger_query_for(self, resource_uri: str) -> Jrd:
        uri = self.construct_webfinger_uri_for(resource_uri)

        response: httpx.Response = None
        with httpx.Client(verify=False) as client:  # FIXME disable TLS cert verification for now
            info( f'Performing HTTP GET on {uri}')
            request = httpx.Request('GET', uri)
            for redirect_count in range(10, 0, -1):
                response = client.send(request)
                if response.is_redirect:
                    if redirect_count <= 0:
                        raise WebClient.TooManyRedirectsError(uri)
                    request = response.next_request

        if response and response.is_success :
            jrd = Jrd(response.content) # may raise
            jrd.validate() # may raise
            return jrd
        else:
            raise WebFingerClient.UnknownResourceException(uri, response)


@nodedriver
class ImpInProcessNodeDriver(NodeDriver):
    # use superclass constructor

    # Python 3.12 @override
    def _provision_node(self, rolename: str, hostname: str, parameters: dict[str,Any] | None = None ) -> Imp:
        if parameters:
            raise Exception('ImpInProcessNodeDriver nodes do not take parameters')

        node = Imp(rolename, self)
        return node


    # Python 3.12 @override
    def _unprovision_node(self, node: Imp) -> None:
        pass

