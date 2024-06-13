from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ActorUriRequest(_message.Message):
    __slots__ = ("role_name",)
    ROLE_NAME_FIELD_NUMBER: _ClassVar[int]
    role_name: str
    def __init__(self, role_name: _Optional[str] = ...) -> None: ...

class ActorUriReply(_message.Message):
    __slots__ = ("actor_uri",)
    ACTOR_URI_FIELD_NUMBER: _ClassVar[int]
    actor_uri: str
    def __init__(self, actor_uri: _Optional[str] = ...) -> None: ...

class ActorFollowersUriRequest(_message.Message):
    __slots__ = ("actor_uri",)
    ACTOR_URI_FIELD_NUMBER: _ClassVar[int]
    actor_uri: str
    def __init__(self, actor_uri: _Optional[str] = ...) -> None: ...

class ActorFollowersUriReply(_message.Message):
    __slots__ = ("uri",)
    URI_FIELD_NUMBER: _ClassVar[int]
    uri: str
    def __init__(self, uri: _Optional[str] = ...) -> None: ...

class ActorFollowingUriRequest(_message.Message):
    __slots__ = ("actor_uri",)
    ACTOR_URI_FIELD_NUMBER: _ClassVar[int]
    actor_uri: str
    def __init__(self, actor_uri: _Optional[str] = ...) -> None: ...

class ActorFollowingUriReply(_message.Message):
    __slots__ = ("uri",)
    URI_FIELD_NUMBER: _ClassVar[int]
    uri: str
    def __init__(self, uri: _Optional[str] = ...) -> None: ...

class CreateObjectRequest(_message.Message):
    __slots__ = ("type", "actor_uri", "content", "inbox_kind", "to_uri")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ACTOR_URI_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    INBOX_KIND_FIELD_NUMBER: _ClassVar[int]
    TO_URI_FIELD_NUMBER: _ClassVar[int]
    type: str
    actor_uri: str
    content: str
    inbox_kind: str
    to_uri: str
    def __init__(self, type: _Optional[str] = ..., actor_uri: _Optional[str] = ..., content: _Optional[str] = ..., inbox_kind: _Optional[str] = ..., to_uri: _Optional[str] = ...) -> None: ...

class CreateObjectReply(_message.Message):
    __slots__ = ("activity_uri", "object_uri")
    ACTIVITY_URI_FIELD_NUMBER: _ClassVar[int]
    OBJECT_URI_FIELD_NUMBER: _ClassVar[int]
    activity_uri: str
    object_uri: str
    def __init__(self, activity_uri: _Optional[str] = ..., object_uri: _Optional[str] = ...) -> None: ...

class WaitForInboxObjectRequest(_message.Message):
    __slots__ = ("actor_uri", "object_uri")
    ACTOR_URI_FIELD_NUMBER: _ClassVar[int]
    OBJECT_URI_FIELD_NUMBER: _ClassVar[int]
    actor_uri: str
    object_uri: str
    def __init__(self, actor_uri: _Optional[str] = ..., object_uri: _Optional[str] = ...) -> None: ...

class WaitForInboxObjectReply(_message.Message):
    __slots__ = ("succeeded",)
    SUCCEEDED_FIELD_NUMBER: _ClassVar[int]
    succeeded: bool
    def __init__(self, succeeded: bool = ...) -> None: ...

class AnnounceObjectRequest(_message.Message):
    __slots__ = ("actor_uri", "object_uri")
    ACTOR_URI_FIELD_NUMBER: _ClassVar[int]
    OBJECT_URI_FIELD_NUMBER: _ClassVar[int]
    actor_uri: str
    object_uri: str
    def __init__(self, actor_uri: _Optional[str] = ..., object_uri: _Optional[str] = ...) -> None: ...

class AnnounceObjectReply(_message.Message):
    __slots__ = ("succeeded", "activity_uri", "object_uri")
    SUCCEEDED_FIELD_NUMBER: _ClassVar[int]
    ACTIVITY_URI_FIELD_NUMBER: _ClassVar[int]
    OBJECT_URI_FIELD_NUMBER: _ClassVar[int]
    succeeded: bool
    activity_uri: str
    object_uri: str
    def __init__(self, succeeded: bool = ..., activity_uri: _Optional[str] = ..., object_uri: _Optional[str] = ...) -> None: ...

class ReplyToObjectRequest(_message.Message):
    __slots__ = ("actor_uri", "object_uri", "content")
    ACTOR_URI_FIELD_NUMBER: _ClassVar[int]
    OBJECT_URI_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    actor_uri: str
    object_uri: str
    content: str
    def __init__(self, actor_uri: _Optional[str] = ..., object_uri: _Optional[str] = ..., content: _Optional[str] = ...) -> None: ...

class ReplyToObjectReply(_message.Message):
    __slots__ = ("succeeded", "activity_uri", "object_uri")
    SUCCEEDED_FIELD_NUMBER: _ClassVar[int]
    ACTIVITY_URI_FIELD_NUMBER: _ClassVar[int]
    OBJECT_URI_FIELD_NUMBER: _ClassVar[int]
    succeeded: bool
    activity_uri: str
    object_uri: str
    def __init__(self, succeeded: bool = ..., activity_uri: _Optional[str] = ..., object_uri: _Optional[str] = ...) -> None: ...

class FollowActorRequest(_message.Message):
    __slots__ = ("following_actor_uri", "followed_actor_uri")
    FOLLOWING_ACTOR_URI_FIELD_NUMBER: _ClassVar[int]
    FOLLOWED_ACTOR_URI_FIELD_NUMBER: _ClassVar[int]
    following_actor_uri: str
    followed_actor_uri: str
    def __init__(self, following_actor_uri: _Optional[str] = ..., followed_actor_uri: _Optional[str] = ...) -> None: ...

class FollowActorReply(_message.Message):
    __slots__ = ("accepted",)
    ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    accepted: bool
    def __init__(self, accepted: bool = ...) -> None: ...

class CollectionContainsRequest(_message.Message):
    __slots__ = ("object_uri", "collection_uri")
    OBJECT_URI_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_URI_FIELD_NUMBER: _ClassVar[int]
    object_uri: str
    collection_uri: str
    def __init__(self, object_uri: _Optional[str] = ..., collection_uri: _Optional[str] = ...) -> None: ...

class CollectionContainsReply(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: bool
    def __init__(self, result: bool = ...) -> None: ...
