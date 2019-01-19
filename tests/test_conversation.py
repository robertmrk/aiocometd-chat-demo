from datetime import datetime, timedelta

from asynctest import TestCase, mock
from PyQt5.QtCore import Qt

from aiocometd_chat_demo.conversation import ConversationModel, ChatMessage, \
    ItemRole


class TestConversationModel(TestCase):
    def setUp(self):
        self.channel_name = "name"
        self.model = ConversationModel(self.channel_name)

    def test_init(self):
        self.assertEqual(self.model._channel, self.channel_name)
        self.assertEqual(self.model._messages, [])

    def test_channel(self):
        self.assertEqual(self.model.channel, self.model._channel)

    def test_row_count_returns_message_count(self):
        count = 5
        self.model._messages = [None] * count

        self.assertEqual(self.model.rowCount(), count)

    def test_row_count_zero_on_empty_model(self):
        self.assertEqual(self.model.rowCount(), 0)

    def test_role_names(self):
        self.assertEqual(self.model.roleNames(), self.model._role_names)

    def test_send_message(self):
        self.model.message_sending_requested = mock.MagicMock()
        contents = "text"

        self.model.send_message(contents)

        self.model.message_sending_requested.emit.assert_called_with(contents)

    def test_add_incoming_message(self):
        self.model.beginInsertRows = mock.MagicMock()
        self.model.endInsertRows = mock.MagicMock()
        self.assertEqual(self.model._messages, [])
        message = ChatMessage(time=datetime.now(), sender="john",
                              contents="hi")

        self.model.add_incoming_message(message)

        self.assertEqual(self.model._messages, [message])


class TestConversationModelData(TestCase):
    message1 = ChatMessage(time=datetime.now(), sender="john", contents="hi")
    message2 = ChatMessage(time=datetime.now() + timedelta(minutes=1),
                           sender="james", contents="bye")

    def setUp(self):
        self.model = ConversationModel("channel_name")
        self.model._messages = [self.message1, self.message2]

    def test_data(self):
        cases = (
            (0, 0, ItemRole.TIME, self.message1.time),
            (0, 0, ItemRole.SENDER, self.message1.sender),
            (0, 0, ItemRole.CONTENTS, self.message1.contents),
            (1, 0, ItemRole.TIME, self.message2.time),
            (1, 0, ItemRole.SENDER, self.message2.sender),
            (1, 0, ItemRole.CONTENTS, self.message2.contents)
        )

        for row, column, role, expected in cases:
            with self.subTest(row=row, column=column, role=role,
                              expected=expected):
                index = self.model.createIndex(row, column)
                self.assertEqual(self.model.data(index, role), expected)

    def test_data_return_none_for_invalid_index(self):
        cases = (
            (-1, 0, ItemRole.TIME, None),
            (-1, 0, ItemRole.SENDER, None),
            (-1, 0, ItemRole.CONTENTS, None),
            (2, 0, ItemRole.TIME, None),
            (2, 0, ItemRole.SENDER, None),
            (2, 0, ItemRole.CONTENTS, None)
        )

        for row, column, role, expected in cases:
            with self.subTest(row=row, column=column, role=role,
                              expected=expected):
                index = self.model.createIndex(row, column)
                self.assertEqual(self.model.data(index, role), expected)

    def test_data_return_none_for_unhandled_role(self):
        cases = (
            (0, 0, Qt.DisplayRole, None),
            (0, 0, Qt.DisplayRole, None),
            (0, 0, Qt.DisplayRole, None),
            (1, 0, Qt.DisplayRole, None),
            (1, 0, Qt.DisplayRole, None),
            (1, 0, Qt.DisplayRole, None)
        )

        for row, column, role, expected in cases:
            with self.subTest(row=row, column=column, role=role,
                              expected=expected):
                index = self.model.createIndex(row, column)
                self.assertEqual(self.model.data(index, role), expected)
