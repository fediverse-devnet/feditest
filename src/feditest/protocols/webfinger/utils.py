"""
WebFinger testing utils
"""

from urllib.parse import quote, urlparse
from typing import Any, Type

from multidict import MultiDict
from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.description import Description

from .diag import ClaimedJrd, WebFingerQueryDiagResponse


class UnsupportedUriSchemeError(RuntimeError):
    """
    Raised when a WebFinger resource uses a scheme other than http, https, acct
    """
    def __init__(self, resource_uri: str):
        self.resource_uri = resource_uri


class CannotDetermineWebFingerHostError(RuntimeError):
    """
    Raised when the WebFinger host could not be determined.
    """
    def __init__(self, resource_uri: str):
        self.resource_uri = resource_uri


def construct_webfinger_uri_for(
    resource_uri: str,
    rels: list[str] | None = None,
    hostname: str | None = None
) -> str:
    """
    Helper method to construct the WebFinger URI from a resource URI, an optional list
    of rels to ask for, and (if given) a non-default hostname
    """
    if not hostname:
        parsed_resource_uri = urlparse(resource_uri)
        match parsed_resource_uri.scheme:
            case "acct":
                _, hostname = parsed_resource_uri.path.split(
                    "@", maxsplit=1
                )  # 1: number of splits, not number of elements

            case 'http':
                hostname = parsed_resource_uri.netloc

            case 'https':
                hostname = parsed_resource_uri.netloc

            case _:
                raise UnsupportedUriSchemeError(resource_uri)

    if not hostname:
        raise CannotDetermineWebFingerHostError(resource_uri)

    uri = f"https://{hostname}/.well-known/webfinger?resource={quote(resource_uri)}"
    if rels:
        for rel in rels:
            uri += f"&rel={ quote(rel) }"

    return uri


class RecursiveEqualToMatcher(BaseMatcher):
    """
    Custom matcher: recursively match two objects
    """
    def __init__(self, other: Any):
        self._other = other


    def _matches(self, here: Any) -> bool:
        return self._equals(here, self._other)


    def _equals(self, a: Any, b: Any):
        if a is None:
            return b is None
        if b is None:
            return False
        if type(a) is not type(b):
            return False
        if isinstance(a, (int, float, str, bool)):
            return a == b
        if isinstance(a, (list, tuple, set)):
            if len(a) != len(b):
                return False
            return all(self._equals(aa, bb) for aa, bb in zip(a, b))
        if isinstance(a, dict):
            if len(a) != len(b):
                return False
            for key in a:
                if key not in b:
                    return False
                if not self._equals(a[key], b[key]):
                    return False
            return True
        if hasattr(a, '__dict__') and hasattr(b, '__dict__'):
            return self._equals(a.__dict__, b.__dict__)
        return False # not sure what else it can be


    def describe_to(self, description: Description) -> None:
        description.append_text(f'Objects must be of the same type and recursive structure: { self._other }')


class LinkSubsetOrEqualToMatcher(BaseMatcher):
    """
    Custom matcher: decide whether this JRD is the same as the provided JRD,
    or is the same with only a subset of the link elements.
    See https://pyhamcrest.readthedocs.io/en/latest/custom_matchers.html
    """
    def __init__(self, jrd_with_superset: ClaimedJrd, rels: list[str] | None = None):
        """
        jrd_with_superset: the JRD to compare against
        rels: the rels the subset is not supposed to have stripped
        """
        self._jrd_with_superset = jrd_with_superset
        self._rels = rels or [] # that makes the code below simpler


    def _matches(self, jrd_with_subset: ClaimedJrd) -> bool:
        if self._jrd_with_superset is None:
            return False
        if jrd_with_subset is None:
            return False
        return jrd_with_subset.is_valid_link_subset(self._jrd_with_superset, self._rels)


    def describe_to(self, description: Description) -> None:
        description.append_text('Links must be the same or a subset.')
        description.append_text(f'JRD: { self._jrd_with_superset }')
        if self._rels:
            description.append_text(f'rels: { ", ".join(self._rels) }')


class MultiDictHasKeyMatcher(BaseMatcher):
    """
    Custom matcher: decide whether a MultiDict has an entry with this name.
    Does not check whether there is a value or multiple values.
    """
    def __init__(self, key: str):
        self._key = key


    def _matches(self, multi_dict: MultiDict) -> bool:
        return self._key in multi_dict


    def describe_to(self, description: Description) -> None:
        description.append_text(f'MultiDict has key: { self._key }')


class NoneExceptMatcher(BaseMatcher):
    """
    Custom matcher: decode whether an Exception (which may be an ExceptionGroup) contains
    any Exception other than the provided allowed exceptions.
    """
    def __init__(self, allowed_excs: list[Type[Exception]]):
        self._allowed_excs = allowed_excs


    def _matches(self, candidate: Exception | None ) -> bool:
        if candidate is None:
            return True
        if isinstance(candidate, ExceptionGroup):
            for cand in candidate.exceptions:
                found = False
                for allowed in self._allowed_excs:
                    if isinstance(cand, allowed):
                        found = True
                if not found:
                    return False
            return True

        for allowed in self._allowed_excs:
            if isinstance(candidate, allowed):
                return True
        return False


    def describe_to(self, description: Description) -> None:
        description.append_text(f'No exception other than: { ",".join( [ x.__name__ for x in self._allowed_excs ] ) }')


def recursive_equal_to(arg: object) -> RecursiveEqualToMatcher :
    return RecursiveEqualToMatcher(arg)


def link_subset_or_equal_to(arg: ClaimedJrd) -> LinkSubsetOrEqualToMatcher :
    return LinkSubsetOrEqualToMatcher(arg)


def multi_dict_has_key(arg: str) -> MultiDictHasKeyMatcher :
    return MultiDictHasKeyMatcher(arg)


def none_except(*allowed_excs : Type[Exception]) -> NoneExceptMatcher :
    return NoneExceptMatcher(list(allowed_excs))


def wf_error(response: WebFingerQueryDiagResponse) -> str:
    """
    Construct an error message
    """
    if not response.exceptions:
        return 'ok'

    msg = f'Accessed URI: "{ response.http_request_response_pair.request.parsed_uri.uri }":'
    for i, exc in enumerate(response.exceptions):
        msg += f'\n{ i }: { exc }'

    return msg
