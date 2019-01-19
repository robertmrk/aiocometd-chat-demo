from asynctest import TestCase, mock
from PyQt5.QtCore import Qt, QModelIndex

from aiocometd_chat_demo.channels import ChannelsModel, ChannelItemRole, \
    ChannelType, ChannelItem


class TestChannelItem(TestCase):
    def test_less_then_comparable_by_name(self):
        channel1 = ChannelItem(name="channel1", type=ChannelType.GROUP)
        channel2 = ChannelItem(name="channel2", type=ChannelType.GROUP)
        channel3 = ChannelItem(name="channel3", type=ChannelType.GROUP)

        self.assertTrue(channel1 < channel2 < channel3)


class TestChannelsModel(TestCase):
    def setUp(self):
        self.group_channel_name = "group"
        self.model = ChannelsModel(group_channel_name=self.group_channel_name)

    def test_init(self):
        model = ChannelsModel(group_channel_name=self.group_channel_name)

        self.assertIsInstance(model.group_channel, ChannelItem)
        self.assertEqual(model.group_channel_name, self.group_channel_name)
        self.assertEqual(model.group_channel.name, self.group_channel_name)

    def test_init_sets_up_signal_forwarding(self):
        model = ChannelsModel(group_channel_name=self.group_channel_name)
        model.message_sending_requested = mock.MagicMock()
        contents = "message"

        model.group_channel.conversation.message_sending_requested.emit(
            contents
        )

        model.message_sending_requested.emit.assert_called_with(
            model.group_channel.name,
            model.group_channel.type,
            contents
        )

    def test_row_count(self):
        for user_channels in range(3):
            with self.subTest(user_channels=user_channels):
                self.model._channels = [None] * user_channels
                self.assertEqual(self.model.rowCount(), user_channels+1)

    def test_role_names(self):
        self.assertEqual(self.model.roleNames(), self.model._role_names)

    def test_channel_index(self):
        self.model._channels = [
            ChannelItem("b", ChannelType.USER),
            ChannelItem("c", ChannelType.USER),
            ChannelItem("d", ChannelType.USER),
            ChannelItem("e", ChannelType.USER),
            ChannelItem("f", ChannelType.USER),
            ChannelItem("g", ChannelType.USER),
            ChannelItem("h", ChannelType.USER),
            ChannelItem("i", ChannelType.USER),
            ChannelItem("j", ChannelType.USER),
            ChannelItem("k", ChannelType.USER),
        ]
        cases = (
            ("b", 0),
            ("c", 1),
            ("d", 2),
            ("e", 3),
            ("f", 4),
            ("g", 5),
            ("h", 6),
            ("i", 7),
            ("j", 8),
            ("k", 9),
            ("a", -1),
            ("z", -1),
        )
        for channel_name, expected in cases:
            with self.subTest(channel_name=channel_name, expected=expected):
                self.assertEqual(self.model._channel_index(channel_name),
                                 expected)

    def test_add_channel_inserts_channel_in_sorted_order(self):
        self.model._channels = [
            ChannelItem("a", ChannelType.USER),
            ChannelItem("c", ChannelType.USER),
            ChannelItem("d", ChannelType.USER),
            ChannelItem("e", ChannelType.USER)
        ]
        self.model.message_sending_requested = mock.MagicMock()
        self.model.beginInsertRows = mock.MagicMock()
        self.model.endInsertRows = mock.MagicMock()
        channel_name = "b"
        expected_index = 1
        preinsert_count = len(self.model._channels)

        self.model._add_channel(channel_name)

        self.assertEqual(len(self.model._channels), preinsert_count+1)
        self.assertEqual(self.model._channels[expected_index].name,
                         channel_name)
        self.model.beginInsertRows.assert_called_with(
            QModelIndex(), expected_index+1, expected_index+1
        )
        self.model.endInsertRows.assert_called()

    def test_add_channel_sets_up_signal_forwarding(self):
        self.model.message_sending_requested = mock.MagicMock()
        self.model._add_channel("channel")
        channel = self.model._channels[0]
        message_contents = "contents"

        channel.conversation.message_sending_requested.emit(message_contents)

        self.model.message_sending_requested.emit.assert_called_with(
            channel.name, channel.type, message_contents
        )

    def test_remove_channel(self):
        self.model.beginRemoveRows = mock.MagicMock()
        self.model.endRemoveRows = mock.MagicMock()
        channel = mock.MagicMock()
        channel_name = "channel"
        self.model._channels = [channel]
        index = 0
        self.model._channel_index = mock.MagicMock(return_value=index)

        self.model._remove_channel(channel_name)

        self.model.beginRemoveRows.assert_called_with(
            QModelIndex(), index+1, index+1
        )
        self.assertEqual(self.model._channels, [])
        channel.conversation.disconnect.assert_called()
        self.model.endRemoveRows.assert_called()

    def test_remove_channel_does_nothing_on_nonexistant_channel(self):
        self.model.beginRemoveRows = mock.MagicMock()
        self.model.endRemoveRows = mock.MagicMock()
        channel = mock.MagicMock()
        self.model._channels = [channel]
        self.model._channel_index = mock.MagicMock(return_value=-1)

        self.model._remove_channel("fake_channel")

        self.model.beginRemoveRows.assert_not_called()
        self.assertEqual(self.model._channels, [channel])
        channel.conversation.disconnect.assert_not_called()
        self.model.endRemoveRows.assert_not_called()

    def test_update_available_channels(self):
        self.model._channels = [
            ChannelItem("a", ChannelType.USER),
            ChannelItem("b", ChannelType.USER),
            ChannelItem("c", ChannelType.USER),
            ChannelItem("d", ChannelType.USER)
        ]
        updated_channel_names = {"c", "d", "e", "f"}
        self.model._add_channel = mock.MagicMock()
        self.model._remove_channel = mock.MagicMock()

        self.model.update_available_channels(updated_channel_names)

        self.model._add_channel.assert_has_calls([
            mock.call("e"), mock.call("f")
        ], any_order=True)
        self.model._remove_channel.assert_has_calls([
            mock.call("a"), mock.call("b")
        ], any_order=True)

    def test_add_incoming_message_on_group_channel(self):
        channel_name = "channel"
        channel_type = ChannelType.GROUP
        message = object()
        self.model.group_channel.conversation.add_incoming_message \
            = mock.MagicMock()

        self.model.add_incoming_message(channel_name, channel_type, message)

        self.model.group_channel.conversation.add_incoming_message\
            .assert_called_with(message)

    def test_add_incoming_message_on_user_channel(self):
        channel_name = "channel"
        channel_type = ChannelType.USER
        message = object()
        channel = mock.MagicMock()
        self.model._channels = [channel]
        self.model._channel_index = mock.MagicMock(return_value=0)

        self.model.add_incoming_message(channel_name, channel_type, message)

        channel.conversation.add_incoming_message.assert_called_with(message)

    def test_add_incoming_message_ignore_nonexistant_channel(self):
        channel_name = "channel"
        channel_type = ChannelType.USER
        message = object()
        channel = mock.MagicMock()
        self.model._channels = [channel]
        self.model._channel_index = mock.MagicMock(return_value=-1)
        self.model.group_channel.conversation.add_incoming_message \
            = mock.MagicMock()

        self.model.add_incoming_message(channel_name, channel_type, message)

        channel.conversation.add_incoming_message.assert_not_called()
        self.model.group_channel.conversation.add_incoming_message \
            .assert_not_called()


