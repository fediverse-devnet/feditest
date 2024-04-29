"""
Webfinger testing utils
"""

from multidict import MultiDict
from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.description import Description

from feditest.protocols.webfinger.traffic import ClaimedJrd

class LinkSubsetOrEqualsToMatcher(BaseMatcher):
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
        return jrd_with_subset.is_valid_link_subset(self._jrd_with_superset, self._rels)


    def describe_to(self, description: Description) -> None:
        description.append_text('Links must be the same or a subset')


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


def link_subset_or_equal_to(arg: ClaimedJrd) -> LinkSubsetOrEqualsToMatcher :
    return LinkSubsetOrEqualsToMatcher(arg)


def multi_dict_has_key(arg: str) -> MultiDictHasKeyMatcher :
    return MultiDictHasKeyMatcher(arg)
