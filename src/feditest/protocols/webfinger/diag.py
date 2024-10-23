"""
"""

import json
from dataclasses import dataclass, field
from typing import Any

from feditest.nodedrivers import NotImplementedByNodeError
from feditest.protocols.web.diag import HttpRequestResponsePair, WebDiagClient
from . import WebFingerClient, WebFingerServer

from feditest.utils import (
    http_https_acct_uri_parse_validate,
    rfc5646_language_tag_parse_validate,
    uri_parse_validate,
)


class ClaimedJrd:
    """
    The JSON structure that claims to be a JRD. This can contain any JSON because it needs to hold whatever
    claims to be a JRD, even if it is invalid. It won't try to hold data that isn't valid JSON.
    """
    def __init__(self, json_string: str):
        if json_string is None or not isinstance(json_string, (str, bytes)):
            raise RuntimeError(f"Invalid payload type: {type(json_string)}")
        self._json = json.loads(json_string)


    class JrdError(RuntimeError):
        """
        Represents a problem during JRD parsing, such as syntax error.
        """
        def __init__(self, jrd: 'ClaimedJrd', msg: str):
            self._jrd = jrd
            self._msg = msg


        def __str__(self):
            return self._msg or self.__class__.__name__


    class InvalidTypeError(JrdError):
        """
        The JSON structure is invalid for a Jrd.
        """
        pass # pylint: disable=unnecessary-pass


    class InvalidUriError(JrdError):
        """
        The URI in a Jrd is invalid.
        """
        pass # pylint: disable=unnecessary-pass


    class InvalidValueError(JrdError):
        """
        A value in a Jrd is None or invalid.
        """
        pass # pylint: disable=unnecessary-pass


    class MissingMemberError(JrdError):
        """
        The JRD is missing a member that is required.
        """
        pass # pylint: disable=unnecessary-pass


    class InvalidRelError(JrdError):
        """
        The JRD specifies a link relationship that is invalid.
        """
        pass # pylint: disable=unnecessary-pass


    class InvalidMediaTypeError(JrdError):
        """
        The JRD specifies a media type that is invalid.
        """
        pass # pylint: disable=unnecessary-pass


    class InvalidLanguageTagError(JrdError):
        """
        The JRD specifies a language tag that is invalid.
        """
        pass # pylint: disable=unnecessary-pass


    def subject(self) -> str | None: # optional in WebFinger
        return self._json.get('subject')


    def aliases(self) -> list[str] | None:
        return self._json.get('aliases')


    def properties(self) -> dict[str, str | None] | None:
        return self._json['properties']


    def links(self) -> list[dict[str,Any | None]] | None :
        return self._json['links']


    def as_json_string(self) -> Any:
        return json.dumps(self._json)


    @staticmethod
    def create_and_validate(value: str) -> 'ClaimedJrd':
        ret = ClaimedJrd(value) # may raise JSONDecodeError
        ret.validate()          # may raise any of the errors defined here
        return ret


    @staticmethod
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

    @staticmethod
    def is_valid_media_type(value: str) -> bool:
        """
        This should check for a valid media type per RFC 6838.
        FIXME
        """
        return value.find('/') > 0


    VALID_JRD_KEYS = { "subject", "aliases", "properties", "links" }


    def validate(self) -> None: # pylint: disable=too-many-branches,too-many-statements
        """
        Validate the correctness of the JRD. Throws a single Exceptions if it is not valid. This Exception
        may be an ExceptionGroup in case there is more than one error.
        """
        excs : list[Exception] = []
        if not isinstance(self._json, dict):
            raise ClaimedJrd.InvalidTypeError(self, 'Must be a JSON object') # can't continue otherwise

        for key in self._json:
            if key not in self.VALID_JRD_KEYS:
                excs.append(ClaimedJrd.JrdError(self, f"Invalid key: {key}"))

        if 'subject' in self._json:
            # is optional

            if not isinstance(self._json['subject'], str):
                excs.append(ClaimedJrd.InvalidTypeError(self, 'Subject not a string'))
            elif http_https_acct_uri_parse_validate(self._json['subject']) is None:
                excs.append(ClaimedJrd.InvalidUriError(self, 'Subject not absolute URI: "' + f"{ self._json['subject'] }" + '"'))


        if 'aliases' in self._json:
            # is optional

            if not isinstance(self._json['aliases'], list):
                excs.append(ClaimedJrd.InvalidTypeError(self, 'Aliases not a JSON array'))
            else:
                for alias in self._json['aliases'] :
                    if not isinstance(alias, str):
                        excs.append(ClaimedJrd.InvalidTypeError(self, 'Alias not a string'))
                    elif http_https_acct_uri_parse_validate(alias) is None:
                        excs.append(ClaimedJrd.InvalidUriError(self, f'Alias not absolute URI: "{ alias }"'))

        if 'properties' in self._json:
            # is optional

            if not isinstance(self._json['properties'], dict):
                excs.append(ClaimedJrd.InvalidTypeError(self, 'Properties not a JSON object'))
            else:
                for key, value in self._json['properties'].items():
                    if not isinstance(key, str):
                        excs.append(ClaimedJrd.InvalidTypeError(self, 'Property name not a string'))
                    elif http_https_acct_uri_parse_validate(key) is None:
                        excs.append(ClaimedJrd.InvalidUriError(self, f'Property name not an absolute URI: "{ key }"'))
                    elif value is not None and not isinstance(value, str):
                        excs.append(ClaimedJrd.InvalidTypeError(self, f'Property value not string or null: key "{ key }"'))

        if 'links' in self._json:
            # is optional

            if not isinstance(self._json['links'], list):
                excs.append(ClaimedJrd.InvalidTypeError(self, 'Links not a JSON array'))
            else:
                for link in self._json['links']:
                    if not isinstance(link, dict):
                        excs.append(ClaimedJrd.InvalidTypeError(self, 'Link not a JSON object'))
                    elif 'rel' not in link:
                        excs.append(ClaimedJrd.MissingMemberError(self, 'Link missing rel property'))
                    elif not isinstance(link['rel'], str):
                        excs.append(ClaimedJrd.InvalidTypeError(self, 'Link rel value not a string'))
                    elif http_https_acct_uri_parse_validate(link['rel']) is None and not ClaimedJrd.is_registered_relation_type(link['rel']):
                        excs.append(ClaimedJrd.InvalidRelError(self, 'Link rel value not absolute URI nor registered relation type: "' + f"{link['rel']}" + '"'))

                    if 'type' in link:
                        # is optional

                        if not isinstance(link['type'], str):
                            excs.append(ClaimedJrd.InvalidTypeError(self, 'Link type not a string'))
                        elif not ClaimedJrd.is_valid_media_type(link['type']):
                            excs.append(ClaimedJrd.InvalidMediaTypeError(self, 'Link type not a valid media type: "' + f"{ link['type'] }" + '"'))

                    if 'href' in link:
                        # is optional

                        if not isinstance(link['href'], str):
                            excs.append(ClaimedJrd.InvalidTypeError(self, 'Link href not a string'))
                        elif uri_parse_validate(link['href']) is None:
                            excs.append( ClaimedJrd.InvalidUriError(self, 'Link href not a URI: "' + f"{ link['href']}" + '"'))

                    if 'titles' in link:
                        # is optional

                        if not isinstance(link['titles'], dict):
                            excs.append(ClaimedJrd.InvalidTypeError(self, 'Link titles not a JSON Object'))
                        else:
                            for key, value in link['titles']:
                                if not isinstance(key,str):
                                    excs.append(ClaimedJrd.InvalidTypeError(self, 'Link title name not a string'))
                                elif key != 'und' and rfc5646_language_tag_parse_validate(key) is None:
                                    excs.append(ClaimedJrd.InvalidLanguageTagError(self, f'Link title name not a valid language tag or "und": "{ key }"'))

                                if not value or not isinstance(value, str):
                                    excs.append(ClaimedJrd.InvalidValueError(self, 'Link title value not a non-null string: name "{ key }"'))

                    if 'properties' in link:
                        # is optional

                        if not isinstance(link['properties'], dict):
                            excs.append(ClaimedJrd.InvalidTypeError(self, 'Link properties not a JSON object'))
                        else:
                            for key, value in link['properties'].items():
                                if not isinstance(key, str):
                                    excs.append(ClaimedJrd.InvalidTypeError(self, 'Link property name not a string'))
                                elif http_https_acct_uri_parse_validate(key) is None:
                                    excs.append(ClaimedJrd.InvalidUriError(self, 'Link property name not absolute URI: "{ key }"'))

                                if value is not None and not isinstance(value, str):
                                    excs.append(ClaimedJrd.InvalidTypeError(self, 'Link property value not a string nor null. Key "{ key }"'))

        if excs:
            if len(excs) == 1:
                raise excs[0]
            else:
                raise ExceptionGroup('JRD has multiple errors', excs)


    def is_valid_link_subset(self, jrd_with_superset : 'ClaimedJrd', rels: list[str] | None = None) -> bool:
        """
        Returns true if this and the provided ClaimedJrd are identical, except that the provided jrd_with_superset
        may contain additional 'link' entries as long as they don't have a 'rel' value in set rels.
        """
        super_links = jrd_with_superset.links()
        sub_links = self.links()

        if super_links:
            if sub_links:
                if len(sub_links) > len(super_links):
                    return False

                super_position = 0
                for sub_link in sub_links:
                    found = False
                    for super_i in range(super_position, len(super_links)):
                        super_link = super_links[super_i]
                        if self._element_equals(super_link, sub_link):
                            super_position = super_i + 1
                            found = True
                            break
                        if super_link['rel'] in sub_links:
                            # should not have removed this one
                            return False
                    if not found:
                        return False

            return True # sub has none

        if sub_links:
            return False # super has none
        return True # neither has any


    def _element_equals(self, a: dict[str, Any], b: dict[str, Any]) -> bool: # pylint: disable=too-many-return-statements
        """
        Helper to compare two link elements for equality.
        """
        if len(a) != len(b):
            return False

        if a.get('rel') != b.get('rel'):
            return False

        if a.get('type') != b.get('type'):
            return False

        if a.get('href') != b.get('href'):
            return False

        if not self._dict_equals(a.get('titles'), b.get('titles')):
            return False

        if not self._dict_equals(a.get('properties'), b.get('properties')):
            return False

        return True


    def _dict_equals(self, a: dict[str,Any] | None, b: dict[str,Any] | None) -> bool: # pylint: disable=too-many-return-statements
        """
        Helper to compare two dicts for equality.
        """
        if a is None:
            if b is None:
                return True
            return False

        if b is None:
            return False

        if len(a) != len(b):
            return False

        for a_key, a_value in a.items():
            if a_key in b:
                b_value = b[a_key]
                if a_value != b_value:
                    return False
            else:
                return False

        return True


    def __str__(self):
        """
        For error messages.
        """
        return json.dumps(self._json)


