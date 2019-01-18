from asynctest import TestCase, mock
import concurrent.futures

from aiocometd_chat_demo.cometd import CometdClient, ClientState, \
    MessageResponse, run_coro

from aiocometd_chat_demo.exceptions import InvalidStateError


class TestCometdClient(TestCase):
    def setUp(self):
        self.url = "url"
        self.subscriptions = ["channel1", "channel2"]
        self.client = CometdClient(self.url, self.subscriptions, self.loop)

    def make_async_iterator(self, iterable):
        async def iterator(instance):
            for item in iterable:
                yield item
        return iterator

    def test_init(self):
        self.assertEqual(self.client._url, self.url)
        self.assertEqual(self.client._subscriptions, self.subscriptions)
        self.assertEqual(self.client._loop, self.loop)
        self.assertEqual(self.client._state, ClientState.DISCONNECTED)

    @mock.patch("aiocometd_chat_demo.cometd.run_coro")
    def test_connect(self, run_coro):
        self.client._connect = mock.MagicMock()

        self.client.connect_()

        run_coro.assert_called_with(self.client._connect.return_value,
                                    self.client._on_connect_done,
                                    self.client._loop)

    @mock.patch("aiocometd_chat_demo.cometd.run_coro")
    def test_connect_do_nothing_if_connected(self, run_coro):
        self.client._state = ClientState.CONNECTED
        self.client._connect = mock.MagicMock()

        self.client.connect_()

        run_coro.assert_not_called()

    def test_disconnect(self):
        self.client._connect_task = mock.MagicMock()
        self.client._state = ClientState.CONNECTED

        self.client.disconnect_()

        self.client._connect_task.cancel.assert_called()

    def test_disconnect_does_nothing_if_disconnected(self):
        self.client._connect_task = mock.MagicMock()
        self.client._state = ClientState.DISCONNECTED

        self.client.disconnect_()

        self.client._connect_task.cancel.assert_not_called()

    def test_disconnect_does_nothing_in_error_state(self):
        self.client._connect_task = mock.MagicMock()
        self.client._state = ClientState.ERROR

        self.client.disconnect_()

        self.client._connect_task.cancel.assert_not_called()

    def test_disconnect_error_on_no_task(self):
        self.client._connect_task = None
        self.client._state = ClientState.CONNECTED

        with self.assertRaisesRegex(InvalidStateError,
                                    "Uninitialized _connect_task attribute."):
            self.client.disconnect_()

    @mock.patch("aiocometd_chat_demo.cometd.aiocometd.Client")
    async def test__connect(self, client_cls):
        client = mock.MagicMock()
        client_cls.return_value = client
        client.__aenter__ = mock.CoroutineMock(return_value=client)
        client.__aexit__ = mock.CoroutineMock()
        client.subscribe = mock.CoroutineMock()
        messages = [object(), object()]
        client.__aiter__ = self.make_async_iterator(messages)
        loop = mock.MagicMock()
        cometd_client = CometdClient(self.url, self.subscriptions, loop)
        cometd_client.message_received = mock.MagicMock()

        await cometd_client._connect()

        client_cls.assert_called_with(self.url, loop=loop)
        client.__aenter__.assert_called()
        client.subscribe.assert_has_calls([
            mock.call(channel) for channel in self.subscriptions
        ])
        loop.call_soon_threadsafe.assert_has_calls([
            mock.call(cometd_client.message_received.emit, messages[0]),
            mock.call(cometd_client.message_received.emit, messages[1])
        ])
        self.assertEqual(cometd_client.state, ClientState.DISCONNECTED)

    @mock.patch("aiocometd_chat_demo.cometd.aiocometd.Client")
    async def test__connect_retruns_if_cancelled(self, client_cls):
        client = mock.MagicMock()
        client_cls.return_value = client
        client.__aenter__ = mock.CoroutineMock(return_value=client)
        client.__aexit__ = mock.CoroutineMock()
        client.subscribe = mock.CoroutineMock()
        client.receive = mock.CoroutineMock(
            side_effect=concurrent.futures.CancelledError()
        )
        loop = mock.MagicMock()
        cometd_client = CometdClient(self.url, self.subscriptions, loop)
        cometd_client.message_received = mock.MagicMock()

        await cometd_client._connect()

        client_cls.assert_called_with(self.url, loop=loop)
        client.__aenter__.assert_called()
        client.subscribe.assert_has_calls([
            mock.call(channel) for channel in self.subscriptions
        ])
        self.assertEqual(cometd_client.state, ClientState.DISCONNECTED)

    def test_on_connect_done_does_nothing_on_normal_return(self):
        future = mock.MagicMock()
        future.exception.return_value = None
        self.client._set_state = mock.MagicMock()
        self.client.error = mock.MagicMock()

        self.client._on_connect_done(future)

        self.client._set_state.assert_not_called()
        self.client.error.emit.assert_not_called()

    def test_on_connect_done_does_nothing_on_cancelled_error(self):
        future = mock.MagicMock()
        future.exception.side_effect = concurrent.futures.CancelledError()
        self.client._set_state = mock.MagicMock()
        self.client.error = mock.MagicMock()

        self.client._on_connect_done(future)

        self.client._set_state.assert_not_called()
        self.client.error.emit.assert_not_called()

    def test_on_connect_done_set_error_on_exception(self):
        future = mock.MagicMock()
        future.exception.return_value = ValueError()
        self.client._set_state = mock.MagicMock()
        self.client.error = mock.MagicMock()

        self.client._on_connect_done(future)

        self.assertEqual(self.client.state, ClientState.ERROR)
        self.client.error.emit.assert_called_with(
            future.exception.return_value
        )

    @mock.patch("aiocometd_chat_demo.cometd.partial")
    @mock.patch("aiocometd_chat_demo.cometd.run_coro")
    def test_publish(self, run_coro, partial_func):
        channel = "channel"
        message = object()
        self.client._client = mock.MagicMock()
        self.client._state = ClientState.CONNECTED

        response = self.client.publish(channel, message)

        self.client._client.publish.assert_called_with(channel, message)
        partial_func.assert_called_with(self.client._on_publish_done,
                                        response)
        run_coro.assert_called_with(
            self.client._client.publish.return_value,
            partial_func.return_value,
            self.loop
        )

    def test_publish_error_if_not_connected(self):
        channel = "channel"
        message = object()

        with self.assertRaisesRegex(InvalidStateError,
                                    "Can't send messages in a non-connected "
                                    "state."):
            self.client.publish(channel, message)

    def test_publish_error_if_client_not_initialized(self):
        channel = "channel"
        message = object()
        self.client._state = ClientState.CONNECTED

        with self.assertRaisesRegex(InvalidStateError,
                                    "Uninitialized _client attribute."):
            self.client.publish(channel, message)

    def test__on_publish_done_on_normal_return(self):
        future = mock.MagicMock()
        future.exception.return_value = None
        response = MessageResponse()
        response.finished = mock.MagicMock()

        self.client._on_publish_done(response, future)

        self.assertIsNone(response.error)
        self.assertEqual(response.result, future.result.return_value)
        response.finished.emit.assert_called()

    def test__on_publish_done_error_on_exception(self):
        future = mock.MagicMock()
        future.exception.return_value = ValueError()
        response = MessageResponse()
        response.finished = mock.MagicMock()

        self.client._on_publish_done(response, future)

        self.assertEqual(response.error, future.exception.return_value)
        self.assertIsNone(response.result)
        response.finished.emit.assert_called()

    def test_set_state_connected(self):
        self.client._state_signals[ClientState.CONNECTED] = mock.MagicMock()
        self.client._state = ClientState.DISCONNECTED
        self.client.state_changed = mock.MagicMock()

        self.client.state = ClientState.CONNECTED

        self.client.state_changed.emit.assert_called_with(
            ClientState.CONNECTED
        )
        self.client._state_signals[ClientState.CONNECTED].emit.assert_called()

    def test_set_state_disconnected(self):
        self.client._state_signals[ClientState.DISCONNECTED] = mock.MagicMock()
        self.client._state = ClientState.CONNECTED
        self.client.state_changed = mock.MagicMock()

        self.client.state = ClientState.DISCONNECTED

        self.client.state_changed.emit.assert_called_with(
            ClientState.DISCONNECTED
        )
        self.client._state_signals[ClientState.DISCONNECTED].emit\
            .assert_called()

    def test_set_state_no_state_change(self):
        self.client._state_signals[ClientState.DISCONNECTED] = mock.MagicMock()
        self.client._state = ClientState.DISCONNECTED
        self.client.state_changed = mock.MagicMock()

        self.client.state = ClientState.DISCONNECTED

        self.client.state_changed.emit.assert_not_called()
        self.client._state_signals[ClientState.DISCONNECTED].emit\
            .assert_not_called()

    def test_set_state_on_error(self):
        self.client._state_signals[ClientState.DISCONNECTED] = mock.MagicMock()
        self.client._state = ClientState.DISCONNECTED
        self.client.state_changed = mock.MagicMock()

        self.client.state = ClientState.ERROR

        self.client.state_changed.emit.assert_called_with(ClientState.ERROR)


