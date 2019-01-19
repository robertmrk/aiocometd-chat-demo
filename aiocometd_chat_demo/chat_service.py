"""Chat service class definition"""
from typing import Optional, Deque
from datetime import datetime
from collections import deque
import logging

# pylint: disable=no-name-in-module,wrong-import-order
from PyQt5.QtCore import (  # type: ignore
    QObject,
    pyqtSlot,
    pyqtSignal,
    pyqtProperty,
)
# pylint: enable=no-name-in-module,wrong-import-order

from aiocometd_chat_demo.cometd import CometdClient, JsonObject
from aiocometd_chat_demo.channels import ChannelsModel, ChannelType, \
    ChatMessage


LOGGER = logging.getLogger(__name__)
#: Name of the chat room (all existing demos use this name at the moment)
CHAT_ROOM_NAME = "demo"


class ChatService(QObject):  # type: ignore
    """CometD demo chat service"""
    #: Url of the service
    _url: str = ""
    #: Name of the chat room
    _room_name: str = CHAT_ROOM_NAME
    #: Username of the peer/member
    _username: str = ""
    #: CometD client object
    _client: Optional[CometdClient] = None
    #: Model object managing the existing channels inside the chat service
    _channels_model: Optional[ChannelsModel] = None
    #: A queue that contains the usernames to which we most recently sent
    #: a private message, but the messages doesn't yet arrived as incoming
    #: messages (when private messages come back from the service they doesn't
    #: contain the recipient of the message)
    _last_private_message_users: Deque[str] = deque()
    #: The string representation of the last error that occurred
    _last_error: str = ""
    #: Name of the CometD service channel on which new members advertise
    #: themselves
    _members_service_channel = "/service/members"
    #: Signal emitted when the url changes
    url_changed = pyqtSignal(str)
    #: Signal emitted when the username changes
    username_changed = pyqtSignal(str)
    #: Signal emitted when the channels_model changes
    channels_model_changed = pyqtSignal(ChannelsModel)
    #: Signal emitted when the last_error changes
    last_error_changed = pyqtSignal(str)
    #: Signal emitted when a connection is established with the service
    connected = pyqtSignal()
    #: Signal emitted when the client disconnects from the service
    disconnected = pyqtSignal()
    #: Signal emitted when an error occurs (the error message is stored in
    #: last_error)
    error = pyqtSignal()

    @pyqtProperty(str, notify=url_changed)
    def url(self) -> str:
        """Url of the service"""
        return self._url

    @url.setter  # type: ignore
    def url(self, url: str) -> None:
        """Set the url of the service"

        :param url: New url
        """
        self._url = url
        self.url_changed.emit(url)

    @pyqtProperty(str, notify=url_changed)
    def username(self) -> str:
        """Username of the peer/member"""
        return self._username

    @username.setter  # type: ignore
    def username(self, username: str) -> None:
        """Set the username

        :param username: New username
        """
        self._username = username
        self.username_changed.emit(username)

    @pyqtProperty(ChannelsModel, notify=channels_model_changed)
    def channels_model(self) -> Optional[ChannelsModel]:
        """Model object managing the existing channels inside the chat service
        """
        return self._channels_model

    @channels_model.setter  # type: ignore
    def channels_model(self, model: Optional[ChannelsModel]) -> None:
        """Set the channels model

        :param model: New channels model object
        """
        self._channels_model = model
        self.channels_model_changed.emit(model)

    @pyqtProperty(str, notify=last_error_changed)
    def last_error(self) -> str:
        """The string representation of the last error that occurred"""
        return self._last_error

    @last_error.setter  # type: ignore
    def last_error(self, error_message: str) -> None:
        """Set the last error

        :param error_message: New error message
        """
        self._last_error = error_message
        self.last_error_changed.emit(error_message)
        # notify listeners that some error have occurred
        self.error.emit()

    @property
    def _room_channel(self) -> str:
        """CometD broadcast channel where new messages are published"""
        return "/chat/" + self._room_name

    @property
    def _members_channel(self) -> str:
        """CometD broadcast channel where the new membership states are
        published
        """
        return "/members/" + self._room_name

    @pyqtSlot()  # type: ignore
    def connect_(self) -> None:
        """Connect to the chat service and start listening for messages"""
        # create new channels model and connect its signals
        self.channels_model = ChannelsModel(self._room_name)
        self.channels_model.message_sending_requested.connect(
            self.send_message
        )

        # create a new CometD client and connect its signals
        self._client = CometdClient(
            self.url,
            (self._members_channel, self._room_channel)
        )
        self._client.connected.connect(self.on_connected)
        self._client.disconnected.connect(self.on_disconnected)
        self._client.error.connect(self.on_error)
        self._client.error.connect(self.on_disconnected)
        self._client.message_received.connect(self.message_received)

        # start the connection
        self._client.connect_()

    @pyqtSlot()  # type: ignore
    def on_connected(self) -> None:
        """Notify observers that a connection was successfully established
        and notify the service that a new peer/member has joined the chat
        """
        if self._client is not None:
            self._client.publish(self._members_service_channel, {
                "user": self._username,
                "room": self._room_channel
            })
            self.connected.emit()
        else:
            message = "Uninitialized _client attribute."
            LOGGER.error(message)
            self.last_error = message

    def disconnect_(self) -> None:
        """Disconnect from the chat service"""
        if self._client is not None:
            self._client.disconnect_()

    @pyqtSlot()  # type: ignore
    def on_disconnected(self) -> None:
        """Notify observers that the connection has been terminated"""
        if self._client is not None:
            # destroy the CometD client
            self._client.disconnect()
            self._client = None

            # destroy the channels model
            self.channels_model.disconnect()
            self.channels_model = None  # type: ignore

            self.disconnected.emit()
        else:
            message = "Uninitialized _client attribute."
            LOGGER.error(message)
            self.last_error = message

    @pyqtSlot(Exception)  # type: ignore
    def on_error(self, error: Exception) -> None:
        """Update the value of the last error message with *error*

        :param error: An exception during the connection
        """
        message = repr(error)
        LOGGER.error("CometD client error: %s", message)
        self.last_error = message

    @pyqtSlot(dict)  # type: ignore
    def message_received(self, message: JsonObject) -> None:
        """Add the incoming *message* to the channels model

        :param message: An incoming message
        """
        if self.channels_model is not None:
            # add a new incoming chat message
            if message["channel"] == self._room_channel:
                # create a message object
                data = message["data"]
                chat_message = ChatMessage(
                    sender=data["user"],
                    contents=data["chat"],
                    time=datetime.now()
                )
                # by default use the group channel
                channel_name = self._room_name
                channel_type = ChannelType.GROUP
                # if it's a private message
                if data.get("scope") == "private":
                    channel_type = ChannelType.USER
                    # get the sender of the message
                    channel_name = data["user"]
                    # if the message appears to be sent by ourselves, then
                    # then it's a private message that we sent out and came
                    # back from the service
                    # pylint: disable=comparison-with-callable
                    if channel_name == self.username:
                        # get the name of the recipient to who we sent the
                        # message from the queue (we're expecting that private
                        # messages we sent come back in the same order from
                        # the service)
                        channel_name = self._last_private_message_users.pop()
                    # pylint: enable=comparison-with-callable

                self.channels_model.add_incoming_message(
                    channel_name=channel_name,
                    channel_type=channel_type,
                    message=chat_message
                )
            # update the members of the chat
            elif message["channel"] == self._members_channel:
                # avoid listing ourseves as a member, we don't need to send
                # messages to ourselves
                current_members = set(message["data"])
                current_members.remove(self.username)
                self.channels_model.update_available_channels(current_members)
        else:
            message = "Uninitialized channels_model attribute."
            LOGGER.error(message)
            self.last_error = message

    @pyqtSlot(str, str, str)  # type: ignore
    def send_message(self, channel_name: str, channel_type: ChannelType,
                     contents: str) -> None:
        """Send a chat message with the given *contents* to the channel named
        *channel_type* with the type *channel_type*

        :param channel_name: The name of the chat service channel
        :param channel_type: The type of the chat service channel
        :param contents: The contents of the chat message
        """
        if self._client is not None:
            # send a message on the group channel to the single group
            # chat channel
            if channel_type == ChannelType.GROUP:
                self._client.publish(self._room_channel, {
                    "user": self.username,
                    "chat": contents
                })
            # otherwise send a private message
            else:
                # store username of the peer to who we're sending the message
                self._last_private_message_users.appendleft(channel_name)
                self._client.publish("/service/privatechat", {
                    "room": self._room_channel,
                    "user": self.username,
                    "chat": contents,
                    "peer": channel_name
                })
        else:
            message = "Uninitialized _client attribute."
            LOGGER.error(message)
            self.last_error = message
