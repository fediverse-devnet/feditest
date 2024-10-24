"""
"""

from abc import abstractmethod
import certifi
import json
from dataclasses import dataclass
import requests
from requests.exceptions import HTTPError
from typing import cast, Any
from urllib.parse import urlencode

from feditest.nodedrivers import (
    Account,
    AccountManager,
    DefaultAccountManager,
    NodeConfiguration,
    NodeDriver,
    NonExistingAccount,
    NotImplementedByNodeError,
    APP_PAR,
    APP_VERSION_PAR,
    HOSTNAME_PAR
)
from feditest.protocols.fediverse import (
    ROLE_ACCOUNT_FIELD,
    ROLE_NON_EXISTING_ACCOUNT_FIELD,
    USERID_ACCOUNT_FIELD,
    USERID_NON_EXISTING_ACCOUNT_FIELD,
    FediverseAccount,
    FediverseNode,
    FediverseNonExistingAccount,
    userid_validate
)
from feditest.reporting import is_trace_active, trace
from feditest.testplan import (
    InvalidAccountSpecificationException,
    TestPlanConstellationNode,
    TestPlanNodeAccountField,
    TestPlanNodeNonExistingAccountField,
    TestPlanNodeParameter
)
from feditest.utils import (
    boolean_parse_validate,
    email_validate,
    find_first_in_array,
    hostname_validate,
    prompt_user_parse_validate,
    ParsedUri,
    ParsedAcctUri
)

VERIFY_API_TLS_CERTIFICATE_PAR = TestPlanNodeParameter(
    'verify_api_tls_certificate',
    """If set to false, accessing the Mastodon API will be performed without checking TLS certificates.""",
    validate=boolean_parse_validate
)