class TestChannelsModelData(TestCase):
    channel1 = ChannelItem(name="one", type=ChannelType.USER, changed=False)
    channel2 = ChannelItem(name="two", type=ChannelType.USER, changed=True)
    group_channel_name = "group"

    def setUp(self):
        self.model = ChannelsModel(self.group_channel_name)
        self.model._channels = [self.channel1, self.channel2]

    def test_data(self):
        cases = (
            (0, 0, ChannelItemRole.NAME, self.model.group_channel.name),
            (0, 0, ChannelItemRole.CONVERSATION,
                self.model.group_channel.conversation),
            (0, 0, ChannelItemRole.CHANNEL_TYPE,
                self.model.group_channel.type),
            (0, 0, ChannelItemRole.CHANGED, self.model.group_channel.changed),
            (1, 0, ChannelItemRole.NAME, self.channel1.name),
            (1, 0, ChannelItemRole.CONVERSATION, self.channel1.conversation),
            (1, 0, ChannelItemRole.CHANNEL_TYPE, self.channel1.type),
            (1, 0, ChannelItemRole.CHANGED, self.channel1.changed),
            (2, 0, ChannelItemRole.NAME, self.channel2.name),
            (2, 0, ChannelItemRole.CONVERSATION, self.channel2.conversation),
            (2, 0, ChannelItemRole.CHANNEL_TYPE, self.channel2.type),
            (2, 0, ChannelItemRole.CHANGED, self.channel2.changed)
        )

        for row, column, role, expected in cases:
            with self.subTest(row=row, column=column, role=role,
                              expected=expected):
                index = self.model.createIndex(row, column)
                self.assertEqual(self.model.data(index, role), expected)

    def test_data_return_none_for_invalid_index(self):
        cases = (
            (-1, 0, ChannelItemRole.NAME, None),
            (-1, 0, ChannelItemRole.CONVERSATION, None),
            (-1, 0, ChannelItemRole.CHANNEL_TYPE, None),
            (-1, 0, ChannelItemRole.CHANGED, None),
            (3, 0, ChannelItemRole.NAME, None),
            (3, 0, ChannelItemRole.CONVERSATION, None),
            (3, 0, ChannelItemRole.CHANNEL_TYPE, None),
            (3, 0, ChannelItemRole.CHANGED, None)
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
            (0, 0, Qt.DisplayRole, None),
            (1, 0, Qt.DisplayRole, None),
            (1, 0, Qt.DisplayRole, None),
            (1, 0, Qt.DisplayRole, None),
            (1, 0, Qt.DisplayRole, None),
            (2, 0, Qt.DisplayRole, None),
            (2, 0, Qt.DisplayRole, None),
            (2, 0, Qt.DisplayRole, None),
            (2, 0, Qt.DisplayRole, None)
        )

        for row, column, role, expected in cases:
            with self.subTest(row=row, column=column, role=role,
                              expected=expected):
                index = self.model.createIndex(row, column)
                self.assertEqual(self.model.data(index, role), expected)