@dataclass
class WebFingerQueryDiagResponse:
    http_request_response_pair: HttpRequestResponsePair
    jrd : ClaimedJrd | None # This may be an invalid jrd
    exceptions : list[Exception] = field(default_factory=list) # List of all things that were found to be wrong


    def exceptions_of_type(self, filter_by: type) -> list[Exception]:
        """
        Return only the subset of exceptions that are of type filter_by
        """
        return [ ex for ex in self.exceptions if isinstance(ex, filter_by) ]


    def not_exceptions_of_type(self, filter_by: tuple) -> list[Exception]:
        """
        Return only the subset of exceptions that are not of any of the types in filter_by
        """
        return [ ex for ex in self.exceptions if not isinstance(ex, filter_by) ]


class WebFingerDiagClient(WebFingerClient, WebDiagClient):
    """
    A Node that acts as a WebFinger client.
    """
    # Python 3.12 @override
    def perform_webfinger_query(self, resource_uri: str) -> None:
        self.diag_perform_webfinger_query(resource_uri)


    def diag_perform_webfinger_query(
        self,
        resource_uri: str,
        rels: list[str] | None = None,
        server: WebFingerServer | None = None
    ) -> WebFingerQueryDiagResponse:
        """
        Make this Node perform a WebFinger query for the provided resource_uri.
        The resource_uri must be a valid, absolute URI, such as 'acct:foo@bar.com` or
        'https://example.com/aabc' (not escaped).
        rels is an optional list of 'rel' query parameters.
        server, if given, indicates the non-default server that is supposed to perform the query
        Return the result of the query.
        """
        raise NotImplementedByNodeError(self, WebFingerDiagClient.diag_perform_webfinger_query)


    class WrongHttpStatusError(RuntimeError):
        """
        Raised when an HTTP status was obtained that was wrong for the situation.
        """
        def __init__(self, http_request_response_pair: HttpRequestResponsePair):
            self._http_request_response_pair = http_request_response_pair


        def __str__(self):
            return 'Wrong HTTP status code.' \
                   + f'\n -> { self._http_request_response_pair.response.http_status }'


    class WrongContentTypeError(RuntimeError):
        """
        Raised when payload of a content type was received that was wrong for the situation
        """
        def __init__(self, http_request_response_pair: HttpRequestResponsePair):
            self._http_request_response_pair = http_request_response_pair


        def __str__(self):
            return 'Wrong HTTP content type.' \
                   + f'\n -> "{ self._http_request_response_pair.response.content_type() }"'


class WebFingerDiagServer(WebFingerServer):
    """
    """

    # Work in progress

    # def diag_override_webfinger_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):
    #     """
    #     Instruct the server to temporarily return the overridden_json_response when the client_operation is performed.
    #     """
    #     raise NotImplementedByNodeError(self, WebFingerDiagServer.diag_override_webfinger_response)
