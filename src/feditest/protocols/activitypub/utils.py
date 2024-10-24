"""
ActivityPub testing utils
"""

from typing import Any

from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.description import Description

from feditest.nodedrivers import Node
from feditest.utils import boolean_response_parse_validate, prompt_user_parse_validate


class MemberOfCollectionMatcher(BaseMatcher[Any]):
    """
    Custom matcher: decide whether a URI is a member of Collection identified by another URI
    """
    def __init__(self, collection_uri: str, node: Node):
        """
        collection_uri: the URI identifying the collection which to examine
        """
        self._collection_uri = collection_uri
        self._node = node


    def _matches(self, member_candidate_uri: str) -> bool:
        ret = prompt_user_parse_validate(
                f'Is "{ member_candidate_uri }" a member of the collection at URI "{ self._collection_uri }"? ',
                parse_validate=boolean_response_parse_validate)
        return ret


    def describe_to(self, description: Description) -> None:
        description.append_text('Not a member of the set')


def is_member_of_collection_at(arg: str, node: Node) -> MemberOfCollectionMatcher :
    return MemberOfCollectionMatcher(arg, node)