def _oauth_token_validate(candidate: str) -> str | None:
    """
    Validate a Mastodon client API token. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    candidate = candidate.strip()
    return candidate if len(candidate)>10 else None


def _password_validate(candidate: str) -> str | None:
    """
    Validate a Mastodon password. Avoids user input errors.
    FIXME this is a wild guess and can be better.
    """
    candidate = candidate.strip()
    return candidate if len(candidate)>4 else None


EMAIL_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'email',
        """E-mail for the user on an Account. Required for accounts specified with a password (not a token) because logging into Mastodon is by e-mail address.""",
        email_validate
)
PASSWORD_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'password',
        """Password for a user. Required for accounts that also have an e-mail address and no token.""",
        _password_validate
)
OAUTH_TOKEN_ACCOUNT_FIELD = TestPlanNodeAccountField(
        'oauth_token',
        """OAuth token of a user, obtained out of band, for users not specified with e-mail address and password.""",
        _oauth_token_validate
)


def mastodon_api_invoke_get_or_delete(
    method: str,
    api_base_url: str,
    session: requests.Session,
    path: str,
    headers: dict[str,str] | None
) -> dict[str,Any]:
    method = method.lower()
    url = api_base_url + path
    real_headers = {
        'user-agent' : 'FediTest',
        'accept' : 'application/json+activity'
    }
    if headers:
        for key, value in headers.items():
            real_headers[key.lower()] = value

    if is_trace_active():
        curl = f'curl { url }'
        if method != 'GET':
            curl += f' -X { method }'
        for key, value in real_headers.items():
            curl += f' -H "{ key }: { value }"'
        trace(f'Mastodon API call as curl: { curl }')

    response_json = None
    try :
        if 'get' == method:
            response = session.get(url, headers=real_headers)
        else:
            response = session.delete(url, headers=real_headers)
        if response.status_code >= 400: # taken from requests' raise_for_status()
            raise HTTPError(f'HTTP status { response.status_code }: { response.content.decode("utf-8") }', response=response)
        response_json = response.json()
        return response_json

    finally:
        if response_json:
            trace(f'Mastodon API call returns { response }: { json.dumps(response_json) }')
        else:
            trace(f'Mastodon API call returns { response }: Not a JSON response: { response.text }')


def mastodon_api_invoke_post_or_put(
    method: str,
    api_base_url: str,
    session: requests.Session,
    path: str,
    args: dict[str,str] | None = None,
    headers: dict[str,str] | None = None
) -> dict[str,Any]:
    method = method.lower()
    url = api_base_url + path
    real_headers = {
        'user-agent' : 'FediTest',
        'accept' : 'application/json+activity'
    }
    if headers:
        for key, value in headers.items():
            real_headers[key.lower()] = value

    if is_trace_active():
        curl = f'curl -X { method } { url }'
        for key, value in real_headers.items():
            curl += f' -H "{ key }: { value }"'
        if args:
            for key, value in args.items():
                curl += f' -F "{ key }={ value }"'
        trace(f'Mastodon API call as curl: { curl }')

    response_json = None
    try :
        if 'post' == method:
            response = session.post(url, data=args, headers=real_headers)
        else:
            response = session.put(url, data=args, headers=real_headers)
        if response.status_code >= 400: # taken from requests' raise_for_status()
            raise HTTPError(f'HTTP status { response.status_code }: { response.content.decode("utf-8") }', response=response)
        response_json = response.json()
        return response_json

    finally:
        if response_json:
            trace(f'Mastodon API call returns { response }: { json.dumps(response_json) }')
        else:
            trace(f'Mastodon API call returns { response }: Not a JSON response: { response.text }')


@dataclass
class MastodonOAuthApp:
    """
    Captures what we know about the Mastodon OAuth "app" we create to interact with our Mastodon instance.
    """
    client_id : str
    client_secret : str
    api_base_url : str
    session : requests.Session # Use this session which has the right CA certs

    @staticmethod
    def create(api_base_url: str, session: requests.Session) -> 'MastodonOAuthApp':
        args = {
            'client_name' : 'feditest',
            'redirect_uris' : 'urn:ietf:wg:oauth:2.0:oob',
            'scopes' : 'read write follow push',
            'website' : 'https://feditest.org/'

        }
        result = mastodon_api_invoke_post_or_put('POST', api_base_url, session, '/api/v1/apps', args=args)
        client_id = result['client_id']
        client_secret = result['client_secret']

        trace(f'Created Mastodon app with client_id="{ client_id }", client_secret="{ client_secret }".')
        return MastodonOAuthApp(client_id, client_secret, api_base_url, session)


class AuthenticatedMastodonApiClient:
    def __init__(self, app: MastodonOAuthApp, account: 'AccountOnNodeWithMastodonAPI', bearer_token: str):
        """
        Represents an authenticated client to a Mastodon instance, for client acct_uri with bearer_token
        """
        self._app = app
        self._account = account
        self._auth_header = {
            'Authorization' : 'Bearer ' + bearer_token
        }


    def http_get(self, path: str) -> Any:
        return mastodon_api_invoke_get_or_delete('GET', self._app.api_base_url, self._app.session, path, self._auth_header)


    def http_post(self, path: str, args: dict[str,str] | None = None) -> Any:
        return mastodon_api_invoke_post_or_put('POST', self._app.api_base_url, self._app.session, path, args=args, headers=self._auth_header)


    def http_put(self, path: str, args: dict[str,str] | None = None) -> Any:
        return mastodon_api_invoke_post_or_put('PUT', self._app.api_base_url, self._app.session, path, args=args, headers=self._auth_header)


    def http_delete(self, path: str) -> Any:
        return mastodon_api_invoke_get_or_delete('DELETE', self._app.api_base_url, self._app.session, path, self._auth_header)


    def make_follow(self, to_follow_actor_acct_uri: str) -> dict[str, str]:
        if to_follow_account := self._find_account_dict_by_other_actor_acct_uri(to_follow_actor_acct_uri):
            local_to_follow_account_id = to_follow_account['id']
            response = self.http_post(f'/api/v1/accounts/{ local_to_follow_account_id }/follow')
            return response
        raise ValueError(f'Cannot find account for Actor on { self }: "{ to_follow_actor_acct_uri }"')


    def make_unfollow(self, following_actor_acct_uri: str) -> dict[str,str]:
        if following_account := self._find_account_dict_by_other_actor_acct_uri(following_actor_acct_uri):
            following_account_id = following_account['id']
            response = self.http_post(f'/api/v1/accounts/{ following_account_id }/unfollow')
            return response
        raise ValueError(f'Account not found with Actor URI: { following_actor_acct_uri }')


    def actor_is_following_actor(self, leader_actor_acct_uri: str) -> bool:
        this_account_id = self._account.internal_userid
        response = self.http_get(f'/api/v1/accounts/{ this_account_id }/following')
        found = find_first_in_array(response, lambda r: r['acct'] == leader_actor_acct_uri[5:]) # remove acct:
        return found is not None


    def actor_is_followed_by_actor(self, follower_actor_acct_uri: str) -> bool:
        this_account_id = self._account.internal_userid
        response = self.http_get(f'/api/v1/accounts/{ this_account_id }/followers')
        found = find_first_in_array(response, lambda r: r['acct'] == follower_actor_acct_uri[5:]) # remove acct:
        return found is not None


    def make_create_note(self, content: str, deliver_to: list[str] | None = None) -> dict[str, str]:
        if deliver_to: # The only way we can address specific accounts in Mastodon
            for to in deliver_to:
                if to_account := self._find_account_dict_by_other_actor_acct_uri(to):
                    to_handle = f'@{to_account["acct"]}'
                    content += f' {to_handle}'
                else:
                    raise ValueError(f'Cannot find account for Actor on { self }: "{ to }"')

        args = {
            'status' : content
        }
        response = self.http_post('/api/v1/statuses', args)
        return response


    def update_note(self, note_uri: str, new_content: str) -> dict[str, Any]:
        if note := self._find_note_dict_by_uri(note_uri):
            note_id = note['id']
            args = {
                'status' : new_content
            }
            response = self.http_put(f'/api/v1/statuses/{ note_id }', args)
            return response
        raise ValueError(f'Cannot find Note on { self }: "{ note_uri }"')


    def delete_object(self, note_uri: str) -> None:
        if note := self._find_note_dict_by_uri(note_uri):
            note_id = note['id']
            response = self.http_delete(f'/api/v1/statuses/{ note_id }')
            return response
        raise ValueError(f'Cannot find Note on { self }: "{ note_uri }"')


    def make_reply_note(self, to_be_replied_to_object_uri: str, reply_content: str) -> dict[str, str]:
        if local_note := self._find_note_dict_by_uri(to_be_replied_to_object_uri):
            local_note_id = local_note['id']

            args = {
                'status' : reply_content,
                'in_reply_to_id' : local_note_id
            }
            response = self.http_post('/api/v1/statuses', args)
            return response
        raise ValueError(f'Cannot find Note on { self }: "{ to_be_replied_to_object_uri }"')


    def like_object(self, object_uri: str) -> None:
        if note := self._find_note_dict_by_uri(object_uri):
            note_id = note['id']
            response = self.http_post(f'/api/v1/statuses/{ note_id }/favourite')
            return response
        raise ValueError(f'Cannot find Note on { self }: "{ object_uri }"')


    def unlike_object(self, object_uri: str) -> None:
        if note := self._find_note_dict_by_uri(object_uri):
            note_id = note['id']
            response = self.http_post(f'/api/v1/statuses/{ note_id }/unfavourite')
            return response
        raise ValueError(f'Cannot find Note on { self }: "{ object_uri }"')


    def announce_object(self, object_uri: str) -> None:
        if note := self._find_note_dict_by_uri(object_uri):
            note_id = note['id']
            response = self.http_post(f'/api/v1/statuses/{ note_id }/reblog')
            return response
        raise ValueError(f'Cannot find Note on { self }: "{ object_uri }"')


    def unannounce_object(self, object_uri: str) -> None:
        if note := self._find_note_dict_by_uri(object_uri):
            note_id = note['id']
            response = self.http_post(f'/api/v1/statuses/{ note_id }/unreblog')
            return response
        raise ValueError(f'Cannot find Note on { self }: "{ object_uri }"')


    def actor_has_received_object(self,  object_uri: str) -> dict[str, Any]:
        # Depending on how the Note is addressed and follow status, Mastodon puts it into the Home timeline or only
        # into notifications.
        # Check for it in the home timeline.
        elements = self.http_get('/api/v1/timelines/home')
        #   Home timeline first case: a post was created by an account we follow
        response = find_first_in_array(elements, lambda s: s['uri'] == object_uri)
        if not response:
            #   Home timeline second case: an announce/boost was created by an account we follow -- need to look for the original URI
            if reblog_response := find_first_in_array(elements, lambda s: 'reblog' in s and s['reblog'] and 'uri' in s['reblog'] and s['reblog']['uri'] == object_uri) :
                response = reblog_response['reblog']
        if not response:
            # Check for it in notifications: mentions arrive here
            elements = self.http_get('/api/v1/notifications')
            # s['status'] exists for some things in notifications, but not others (such as "follow")
            if notifications_response := find_first_in_array(elements, lambda s: 'status' in s and s['status']['uri'] == object_uri) :
                response = notifications_response['status']
        return response


    def note_dict(self, note_uri: str) -> dict[str, Any]:
        if note := self._find_note_dict_by_uri(note_uri):
            return note
        raise ValueError(f'Cannot find Note on { self }: "{ note_uri }"')


    def object_context(self, object_uri: str) -> dict[str,Any]:
        if obj := self._find_note_dict_by_uri(object_uri):
            obj_id = obj['id']
            response = self.http_get(f'/api/v1/statuses/{ obj_id }/context')
            return response
        raise ValueError(f'Cannot find object on { self }: "{ object_uri }"')


    def object_likers(self, object_uri: str) -> list[dict[str, Any]]:
        if obj := self._find_note_dict_by_uri(object_uri):
            obj_id = obj['id']
            response = self.http_get(f'/api/v1/statuses/{ obj_id }/favourited_by')
            return response
        raise ValueError(f'Cannot find object on { self }: "{ object_uri }"')


    def object_announcers(self, object_uri: str) -> list[dict[str, Any]]:
        if obj := self._find_note_dict_by_uri(object_uri):
            obj_id = obj['id']
            response = self.http_get(f'/api/v1/statuses/{ obj_id }/reblogged_by')
            return response
        raise ValueError(f'Cannot find object on { self }: "{ object_uri }"')


    def account_dict(self) -> dict[str, Any]:
        response = self.http_get('/api/v1/accounts/verify_credentials')
        return response


    def delete_all_followers(self) -> None:
        this_account_id = self._account.internal_userid
        while True:
            response = self.http_get(f'/api/v1/accounts/{ this_account_id }/followers')
            if len(response) == 0:
                return

            for follower_dict in response:
                follower_id = follower_dict['id']
                self.http_post(f'/api/v1/accounts/{ follower_id }/unfollow')


    def delete_all_following(self) -> None:
        this_account_id = self._account.internal_userid
        while True:
            response = self.http_get(f'/api/v1/accounts/{ this_account_id }/following')
            if len(response) == 0:
                return

            for following_dict in response:
                following_id = following_dict['id']
                self.http_post(f'/api/v1/accounts/{ following_id }/remove_from_followers')


    def delete_all_statuses(self) -> None:
        while True:
            response = self.http_get('/api/v1/statuses')
            if len(response) == 0:
                return

            for status_dict in response:
                status_id = status_dict['id']
                self.http_post(f'/api/v1/statuses/{ status_id }')


    def _find_account_dict_by_other_actor_acct_uri(self, other_actor_acct_uri: str) -> dict[str,Any]:
        """
        Find the account info for another Actor with
        other_actor_acct_uri, or None.
        """
        # Search for @foo@bar.com, not acct:foo@bar.com or foo@bar.com
        handle_without_at = other_actor_acct_uri.replace('acct:', '')
        handle_with_at = '@' + handle_without_at

        args = {
            'q' : handle_with_at,
            'resolve' : 1,
            'type' : 'accounts'
        }
        results = self.http_get('/api/v2/search?' + urlencode(args))

        # Mastodon has the foo@bar.com in the 'acct' field
        ret = find_first_in_array(results.get('accounts'), lambda b: b['acct'] == handle_without_at)
        if isinstance(ret, dict):
            return cast(dict[str,Any], ret)
        raise ValueError(f'Unexpected type: { ret }')


    def _find_note_dict_by_uri(self, uri: str) -> dict[str,Any] | None:
        """
        Find a the dict for a status, or None.
        """
        args = {
            'q' : uri,
            'resolve' : 1,
            'type' : 'statuses'
        }
        results = self.http_get('/api/v2/search?' + urlencode(args))

        ret = find_first_in_array(results.get('statuses'), lambda b: b['uri'] == uri)
        if ret is None:
            return None
        if isinstance(ret, dict):
            return cast(dict[str,Any], ret)
        raise ValueError(f'Unexpected type: { ret }')


class AccountOnNodeWithMastodonAPI(FediverseAccount): # this is intended to be abstract
    def __init__(self, role: str | None, userid: str):
        super().__init__(role, userid)
        self._account_dict : dict[str, Any] | None = None


    @property
    def account_dict(self) -> dict[str, Any]:
        if self._account_dict is None:
            self._account_dict = self.mastodon_client.account_dict()
        return self._account_dict

    @property
    def internal_userid(self) -> int:
        return self.account_dict['id']


    @property
    @abstractmethod
    def mastodon_client(self) -> AuthenticatedMastodonApiClient:
        ...


class MastodonAccount(AccountOnNodeWithMastodonAPI): # this is intended to be abstract
    @staticmethod
    def create_from_account_info_in_testplan(account_info_in_testplan: dict[str, str | None], context_msg: str = ''):
        """
        Parses the information provided in an "account" dict of TestPlanConstellationNode
        """
        userid = USERID_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, context_msg)
        role = ROLE_ACCOUNT_FIELD.get_validate_from(account_info_in_testplan, context_msg)
        oauth_token = OAUTH_TOKEN_ACCOUNT_FIELD.get_validate_from(account_info_in_testplan, context_msg)

        if oauth_token:
            if EMAIL_ACCOUNT_FIELD.name in account_info_in_testplan:
                raise InvalidAccountSpecificationException(
                    account_info_in_testplan,
                    f'Specify { OAUTH_TOKEN_ACCOUNT_FIELD.name } or { EMAIL_ACCOUNT_FIELD.name }, not both.')
            if PASSWORD_ACCOUNT_FIELD.name in account_info_in_testplan:
                raise InvalidAccountSpecificationException(
                    account_info_in_testplan,
                    f'Specify { OAUTH_TOKEN_ACCOUNT_FIELD.name } or { PASSWORD_ACCOUNT_FIELD.name }, not both.')
            return MastodonOAuthTokenAccount(role, userid, oauth_token)

        email = EMAIL_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, context_msg)
        password = PASSWORD_ACCOUNT_FIELD.get_validate_from_or_raise(account_info_in_testplan, context_msg)
        return MastodonUserPasswordAccount(role, userid, password, email)


class MastodonUserPasswordAccount(MastodonAccount):
    def __init__(self, role: str | None, username: str, password: str, email: str):
        super().__init__(role, username)
        self._password = password
        self._email = email
        self._mastodon_client: AuthenticatedMastodonApiClient | None = None # Allocated as needed


    # Python 3.12 @override
    @property
    def mastodon_client(self) -> AuthenticatedMastodonApiClient:
        if self._mastodon_client is None:
            node = cast(NodeWithMastodonAPI, self._node)
            oauth_app = node._obtain_mastodon_oauth_app()
            trace(f'Logging into Mastodon at "{ oauth_app.api_base_url }" as "{ self._email }" with password.')

            args = {
                'username' : self._email,
                'password' : self._password,
                'redirect_uri' : 'urn:ietf:wg:oauth:2.0:oob',
                'grant_type' : 'password',
                'client_id' : oauth_app.client_id,
                'client_secret': oauth_app.client_secret,
                'scope': 'read write follow push'
            }
            result = mastodon_api_invoke_post_or_put('POST', oauth_app.api_base_url, oauth_app.session, '/oauth/token', args=args)
            token = result['access_token']
            self._mastodon_client = AuthenticatedMastodonApiClient(oauth_app, self, token)
        return self._mastodon_client


class MastodonOAuthTokenAccount(MastodonAccount):
    """
    Compare with WordPressAccount.
    """
    def __init__(self, role: str | None, userid: str, oauth_token: str):
        super().__init__(role, userid)
        self._oauth_token = oauth_token
        self._mastodon_client: AuthenticatedMastodonApiClient | None = None # Allocated as needed


    # Python 3.12 @override
    @property
    def mastodon_client(self) -> AuthenticatedMastodonApiClient:
        if self._mastodon_client is None:
            node = cast(NodeWithMastodonAPI, self._node)
            oauth_app = node._obtain_mastodon_oauth_app()
            trace(f'Logging into Mastodon at "{ oauth_app.api_base_url }" with userid "{ self.userid }" with OAuth token.')
            self._mastodon_client = AuthenticatedMastodonApiClient(oauth_app, self, self._oauth_token)
        return self._mastodon_client


class NodeWithMastodonApiConfiguration(NodeConfiguration):
    def __init__(self,
        node_driver: 'NodeDriver',
        app: str,
        app_version: str | None = None,
        hostname: str | None = None,
        start_delay: float = 0.0,
        verify_tls_certificate: bool = True
    ):
        super().__init__(node_driver=node_driver, app=app, app_version=app_version, hostname=hostname, start_delay=start_delay)
        self._verify_tls_certificate = verify_tls_certificate


    @property
    def verify_tls_certificate(self) -> bool:
        return self._verify_tls_certificate


class NodeWithMastodonAPI(FediverseNode):
    """
    Any Node that supports the Mastodon API. This will be subtyped into things like
    * MastodonNode
    * WordPressPlusAccessoriesNode
    ... so they can add whatever is specific to their implementation.

    This implementation assumes that there is a single client API access token
    (which lets us act as a single user) and there are no tests that require
    us to have multiple accounts that we can act as, on the same node.
    """
    def __init__(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager, auto_accept_follow: bool = True):
        super().__init__(rolename, config, account_manager)

        self._mastodon_oauth_app : MastodonOAuthApp | None = None
        # Information we have about the OAuth "app" we we create to interact with a Mastodon instance.
        # Allocated when needed, so our custom certificate authority has been created before this is used.
        self._requests_session : requests.Session | None = None
        # The request.Session with the custom certificate authority set as verifier.
        # Allocated when needed, so our custom certificate authority has been created before this is used.


# From FediverseNode

    # Python 3.12 @override
    def obtain_actor_acct_uri(self, rolename: str | None = None) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        account = cast(MastodonAccount, account_manager.obtain_account_by_role(rolename))
        return account.actor_acct_uri


    # Python 3.12 @override
    def make_follow(self, actor_acct_uri: str, to_follow_actor_acct_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        mastodon_client.make_follow(to_follow_actor_acct_uri)
        self._run_poor_mans_cron()


    # Python 3.12 @override
    def set_auto_accept_follow(self, actor_acct_uri: str, auto_accept_follow: bool = True) -> None:
        if auto_accept_follow:
            return # Default for Mastodon

        raise NotImplementedByNodeError(self, NodeWithMastodonAPI.set_auto_accept_follow) # Can't find an API call for this


    # Python 3.12 @override
    def make_follow_accept(self, actor_acct_uri: str, follower_actor_acct_uri: str) -> None:
        super().make_follow_accept(actor_acct_uri, follower_actor_acct_uri) # FIXME


    # Python 3.12 @override
    def make_follow_reject(self, actor_acct_uri: str, follower_actor_acct_uri: str) -> None:
        super().make_follow_reject(actor_acct_uri, follower_actor_acct_uri) # FIXME


    # Python 3.12 @override
    def make_unfollow(self, actor_acct_uri: str, following_actor_acct_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        mastodon_client.make_unfollow(following_actor_acct_uri)
        self._run_poor_mans_cron()


   # Python 3.12 @override
    def actor_is_following_actor(self, actor_acct_uri: str, leader_actor_acct_uri: str) -> bool:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        return mastodon_client.actor_is_following_actor(leader_actor_acct_uri)


    # Python 3.12 @override
    def actor_is_followed_by_actor(self, actor_acct_uri: str, follower_actor_acct_uri: str) -> bool:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        return mastodon_client.actor_is_followed_by_actor(follower_actor_acct_uri)


    # Python 3.12 @override
    def make_create_note(self, actor_acct_uri: str, content: str, deliver_to: list[str] | None = None) -> str:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        response = mastodon_client.make_create_note(content, deliver_to)
        self._run_poor_mans_cron()
        return response['uri']


    # Python 3.12 @override
    def update_note(self, actor_acct_uri: str, note_uri: str, new_content: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        mastodon_client.update_note(note_uri, new_content)
        self._run_poor_mans_cron()


    # Python 3.12 @override
    def delete_object(self, actor_acct_uri: str, object_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        mastodon_client.delete_object(object_uri)
        self._run_poor_mans_cron()


    # Python 3.12 @override
    def make_reply_note(self, actor_acct_uri: str, to_be_replied_to_object_uri: str, reply_content: str) -> str:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        response = mastodon_client.make_reply_note(to_be_replied_to_object_uri, reply_content)
        self._run_poor_mans_cron()
        return response['uri']


    # Python 3.12 @override
    def like_object(self, actor_acct_uri: str, object_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        mastodon_client.like_object(object_uri)
        self._run_poor_mans_cron()


    # Python 3.12 @override
    def unlike_object(self, actor_acct_uri: str, object_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        mastodon_client.unlike_object(object_uri)
        self._run_poor_mans_cron()


    # Python 3.12 @override
    def announce_object(self, actor_acct_uri: str, object_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        mastodon_client.announce_object(object_uri)
        self._run_poor_mans_cron()


    # Python 3.12 @override
    def unannounce_object(self, actor_acct_uri: str, object_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        mastodon_client.unannounce_object(object_uri)
        self._run_poor_mans_cron()


   # Python 3.12 @override
    def actor_has_received_object(self, actor_acct_uri: str, object_uri: str) -> str | None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        response = mastodon_client.actor_has_received_object(object_uri)
        if response:
            return response['content']
        return None


    # Python 3.12 @override
    def note_content(self, actor_acct_uri: str, note_uri: str) -> str | None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        response = mastodon_client.note_dict(note_uri)
        if response:
            return cast(str, response['content'])
        return None


    # Python 3.12 @override
    def object_author(self, actor_acct_uri: str, object_uri: str) -> str | None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        response = mastodon_client.note_dict(object_uri)
        return cast(str, response['author']['acct'])


    # Python 3.12 @override
    def direct_replies_to_object(self, actor_acct_uri: str, object_uri: str) -> list[str]:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        response = mastodon_client.object_context(object_uri)
        ret = [ d['uri'] for d in response['descendants']]
        return ret


    # Python 3.12 @override
    def object_likers(self, actor_acct_uri: str, object_uri: str) -> list[str]:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        response = mastodon_client.object_likers(object_uri)
        ret = [ 'acct:' + x['acct'] for x in response ]
        return ret


    # Python 3.12 @override
    def object_announcers(self, actor_acct_uri: str, object_uri: str) -> list[str]:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        response = mastodon_client.object_announcers(object_uri)
        ret = [ 'acct:' + x['acct'] for x in response ]
        return ret


# From ActivityPubNode

    # Python 3.12 @override
    def obtain_actor_document_uri(self, rolename: str | None = None) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        account = cast(MastodonAccount, account_manager.obtain_account_by_role(rolename))
        return account.actor_acct_uri

    # Not implemented:
    # def obtain_followers_collection_uri(self, actor_acct_uri: str) -> str:
    # def obtain_following_collection_uri(self, actor_acct_uri: str) -> str:

    # Python 3.12 @override

    # Work in progress

    # def assert_member_of_collection_at(
    #     self,
    #     candidate_member_uri: str,
    #     collection_uri: str,
    #     spec_level: SpecLevel | None = None,
    #     interop_level: InteropLevel | None= None
    # ):
    #     collection = AnyObject(collection_uri).as_collection()
    #     if not collection.contains_item_with_id(candidate_member_uri):
    #         raise AssertionFailure(
    #             spec_level or SpecLevel.UNSPECIFIED,
    #             interop_level or InteropLevel.UNKNOWN,
    #             f"Node { self }: {candidate_member_uri} not in {collection_uri}")


    # # Python 3.12 @override
    # def assert_not_member_of_collection_at(
    #     self,
    #     candidate_member_uri: str,
    #     collection_uri: str,
    #     spec_level: SpecLevel | None = None,
    #     interop_level: InteropLevel | None= None
    # ):
    #     collection = AnyObject(collection_uri).as_collection()
    #     if collection.contains_item_with_id(candidate_member_uri):
    #         raise AssertionFailure(
    #             spec_level or SpecLevel.UNSPECIFIED,
    #             interop_level or InteropLevel.UNKNOWN,
    #             f"Node { self }: {candidate_member_uri} must not be in {collection_uri}")

# From WebFingerServer

    # Python 3.12 @override
    def obtain_account_identifier(self, rolename: str | None = None) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        account = cast(MastodonAccount, account_manager.obtain_account_by_role(rolename))
        return account.actor_acct_uri


    # Python 3.12 @override
    def obtain_non_existing_account_identifier(self, rolename: str | None = None ) -> str:
        account_manager = cast(AccountManager, self._account_manager)
        non_account = cast(FediverseNonExistingAccount, account_manager.obtain_non_existing_account_by_role(rolename))
        return non_account.actor_acct_uri

    # Not implemented:
    # def obtain_account_identifier_requiring_percent_encoding(self, rolename: str | None = None) -> str:
    # def override_webfinger_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):

# From WebServer

    # Not implemented:
    # def transaction(self, code: Callable[[],None]) -> WebServerLog:
    # def override_http_response(self, client_operation: Callable[[],Any], overridden_json_response: Any):

# From Node

    # Python 3.12 @override
    def provision_account_for_role(self, role: str | None = None) -> Account | None:
        context_msg = f'Mastodon Node { self }: '
        userid = prompt_user_parse_validate(
                context_msg
                + f' provide the userid of an existing account for account role "{ role }" (node account field "{ USERID_ACCOUNT_FIELD.name }"): ',
                parse_validate=userid_validate)
        password = prompt_user_parse_validate(
                context_msg
                + f' provide the password for account "{ userid }", account role "{ role }" (node account field "{ PASSWORD_ACCOUNT_FIELD.name }"): ',
                parse_validate=_password_validate)
        email = prompt_user_parse_validate(
                context_msg
                + f' provide the email for account "{ userid }", account role "{ role }" (node account field "{ EMAIL_ACCOUNT_FIELD.name }"): ',
                parse_validate=_password_validate)

        return MastodonUserPasswordAccount(role, userid, password, email)


    def provision_non_existing_account_for_role(self, role: str | None = None) -> NonExistingAccount | None:
        context_msg = f'Mastodon Node { self }: '
        userid = prompt_user_parse_validate(
                context_msg
                + f' provide the userid of a non-existing account for account role "{ role }" (node non_existing_account field "{ USERID_NON_EXISTING_ACCOUNT_FIELD.name }"): ',
                parse_validate=userid_validate)

        return FediverseNonExistingAccount(role, userid)

# Test support

    def delete_all_followers_of(self, actor_acct_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        mastodon_client.delete_all_followers()
        self._run_poor_mans_cron()


    def delete_all_following_of(self, actor_acct_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        mastodon_client.delete_all_following()
        self._run_poor_mans_cron()


    def delete_all_statuses_by(self, actor_acct_uri: str) -> None:
        mastodon_client = self._get_mastodon_client_by_actor_acct_uri(actor_acct_uri)
        mastodon_client.delete_all_statuses()
        self._run_poor_mans_cron()

# Internal implementation helpers

    def _obtain_requests_session(self) -> requests.Session:
        if self._requests_session is None:
            self._requests_session = requests.Session()
            config = cast(NodeWithMastodonApiConfiguration, self.config)
            if config.verify_tls_certificate:
                self._requests_session.verify = certifi.where() # force re-read of cacert file, which the requests library reads upon first import
            else:
                self._requests_session.verify = None
        return self._requests_session


    def _obtain_mastodon_oauth_app(self) -> MastodonOAuthApp:
        session = self._obtain_requests_session()
        if not self._mastodon_oauth_app:
            self._mastodon_oauth_app = MastodonOAuthApp.create(f'https://{ self.hostname}', session)
        return self._mastodon_oauth_app


    def _get_account_by_actor_acct_uri(self, actor_acct_uri: str) -> MastodonAccount | None:
        """
        Convenience method to get the Account that goes with this actor URI
        """
        userid = self._actor_acct_uri_to_userid(actor_acct_uri)
        if not userid:
            raise ValueError(f'Cannot find Actor on { self }: "{ actor_acct_uri }"')

        ret = self._account_manager.get_account_by_match(lambda candidate: isinstance(candidate, AccountOnNodeWithMastodonAPI) and candidate.userid == userid )
        return cast(MastodonAccount | None, ret)


    def _get_mastodon_client_by_actor_acct_uri(self, actor_acct_uri: str) -> AuthenticatedMastodonApiClient:
        """
        Convenience method to get the instance of the Mastodon client object for a given actor URI.
        """
        account = self._get_account_by_actor_acct_uri(actor_acct_uri)
        if account is None:
            raise Exception(f'On Node { self }, failed to find account with for "{ actor_acct_uri }".')

        return account.mastodon_client


    def _actor_acct_uri_to_userid(self, actor_acct_uri: str) -> str:
        """
        The algorithm by which this application maps userids to ActivityPub actor handles in reverse.
        """
        parsed = ParsedUri.parse(actor_acct_uri)
        if isinstance(parsed, ParsedAcctUri):
            return parsed.user
        raise ValueError(f'Not an acct: URI: { actor_acct_uri }')


    def _run_poor_mans_cron(self) -> None:
        """
        This method is invoked after each operation that may need to push an activity to another node.
        By default, this does nothing: Mastodon itself does not need it, it has a separate queuing daemon.
        But WordPress wants to do it on an HTTP request; so we give it the opportunity to override this.
        """
        pass


class MastodonNode(NodeWithMastodonAPI):
    pass


class MastodonSaasNodeDriver(NodeDriver):
    """
    Create a Mastodon Node that already runs as SaaS
    """
    # Python 3.12 @override
    @staticmethod
    def test_plan_node_parameters() -> list[TestPlanNodeParameter]:
        return [ APP_PAR, APP_VERSION_PAR, HOSTNAME_PAR, VERIFY_API_TLS_CERTIFICATE_PAR ]


    # Python 3.12 @override
    @staticmethod
    def test_plan_node_account_fields() -> list[TestPlanNodeAccountField]:
        return [ USERID_ACCOUNT_FIELD, EMAIL_ACCOUNT_FIELD, PASSWORD_ACCOUNT_FIELD, OAUTH_TOKEN_ACCOUNT_FIELD, ROLE_ACCOUNT_FIELD ]


    # Python 3.12 @override
    @staticmethod
    def test_plan_node_non_existing_account_fields() -> list[TestPlanNodeNonExistingAccountField]:
        return [ USERID_NON_EXISTING_ACCOUNT_FIELD, ROLE_NON_EXISTING_ACCOUNT_FIELD ]


    # Python 3.12 @override
    def create_configuration_account_manager(self, rolename: str, test_plan_node: TestPlanConstellationNode) -> tuple[NodeConfiguration, AccountManager | None]:
        app = test_plan_node.parameter_or_raise(APP_PAR, { APP_PAR.name:  'Mastodon' }) # Let user give a more descriptive name if they want to
        app_version = test_plan_node.parameter(APP_VERSION_PAR)
        hostname = test_plan_node.parameter_or_raise(HOSTNAME_PAR)
        verify_tls_certificate = test_plan_node.parameter_or_raise(VERIFY_API_TLS_CERTIFICATE_PAR, { VERIFY_API_TLS_CERTIFICATE_PAR.name: 'true' })

        if not hostname:
            hostname = prompt_user_parse_validate(
                    f'Enter the hostname for the Mastodon Node of constellation role "{ rolename }" (node parameter "hostname"): ',
                    parse_validate=hostname_validate)

        accounts : list[Account] = []
        if test_plan_node.accounts:
            for index, account_info in enumerate(test_plan_node.accounts):
                accounts.append(MastodonAccount.create_from_account_info_in_testplan(
                        account_info,
                        f'Constellation role "{ rolename }", NodeDriver "{ self }, Account { index }: '))

        non_existing_accounts : list[NonExistingAccount] = []
        if test_plan_node.non_existing_accounts:
            for index, non_existing_account_info in enumerate(test_plan_node.non_existing_accounts):
                non_existing_accounts.append(FediverseNonExistingAccount.create_from_non_existing_account_info_in_testplan(
                        non_existing_account_info,
                        f'Constellation role "{ rolename }", NodeDriver "{ self }, Non-existing account { index }: '))

        return (
            NodeWithMastodonApiConfiguration(
                node_driver=self,
                app=cast(str, app),
                app_version=cast(str, app_version),
                hostname=hostname,
                verify_tls_certificate=verify_tls_certificate
            ),
            DefaultAccountManager(accounts, non_existing_accounts)
        )


    # Python 3.12 @override
    def _provision_node(self, rolename: str, config: NodeConfiguration, account_manager: AccountManager | None) -> FediverseNode:
        return MastodonNode(rolename, config, cast(AccountManager, account_manager))
