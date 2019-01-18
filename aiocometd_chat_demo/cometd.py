"""Synchronous CometD client"""
from enum import IntEnum, unique, auto
import asyncio
from functools import partial
from typing import Optional, Iterable, TypeVar, Awaitable, Callable, Any
import concurrent.futures as futures
from contextlib import suppress

import aiocometd
from aiocometd.typing import JsonObject
# pylint: disable=no-name-in-module
from PyQt5.QtCore import pyqtSignal, pyqtProperty, QObject  # type: ignore
# pylint: enable=no-name-in-module

from aiocometd_chat_demo.exceptions import InvalidStateError


T_co = TypeVar("T_co", covariant=True)  # pylint: disable=invalid-name


def run_coro(coro: Awaitable[T_co],
             callback: Optional[Callable[["futures.Future[T_co]"], Any]]
             = None,
             loop: Optional[asyncio.AbstractEventLoop] = None,) \
        -> "futures.Future[T_co]":
    """Schedule the execution of the given *coro* and set *callback* to be
    called when the *coro* is finished

    :param coro: A coroutine
    :param callback: A callback function called with the future object \
    associated with *coro*
    :param loop: The event loop on which the *coro* should be scheduled
    :return: The future associated with the *coro*
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    if callback is not None:
        future.add_done_callback(callback)
    return future


@unique
class ClientState(IntEnum):
    """CometD client states"""
    #: Connected with the server
    CONNECTED = auto()
    #: Disconnected state
    DISCONNECTED = auto()
    #: Disconnected state due to an error
    ERROR = auto()


# pylint: disable=too-few-public-methods
class MessageResponse(QObject):  # type: ignore
    """The asynchronous result of a sent CometD message"""
    #: Contains the exception object if finished with an error, otherwise None
    error: Optional[BaseException] = None
    #: Contains the response of the server when finished successfully,
    #: otherwise None
    result: Optional[JsonObject] = None
    #: Emited when the response has been received
    finished = pyqtSignal()

# pylint: enable=too-few-public-methods


# pylint: disable=too-many-instance-attributes
class CometdClient(QObject):  # type: ignore
    """Synchronous CometD client implementation

    This class enables the asynchronous Client class from aiocometd to be used
    in synchronous code if it runs on a quamash event loop.
    Since the event loop is shared by Qt's and asyncio's events, the
    concurrent.futures.Future can't be awaited, blocking is not allowed.
    Instead, this class is implemented similarly to how asynchronous network
    operations are implemented in Qt. Namely, on a method call the operation
    is started and the method immediately returns, and then the results or the
    potential errors during the asynchronous operation are broadcasted with
    signals.
    """
    #: Signal emited when the client's state is changed
    state_changed = pyqtSignal(ClientState)
    #: Signal emited when the client enters the :obj:`~ClientState.CONNECTED`
    #: state
    connected = pyqtSignal()
    #: Signal emited when the client enters the
    #: :obj:`~ClientState.DISCONNECTED` state
    disconnected = pyqtSignal()
    #: Signal emited when the client enters the :obj:`~ClientState.ERROR` state
    error = pyqtSignal(Exception)
    #: Signal emited when a message has been received from the server
    message_received = pyqtSignal(dict)

    def __init__(self, url: str, subscriptions: Iterable[str],
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """
        :param url: CometD service url
        :param subscriptions: A list of channels to which the client should \
        subscribe
        :param loop: Event :obj:`loop <asyncio.BaseEventLoop>` used to
                     schedule tasks. If *loop* is ``None`` then
                     :func:`asyncio.get_event_loop` is used to get the default
                     event loop.
        """
        super().__init__()
        self._url = url
        self._subscriptions = list(subscriptions)
        self._loop = loop or asyncio.get_event_loop()
        self._client: Optional[aiocometd.Client] = None
        self._state = ClientState.DISCONNECTED
        self._state_signals = {
            ClientState.CONNECTED: self.connected,
            ClientState.DISCONNECTED: self.disconnected,
        }
        self._connect_task: Optional["futures.Future[None]"] = None

    @pyqtProperty(ClientState, notify=state_changed)
    def state(self) -> ClientState:
        """Current state of the client"""
        return self._state

    @state.setter  # type: ignore
    def state(self, new_state: ClientState) -> None:
        """Set the state of the client to *state*"""
        # if the state didn't changed then don't do anything
        if new_state != self._state:
            self._state = new_state
            # notify listeners that the state changed
            self.state_changed.emit(self._state)
            # emit state specific signals
            if new_state in self._state_signals:
                self._state_signals[new_state].emit()

    def connect_(self) -> None:
        """Connect to the CometD service and start listening for messages

        The function returns immediately. On success the
        :obj:`~CometdClient.connected` signal is emited or the
        :obj:`~CometdClient.error` signal on failure. If the client is already
        connected then it does nothing.
        """
        # don't do anything if already connected
        if self.state != ClientState.CONNECTED:
            # schedule the coroutine for execution
            self._connect_task = run_coro(
                self._connect(),
                self._on_connect_done,
                self._loop
            )

    async def _connect(self) -> None:
        """Connect to the CometD service and retreive the messages sent by
        the service as long as the client is open
        """
        # connect to the service
        async with aiocometd.Client(self._url, loop=self._loop) as client:
            # set the asynchronous client attribute
            self._client = client
            # subscribe to all the channels
            for subscription in self._subscriptions:
                await client.subscribe(subscription)

            # put the client into a connected state
            self.state = ClientState.CONNECTED
            # listen for incoming messages

            with suppress(futures.CancelledError):
                async for message in client:
                    # emit signal about received messages
                    self._loop.call_soon_threadsafe(self.message_received.emit,
                                                    message)

        # clear the asynchronous client attribute
        self._client = None
        # put the client into a disconnected state
        self.state = ClientState.DISCONNECTED

    def _on_connect_done(self, future: "futures.Future[None]") -> None:
        """Evaluate the result of an asynchronous task

        Emit signals about errors if the *future's* result is an exception.
        :param future: A future associated with the asynchronous task
        """
        # clear the task member
        self._connect_task = None
        error = None
        with suppress(futures.CancelledError):
            error = future.exception()
        if error is not None:
            self.state = ClientState.ERROR
            self.error.emit(error)

    def disconnect_(self) -> None:
        """Disconnect from the CometD service

        If the client is not connected it does nothing.
        """
        if self.state == ClientState.CONNECTED:
            # check that the task has been initialized
            if self._connect_task is None:
                raise InvalidStateError("Uninitialized _connect_task "
                                        "attribute.")
            self._connect_task.cancel()

    def publish(self, channel: str, data: JsonObject) -> MessageResponse:
        """Publish *data* to the given *channel*

        :param channel: Name of the channel
        :param data: Data to send to the server
        :return: Return the response associated with the message
        """
        # check that the client has been initialized
        if self.state != ClientState.CONNECTED:
            raise InvalidStateError("Can't send messages in a non-connected "
                                    "state.")
        if self._client is None:
            raise InvalidStateError("Uninitialized _client attribute.")
        response = MessageResponse()
        run_coro(self._client.publish(channel, data),
                 partial(self._on_publish_done, response),
                 self._loop)
        return response

    @staticmethod
    def _on_publish_done(response: MessageResponse,
                         future: "futures.Future[JsonObject]") -> None:
        """Evaluate the result of an asynchronous message sending task

        :param response: A response associated with the *future*
        :param future: A future associated with the asynchronous task
        """
        # set the error or result attributes of the response depending on
        # whether it was completed normally or it exited with an exception
        if future.exception() is not None:
            response.error = future.exception()
        else:
            response.result = future.result()
        # notify listeners that a response has been received
        response.finished.emit()

# pylint: disable=too-many-instance-attributes