class TestRunCoro(TestCase):
    @mock.patch("aiocometd_chat_demo.cometd.asyncio")
    def test_with_loop_and_callback(self, asyncio_mod):
        coro = mock.MagicMock()
        callback = mock.MagicMock()
        loop = mock.MagicMock()
        future = mock.MagicMock()
        asyncio_mod.run_coroutine_threadsafe.return_value = future

        result = run_coro(coro, callback, loop)

        self.assertEqual(result, future)
        asyncio_mod.run_coroutine_threadsafe.assert_called_with(coro, loop)
        future.add_done_callback.assert_called_with(callback)

    @mock.patch("aiocometd_chat_demo.cometd.asyncio")
    def test_without_callback(self, asyncio_mod):
        coro = mock.MagicMock()
        loop = mock.MagicMock()
        future = mock.MagicMock()
        asyncio_mod.run_coroutine_threadsafe.return_value = future

        result = run_coro(coro, None, loop)

        self.assertEqual(result, future)
        asyncio_mod.run_coroutine_threadsafe.assert_called_with(coro, loop)
        future.add_done_callback.assert_not_called()

    @mock.patch("aiocometd_chat_demo.cometd.asyncio")
    def test_without_loop(self, asyncio_mod):
        coro = mock.MagicMock()
        callback = mock.MagicMock()
        loop = mock.MagicMock()
        future = mock.MagicMock()
        asyncio_mod.get_event_loop.return_value = loop
        asyncio_mod.run_coroutine_threadsafe.return_value = future

        result = run_coro(coro, callback, None)

        self.assertEqual(result, future)
        asyncio_mod.run_coroutine_threadsafe.assert_called_with(coro, loop)
        future.add_done_callback.assert_called_with(callback)
