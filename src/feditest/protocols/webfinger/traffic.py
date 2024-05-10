"""
"""

from dataclasses import dataclass
import json
from typing import Any

from feditest.protocols.web.traffic import HttpRequestResponsePair
from feditest.utils import http_https_acct_uri_parse_validate, rfc5646_language_tag_parse_validate, uri_parse_validate


class ClaimedJrd:
    """
    The JSON structure that claims to be a JRD. This can contain any JSON because it needs to hold whatever
    claims to be a JRD, even if it is invalid. It won't try to hold data that isn't valid JSON.
    """
    def __init__(self, json_string: str):
        if json_string is None or not isinstance(json_string, str):
            raise RuntimeError()
        self._json = json.loads(json_string)


    class JrdError(RuntimeError):
        """
        Represents a problem during JRD parsing, such as syntax error.
        """
        pass # pylint: disable=unnecessary-pass


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
        Validate the correctness of the JRD. Throw Exceptions if it is not valid.
        """
        if not isinstance(self._json, dict):
            raise ClaimedJrd.InvalidTypeError(self, 'Must be a JSON object')

        for key in self._json:
            if key not in self.VALID_JRD_KEYS:
                raise ClaimedJrd.JrdError(self, f"Invalid key: {key}")

        if 'subject' in self._json:
            # is optional

            if not isinstance(self._json['subject'], str):
                raise ClaimedJrd.InvalidTypeError(self, 'Member subject must be a string')

            if http_https_acct_uri_parse_validate(self._json['subject']) is None:
                raise ClaimedJrd.InvalidUriError(self, 'Member subject must be an absolute URI')


        if 'aliases' in self._json:
            # is optional

            if not isinstance(self._json['aliases'], list):
                raise ClaimedJrd.InvalidTypeError(self, 'Member aliases must be a JSON array')

            for alias in self._json['aliases'] :
                if not isinstance(alias, str):
                    raise ClaimedJrd.InvalidTypeError(self, 'Members of the aliases array must be strings')

                if http_https_acct_uri_parse_validate(alias) is None:
                    raise ClaimedJrd.InvalidUriError(self, 'Members of aliases array must be absolute URIs')

        if 'properties' in self._json:
            # is optional

            if not isinstance(self._json['properties'], dict):
                raise ClaimedJrd.InvalidTypeError(self, 'Member properties must be a JSON object')

            for key, value in self._json['properties']:
                if not isinstance(key, str):
                    raise ClaimedJrd.InvalidTypeError(self, 'Names in the properties object must be strings')

                if http_https_acct_uri_parse_validate(key) is None:
                    raise ClaimedJrd.InvalidUriError(self, 'Names in the properties object must be absolute URIs')

                if value is not None and not isinstance(value, str):
                    raise ClaimedJrd.InvalidTypeError(self, 'Values in the properties object must be strings or null')

        if 'links' in self._json:
            # is optional

            if not isinstance(self._json['links'], list):
                raise ClaimedJrd.InvalidTypeError(self, 'Member links must be a JSON array')

            for link in self._json['links']:
                if not isinstance(link, dict):
                    raise ClaimedJrd.InvalidTypeError(self, 'Members of the links array must be JSON objects')

                if 'rel' not in link:
                    raise ClaimedJrd.MissingMemberError(self, 'All members of the links array must have a rel property')

                if not isinstance(link['rel'], str):
                    raise ClaimedJrd.InvalidTypeError(self, 'Values for the rel member in the links array must be strings')

                if http_https_acct_uri_parse_validate(link['rel']) is None and not ClaimedJrd.is_registered_relation_type(link['rel']):
                    raise ClaimedJrd.InvalidRelError(self, 'All rel entries in the links array must be a URI or a registered relation type')

                if 'type' in link:
                    # is optional

                    if not isinstance(link['type'], str):
                        raise ClaimedJrd.InvalidTypeError(self, 'Values for the type member in the links array must be strings')

                    if not ClaimedJrd.is_valid_media_type(link['type']):
                        raise ClaimedJrd.InvalidMediaTypeError(self, f'Values for the type member in the links array must be valid media types: { link["type"] }')

                if 'href' in link:
                    # is optional

                    if not isinstance(link['href'], str):
                        raise ClaimedJrd.InvalidTypeError(self, 'Values for the type member in the links array must be strings')

                    if uri_parse_validate(link['href']) is None:
                        raise ClaimedJrd.InvalidUriError(self, 'Values for the href member in the links array must be URIs')

                if 'titles' in link:
                    # is optional

                    if not isinstance(link['titles'], dict):
                        raise ClaimedJrd.InvalidTypeError(self, 'Values for the titles member in a links array mbmber must be JSON objects')

                    for key, value in link['titles']:
                        if not isinstance(key,str):
                            raise ClaimedJrd.InvalidTypeError(self, 'Names in the titles object in a links array member must be strings')

                        if key != 'und' and rfc5646_language_tag_parse_validate(key) is None:
                            raise ClaimedJrd.InvalidLanguageTagError(self, f'Names in the titles object in a links array member must be valid language tags or "und": { key }')

                        if not value or not isinstance(value, str):
                            raise ClaimedJrd.InvalidValueError(self, 'Values in the titles objects in a links array member must be non-null strings')

                if 'properties' in link:
                    # is optional

                    if not isinstance(link['properties'], dict):
                        raise ClaimedJrd.InvalidTypeError(self, 'Member properties in a links array member must be a JSON object')

                    for key, value in link['properties']:
                        if not isinstance(key, str):
                            raise ClaimedJrd.InvalidTypeError(self, 'Names in the properties object in a links array member must be strings')

                        if http_https_acct_uri_parse_validate(key) is None:
                            raise ClaimedJrd.InvalidUriError(self, 'Names in the properties object in a links array member must be absolute URIs')

                        if value is not None and not isinstance(value, str):
                            raise ClaimedJrd.InvalidTypeError(self, 'Values in the properties object in a links array member must be strings or null')


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

        for a_key, a_value in a.values():
            if a_key in b:
                b_value = b[a_key]
                if a_value != b_value:
                    return False
            return False
        return True


@dataclass
class WebFingerQueryResponse:
    http_request_response_pair: HttpRequestResponsePair
    jrd : ClaimedJrd | None
