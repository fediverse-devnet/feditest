"""
Functionality that may be shared by several WebFinger Node implementations.
"""
from typing import cast

from feditest.protocols.web.diag import HttpRequest, HttpRequestResponsePair, WebDiagClient
from feditest.protocols.webfinger import WebFingerServer
from feditest.protocols.webfinger.diag import ClaimedJrd, WebFingerDiagClient
from feditest.protocols.webfinger.utils import construct_webfinger_uri_for, WebFingerQueryDiagResponse
from feditest.utils import ParsedUri


class AbstractWebFingerDiagClient(WebFingerDiagClient):
    # Python 3.12 @override
    def diag_perform_webfinger_query(
        self,
        resource_uri: str,
        rels: list[str] | None = None,
        server: WebFingerServer | None = None
    ) -> WebFingerQueryDiagResponse:
        query_url = construct_webfinger_uri_for(resource_uri, rels, server.hostname() if server else None )
        parsed_uri = ParsedUri.parse(query_url)
        if not parsed_uri:
            raise ValueError('Not a valid URI:', query_url) # can't avoid this
        first_request = HttpRequest(parsed_uri)
        current_request = first_request
        pair : HttpRequestResponsePair | None = None
        for redirect_count in range(10, 0, -1):
            pair = self.http(current_request)
            if pair.response and pair.response.is_redirect():
                if redirect_count <= 0:
                    return WebFingerQueryDiagResponse(pair, None, [ WebDiagClient.TooManyRedirectsError(current_request) ])
                parsed_location_uri = ParsedUri.parse(pair.response.location())
                if not parsed_location_uri:
                    return WebFingerQueryDiagResponse(pair, None, [ ValueError('Location header is not a valid URI:', query_url, '(from', resource_uri, ')') ] )
                current_request = HttpRequest(parsed_location_uri)
            break

        # I guess we always have a non-null responses here, but mypy complains without the cast
        pair = cast(HttpRequestResponsePair, pair)
        ret_pair = HttpRequestResponsePair(first_request, current_request, pair.response)
        if ret_pair.response is None:
            raise RuntimeError('Unexpected None HTTP response')

        excs : list[Exception] = []
        if ret_pair.response.http_status != 200:
            excs.append(WebFingerDiagClient.WrongHttpStatusError(ret_pair))

        content_type = ret_pair.response.content_type()
        if (content_type is None or (content_type != "application/jrd+json"
            and not content_type.startswith( "application/jrd+json;" ))
        ):
            excs.append(WebFingerDiagClient.WrongContentTypeError(ret_pair))

        jrd : ClaimedJrd | None = None

        if ret_pair.response.payload is None:
            raise RuntimeError('Unexpected None payload in HTTP response')

        try:
            json_string = ret_pair.response.payload.decode(encoding=ret_pair.response.payload_charset() or "utf8")

            jrd = ClaimedJrd(json_string) # May throw JSONDecodeError
            jrd.validate() # May throw JrdError
        except ExceptionGroup as exc:
            excs += exc.exceptions
        except Exception as exc:
            excs.append(exc)

        return WebFingerQueryDiagResponse(ret_pair, jrd, excs)
