"""Chat channels related type definitions"""
from typing import List, ClassVar, Dict, Any, Optional, Set
from enum import IntEnum, Enum, unique
from bisect import bisect
from dataclasses import dataclass, field

# pylint: disable=no-name-in-module,wrong-import-order
from PyQt5.QtCore import (  # type: ignore
    QAbstractListModel,
    Qt,
    QByteArray,
    QModelIndex,
    pyqtSignal
)
# pylint: enable=no-name-in-module,wrong-import-order

from .conversation import ConversationModel, ChatMessage


@unique
class ChannelType(str, Enum):
    """The type of the chat channel"""
    #: A group channel with multiple/unlimited members
    GROUP = "group"
    #: A private channel with two members
    USER = "user"


@dataclass()
class ChannelItem:
    """Represents a chat channel"""
    #: The name of the channel
    name: str
    #: The channel's type
    type: ChannelType
    #: The conversation model containing the messages on the channel
    conversation: ConversationModel = field(init=False)

    def __post_init__(self) -> None:
        self.conversation = ConversationModel(self.name)

    def __lt__(self, other: "ChannelItem") -> bool:
        return self.name < other.name


@unique
class ChannelItemRole(IntEnum):
    """Custom item role for the :obj:`ChannelsModel`"""
    #: Channel name role
    NAME = Qt.UserRole
    #: Conversation model role
    CONVERSATION = Qt.UserRole + 1
    #: Channel type role
    CHANNEL_TYPE = Qt.UserRole + 2


