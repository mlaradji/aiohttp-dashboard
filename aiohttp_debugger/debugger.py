from datetime import datetime
from asyncio import ensure_future
from aiohttp.web import WebSocketResponse
from .helper import PubSubSupport


class Debugger(PubSubSupport):
    self = None

    @classmethod
    def instance(cls, application):
        from . import action

        if cls.self is None:
            cls.self = cls(application, action.routes, action.static_routes)

        return cls.self

    def __init__(self, application, routes, static_routes):
        self._application = self._configure_application(application, routes, static_routes)
        self._state = self._State()
        self._api = self._Api(self._state)

    async def __call__(self, *args, **kwargs):
        return await self._middleware_factory(*args, **kwargs)

    def _configure_application(self, application, routes):
        self._add_middlewares(application)
        self._add_routes(application, routes)
        application.on_response_prepare.append(self._on_response_prepare)
        return application

    def _add_middlewares(self, application):
        application.middlewares.append(self)

    def _add_static_routes(self, application, static_routes):
        application.add_static("/static", f"{this_dir}/static")

    def _add_routes(self, application, routes):
        for method, path, handler in routes:
            application.router.add_route(method, path, handler)

    async def _middleware_factory(self, application, handler):

        async def middleware_handler(request):
            if self._is_sutable_req(request):
                self._handle_request(request)
            return await handler(request)
        return middleware_handler

    async def _on_response_prepare(self, request, response):
        if self._is_sutable_req(request):
            rid = id(request)
            if rid in self._state.requests.keys():
                self._state.requests[rid].update(
                    donetime=self._state.now,
                    done=True
                )

            if isinstance(response, WebSocketResponse):
                self._overload_ws_response(request, response)

    def _is_sutable_req(self, req):
        return not req.path.startswith("/_debugger")

    def _overload_ws_response(self, request, response):
        def ping_overload(data):
            """ for catch outbound message """
            self._handle_ws_msg(
                "ws_response_msg",
                request, data, self._out_msg_mapper, WsMsgOutbound())
            return response.__aiohttp_debugger_ping__(data)

        response.__aiohttp_debugger_ping__ = response.ping
        response.pong = ping_overload

        def pong_overload(data):
            """ for catch outbound message """
            self._handle_ws_msg(
                "ws_response_msg",
                request, data, self._out_msg_mapper, WsMsgOutbound())
            return response.__aiohttp_debugger_pong__(data)

        response.__aiohttp_debugger_pong__ = response.pong
        response.pong = pong_overload

        def send_str_overload(data):
            """ for catch outbound message """
            self._handle_ws_msg(
                "ws_response_msg",
                request, data, self._out_msg_mapper, WsMsgOutbound())
            return response.__aiohttp_debugger_send_str__(data)

        response.__aiohttp_debugger_send_str__ = response.send_str
        response.send_str = send_str_overload

        def send_bytes_overload(data):
            """ for catch outbound message """
            self._handle_ws_msg(
                "ws_response_msg",
                request, data, self._out_msg_mapper, WsMsgOutbound())
            return response.__aiohttp_debugger_send_str__(data)

        response.__aiohttp_debugger_send_bytes__ = response.send_bytes
        response.send_bytes = send_bytes_overload

        def send_json_overload(data):
            """ for catch outbound message """
            self._handle_ws_msg(
                "ws_response_msg",
                request, data, self._out_msg_mapper, WsMsgOutbound())
            return response.__aiohttp_debugger_send_json__(data)

        response.__aiohttp_debugger_send_json__ = response.send_json
        response.send_json = send_json_overload

        async def receive_overload():
            """ for catch incoming message """

            msg = await response.__aiohttp_debugger_receive__()
            self._handle_ws_msg(
                "ws_request_msg",
                request, msg, self._in_msg_mapper, WsMsgIncoming())
            return msg

        response.__aiohttp_debugger_receive__ = response.receive
        response.receive = receive_overload

        return response

    def _in_msg_mapper(self, msg):
        return msg.data

    def _out_msg_mapper(self, msg):
        return msg

    def _handle_ws_msg(self, key_name, req, msg, msg_mapper, event):
        if self._is_sutable_req(req):
            idreq = id(req)

            if idreq in self._state.requests.keys():
                if key_name not in self._state.requests[idreq].keys():
                    self._state.requests[idreq][key_name] = []

                self._state.requests[idreq][key_name] += [msg_mapper(msg)]
                self.fire(event)

    def _handle_request(self, request):
        self._state.put_request(request)

    @property
    def api(self):
        return self._api

    class _Api:

        def __init__(self, state):
            self._state = state

        @property
        def requests(self):
            return list(self._state.requests.values())

    class _State:

        def __init__(self):
            self._requests = dict()

        def put_request(self, request):
            id, record = self._make_request_log(request)
            self.requests[id] = record

        def _make_request_log(self, request) -> (int, dict):
            return id(request), dict(
                scheme=request.scheme,
                host=request.host,
                path=request.raw_path,
                method=request.method,
                begintime=self.now,
                done=False
            )

        @property
        def now(self):
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S:%f")

        @property
        def requests(self):
            return self._requests


class WsMsgIncoming(PubSubSupport.Event):
    def __init__(self):
        super().__init__(WsMsgIncoming.__name__)


class WsMsgOutbound(PubSubSupport.Event):
    def __init__(self):
        super().__init__(WsMsgOutbound.__name__)