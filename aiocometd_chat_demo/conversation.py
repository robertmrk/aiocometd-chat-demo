"""Chat conversation related types"""
from typing import NamedTuple, List, ClassVar, Dict, Any, Optional
from datetime import datetime
from enum import IntEnum, unique
from dataclasses import dataclass, field

# pylint: disable=no-name-in-module,wrong-import-order
from PyQt5.QtCore import (  # type: ignore
    QAbstractListModel,
    Qt,
    QByteArray,
    QModelIndex,
    QDateTime,
    pyqtSlot,
    pyqtSignal,
    pyqtProperty
)
# pylint: enable=no-name-in-module,wrong-import-order


class ChatMessage(NamedTuple):
    """Represents a message received from the service"""
    #: Message arrival time
    time: datetime
    #: The user who sent the message
    sender: str
    #: The contets of the message
    contents: str


@unique
class ItemRole(IntEnum):
    """Custom item role for the :obj:`ConversationModel`"""
    #: Message arrival time role
    TIME = Qt.UserRole
    #: Message sender role
    SENDER = Qt.UserRole + 1
    #: Message contents role
    CONTENTS = Qt.UserRole + 2


@dataclass()
class ConversationModel(QAbstractListModel):  # type: ignore
    """A chat conversation or a timeline of messages between two or more users

    This class can also act as a list model of messages for item view classes.
    """
    #: The name of the conversation's channel
    _channel: str
    #: List of chat messages in the conversation in chronological order
    _messages: List[ChatMessage] = field(default_factory=list,
                                         init=False, repr=False)
    #: Custom item role names
    _role_names: ClassVar[Dict[int, QByteArray]] = {
        ItemRole.TIME: QByteArray(b"time"),
        ItemRole.SENDER: QByteArray(b"sender"),
        ItemRole.CONTENTS: QByteArray(b"contents"),
    }
    #: Signal emitted when the channel name changes
    channel_changed: ClassVar[pyqtSignal] = pyqtSignal(str)
    #: Sending of a message to this conversation was requested
    message_sending_requested: ClassVar[pyqtSignal] = pyqtSignal(str)

    def __post_init__(self) -> None:
        super().__init__()

    @pyqtProperty(str, notify=channel_changed)  # type: ignore
    def channel(self) -> str:
        """The name of the conversation's channel"""
        return self._channel

    # pylint: disable=invalid-name,unused-argument
    def rowCount(self, parent: Optional[QModelIndex] = None) -> int:
        """Returns the number of rows in the model

        :param parent: Unused since this not a hierarchical model
        :return: The number of rows in the model
        """
        return len(self._messages)

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
        # ignore out of range data requests
        if 0 <= index.row() < len(self._messages):
            # pylint: disable=unsubscriptable-object
            message = self._messages[index.row()]
            # pylint: enable=unsubscriptable-object
            if role == ItemRole.TIME:
                return QDateTime(message.time)
            if role == ItemRole.SENDER:
                return message.sender
            if role == ItemRole.CONTENTS:
                return message.contents
        return None

    @pyqtSlot(str, name="sendMessage")  # type: ignore
    def send_message(self, contents: str) -> None:
        """Send a new message with the specified *contents* to this
        conversation
        """
        self.message_sending_requested.emit(contents)

    @pyqtSlot(ChatMessage)  # type: ignore
    def add_incoming_message(self, message: ChatMessage) -> None:
        """Add an incoming *message* to the list of messages of the
        conversation
        """
        self.beginInsertRows(
            QModelIndex(),
            len(self._messages),
            len(self._messages)
        )
        self._messages.append(message)  # pylint: disable=no-member
        self.endInsertRows()