@dataclass()
class ChannelsModel(QAbstractListModel):  # type: ignore
    """Represents all the channels available inside a chat service and inserts
    every incoming message to it's appropriate conversation

    This class can also act as a list model of channels for item view classes.
    """
    #: The name of the single group channel
    group_channel_name: str
    #: Group channel item
    group_channel: ChannelItem = field(init=False, repr=False)
    #: List of user channel items
    _channels: List[ChannelItem] = field(default_factory=list, init=False,
                                         repr=False)
    #: Custom item role names
    _role_names: ClassVar[Dict[int, QByteArray]] = {
        ChannelItemRole.NAME: QByteArray(b"name"),
        ChannelItemRole.CONVERSATION: QByteArray(b"conversation"),
        ChannelItemRole.CHANNEL_TYPE: QByteArray(b"type")
    }
    #: Sending of a message was requested to the specified
    #: (channel_name, channel_type and contents)
    message_sending_requested: ClassVar[pyqtSignal] = pyqtSignal(str, str, str)

    def __post_init__(self) -> None:
        super().__init__()
        # create the single group channel
        self.group_channel = ChannelItem(
            name=self.group_channel_name,
            type=ChannelType.GROUP
        )
        # forward message sending request signals
        self.group_channel.conversation.message_sending_requested.connect(
            lambda contents: self.message_sending_requested.emit(
                self.group_channel.name,
                self.group_channel.type,
                contents
            )
        )

    # pylint: disable=invalid-name,unused-argument
    def rowCount(self, parent: Optional[QModelIndex] = None) -> int:
        """Returns the number of rows in the model

        :param parent: Unused since this not a hierarchical model
        :return: The number of rows in the model
        """
        # return the number of user channels + the single group channel
        return len(self._channels) + 1

    def roleNames(self) -> Dict[int, QByteArray]:
        """Returns the mapping between the custom item roles and their names

        :return: Mapping between the custom item roles and their names
        """
        return self._role_names

    # pylint: enable=invalid-name,unused-argument

    def data(self, index: QModelIndex, role: Optional[int] = None) -> Any:
        """Return the data at the row of the given *index* and for the
        specified *role*

        :param index: Used for specifying the model's row, the column is \
        ignored
        :param role: Indicates which type of data the view requested
        :return: The data the view requested at the specified *row* for the \
        given *role*
        """
        channel = None
        # the first channel is the group channel
        if index.row() == 0:
            channel = self.group_channel
        # beyond the 0th index return one of the user channels if the requested
        # row is not out of range
        elif 1 <= index.row() < len(self._channels)+1:
            # pylint: disable=unsubscriptable-object
            channel = self._channels[index.row()-1]
            # pylint: enable=unsubscriptable-object

        # if the requested row wasn't out of range and a channel was found
        if channel is not None:
            if role == ChannelItemRole.NAME:
                return channel.name
            if role == ChannelItemRole.CONVERSATION:
                return channel.conversation
            if role == ChannelItemRole.CHANNEL_TYPE:
                return channel.type.value
        return None

    def _add_channel(self, name: str) -> None:
        """Add a new channel with the with the given *name*"""
        # create the user channel
        channel_item = ChannelItem(name=name, type=ChannelType.USER)
        # forward message sending request signals
        channel_item.conversation.message_sending_requested.connect(
            lambda contents: self.message_sending_requested.emit(
                channel_item.name,
                channel_item.type,
                contents
            )
        )

        # find the index where the new channel should be inserted to maintain
        # sorted channel order
        index = bisect(self._channels, channel_item)

        # insert the channel
        self.beginInsertRows(QModelIndex(), index+1, index+1)
        # pylint: disable=no-member
        self._channels.insert(index, channel_item)
        # pylint: enable=no-member
        self.endInsertRows()

    def _remove_channel(self, name: str) -> None:
        """Remove the channel named *name*"""
        # find the channel by name
        index = self._channel_index(name)
        # if found
        if index >= 0:
            self.beginRemoveRows(QModelIndex(), index+1, index+1)
            # remove the channel
            # pylint: disable=no-member
            channel_item = self._channels.pop(index)
            # pylint: enable=no-member
            # disconnect all signals of the channel
            channel_item.conversation.disconnect()
            self.endRemoveRows()

    def _channel_index(self, name: str) -> int:
        """Find the index of channel with the given *name*

        It would be great to use bisect for this task but unfortunately it
        doesn't takes a key predicate, so we can only use it to find
        comparable items, and it seems wasteful to instantiate a dummy channel
        just for this purpose.
        :param name: The name of the channel
        :return: The index of the channel or -1 if not found
        """
        # standard binary search algorithm
        left = 0
        right = len(self._channels) - 1
        while left <= right:
            # pylint: disable=unsubscriptable-object
            mid = left + (right - left) // 2
            if name < self._channels[mid].name:
                right = mid - 1
            elif name > self._channels[mid].name:
                left = mid + 1
            else:
                return mid
            # pylint: enable=unsubscriptable-object
        return -1

    def update_available_channels(self, channel_names: Set[str]) -> None:
        """Update the list of channels to be the same as specified by
        *channel_names*

        Existing channels with names not present in *channel_names* will be
        removed and new channels will be added for names in *channel_names*
        that doesn't exist yet.
        :param channel_names: The current set of channel names
        """
        # create sets of new and dropped channel names
        # pylint: disable=not-an-iterable
        current_names = set(item.name for item in self._channels)
        # pylint: enable=not-an-iterable
        dropped_channels = current_names - channel_names
        new_channels = channel_names - current_names

        # add new channels
        for name in new_channels:
            self._add_channel(name)

        # remove dropped channels
        for name in dropped_channels:
            self._remove_channel(name)

    # pylint: disable=too-many-arguments
    def add_incoming_message(self, channel_name: str,
                             channel_type: ChannelType,
                             message: ChatMessage) -> None:
        """Add an incoming *message* to the list of messages of the
        appropriate conversation

        :param channel_name: The name of the channel
        :param channel_type: The channel's type
        :param message: An incoming chat message
        """
        # add the message to the group channel if it has the right type
        if channel_type == ChannelType.GROUP:
            self.group_channel.conversation.add_incoming_message(message)

        # otherwise add a user channel
        else:
            # find the channel by name
            index = self._channel_index(channel_name)
            # if found
            if index >= 0:
                # pylint: disable=unsubscriptable-object
                channel = self._channels[index]
                # pylint: enable=unsubscriptable-object
                channel.conversation.add_incoming_message(message)

    # pylint: enable=too-many-arguments
