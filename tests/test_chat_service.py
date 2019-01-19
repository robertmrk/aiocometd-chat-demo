from datetime import datetime

from asynctest import TestCase, mock

from aiocometd_chat_demo.chat_service import ChatService, ChannelsModel, \
    LOGGER as chat_service_logger, ChatMessage, ChannelType


class TestChatService(TestCase):
    def setUp(self):
        self.service = ChatService()
        self.logger = chat_service_logger
        self.logger_name = "aiocometd_chat_demo.chat_service"

    def test_url(self):
        self.service.url_changed = mock.MagicMock()
        url = "url"

        self.service.url = url

        self.assertEqual(self.service.url, url)
        self.service.url_changed.emit.assert_called_with(url)

    def test_username(self):
        self.service.username_changed = mock.MagicMock()
        username = "name"

        self.service.username = username

        self.assertEqual(self.service.username, username)
        self.service.username_changed.emit.assert_called_with(username)

    def test_channels_model(self):
        self.service.channels_model_changed = mock.MagicMock()
        channels_model = object()

        self.service.channels_model = channels_model

        self.assertEqual(self.service.channels_model, channels_model)
        self.service.channels_model_changed.emit.assert_called_with(
            channels_model
        )

    def test_last_error(self):
        self.service.last_error_changed = mock.MagicMock()
        self.service.error = mock.MagicMock()
        last_error = "error"

        self.service.last_error = last_error

        self.assertEqual(self.service.last_error, last_error)
        self.service.last_error_changed.emit.assert_called_with(last_error)
        self.service.error.emit.assert_called()

    def test_room_channel(self):
        self.assertEqual(self.service._room_channel,
                         "/chat/" + self.service._room_name)

    def test_members_channel(self):
        self.assertEqual(self.service._members_channel,
                         "/members/" + self.service._room_name)

    @mock.patch("aiocometd_chat_demo.chat_service.ChannelsModel")
    @mock.patch("aiocometd_chat_demo.chat_service.CometdClient")
    def test_connect(self, cometd_cls, channels_cls):
        cometd_client = mock.MagicMock()
        cometd_cls.return_value = cometd_client
        channels_model = ChannelsModel("group_name")
        channels_model.message_sending_requested = mock.MagicMock()
        channels_cls.return_value = channels_model
        self.service.url = "url"
        self.service.username = "name"

        self.service.connect_()

        channels_cls.assert_called_with(self.service._room_name)
        channels_model.message_sending_requested.connect.assert_called_with(
            self.service.send_message
        )
        cometd_cls.assert_called_with(
            self.service.url,
            (self.service._members_channel, self.service._room_channel)
        )
        cometd_client.connected.connect.assert_called_with(
            self.service.on_connected
        )
        cometd_client.disconnected.connect.assert_called_with(
            self.service.on_disconnected
        )
        cometd_client.error.connect.assert_has_calls([
            mock.call(self.service.on_error),
            mock.call(self.service.on_disconnected)
        ])
        cometd_client.message_received.connect.assert_called_with(
            self.service.message_received
        )
        cometd_client.connect_.assert_called()

    def test_on_connected(self):
        self.service._client = mock.MagicMock()
        self.service.connected = mock.MagicMock()

        self.service.on_connected()

        self.service._client.publish.assert_called_with(
            self.service._members_service_channel,
            dict(user=self.service.username, room=self.service._room_channel)
        )
        self.service.connected.emit.assert_called()

    def test_on_connected_sets_error_on_no_client(self):
        self.service._client = None
        expected_message = "Uninitialized _client attribute."

        with self.assertLogs(self.logger, "ERROR") as logs:
            self.service.on_connected()

        self.assertEqual(logs.output, [
            f"ERROR:{self.logger_name}:{expected_message}"
        ])
        self.assertEqual(self.service.last_error, expected_message)

    def test_disconnect(self):
        self.service._client = mock.MagicMock()

        self.service.disconnect_()

        self.service._client.disconnect_.assert_called()

    def test_disconnect_does_nothing_if_not_connected(self):
        self.service.disconnect_()

    def test_on_disconnected(self):
        client = mock.MagicMock()
        self.service._client = client
        channels_model = mock.MagicMock()
        self.service._channels_model = channels_model
        self.service.disconnected = mock.MagicMock()

        self.service.on_disconnected()

        client.disconnect.assert_called()
        channels_model.disconnect.assert_called()
        self.service.disconnected.emit.assert_called()
        self.assertIsNone(self.service._client)
        self.assertIsNone(self.service.channels_model)

    def test_on_disconnected_sets_error_on_no_client(self):
        self.service._client = None
        expected_message = "Uninitialized _client attribute."

        with self.assertLogs(self.logger, "ERROR") as logs:
            self.service.on_disconnected()

        self.assertEqual(logs.output, [
            f"ERROR:{self.logger_name}:{expected_message}"
        ])
        self.assertEqual(self.service.last_error, expected_message)

    def test_on_error(self):
        error = ValueError("message")

        with self.assertLogs(self.logger, "ERROR") as logs:
            self.service.on_error(error)

        self.assertEqual(logs.output, [
            f"ERROR:{self.logger_name}:CometD client error: {error!r}"
        ])
        self.assertEqual(self.service.last_error, repr(error))

    @mock.patch("aiocometd_chat_demo.chat_service.datetime")
    def test_message_received_on_chat_message(self, datetime_cls):
        self.service.username = "me"
        other_user = "user"
        datetime_cls.now.return_value = datetime.now()
        channels_model = mock.MagicMock()
        self.service._channels_model = channels_model
        self.service._last_private_message_users.appendleft(other_user)
        cases = (
            ("group message", other_user, None, self.service._room_name,
             ChannelType.GROUP),
            ("private message received", other_user, "private", other_user,
             ChannelType.USER),
            ("private message sent", "me", "private", other_user,
             ChannelType.USER)
        )
        for message_type, user, scope, exp_channel, exp_type in cases:
            with self.subTest(message_type=message_type):
                cometd_chat_message = {
                    "channel": self.service._room_channel,
                    "data": dict(user=user, scope=scope, chat="contents")
                }
                chat_message = ChatMessage(
                    sender=cometd_chat_message["data"]["user"],
                    contents=cometd_chat_message["data"]["chat"],
                    time=datetime_cls.now.return_value
                )

                self.service.message_received(cometd_chat_message)

                channels_model.add_incoming_message.assert_called_with(
                    channel_name=exp_channel,
                    channel_type=exp_type,
                    message=chat_message
                )

    def test_message_received_on_members_message(self):
        channels_model = mock.MagicMock()
        self.service._channels_model = channels_model
        other_user = "user"
        self.service.username = "me"
        cometd_message = {
            "data": [other_user, self.service.username],
            "channel": "/members/demo"
        }

        self.service.message_received(cometd_message)

        channels_model.update_available_channels.assert_called_with(
            set((other_user, ))
        )

    def test_message_received_ignores_unrecognized_channels(self):
        channels_model = mock.MagicMock()
        self.service._channels_model = channels_model
        cometd_message = {
            "data": {},
            "channel": "/unrecognized_channel"
        }

        self.service.message_received(cometd_message)

        channels_model.update_available_channels.assert_not_called()
        channels_model.add_incoming_message.assert_not_called()
        self.assertEqual(self.service.last_error, "")

    def test_message_received_sets_error_on_no_channels_model(self):
        self.service._channels_model = None
        expected_message = "Uninitialized channels_model attribute."

        with self.assertLogs(self.logger, "ERROR") as logs:
            self.service.message_received({})

        self.assertEqual(logs.output, [
            f"ERROR:{self.logger_name}:{expected_message}"
        ])
        self.assertEqual(self.service.last_error, expected_message)

    def test_send_message_group_channel(self):
        self.service.username = "me"
        contents = "message contents"
        self.service._client = mock.MagicMock()

        self.service.send_message(self.service._room_name,
                                  ChannelType.GROUP,
                                  contents)

        self.service._client.publish.assert_called_with(
            self.service._room_channel,
            dict(user=self.service.username, chat=contents)
        )

    def test_send_message_user_channel(self):
        self.service.username = "me"
        contents = "message contents"
        other_user = "user"
        self.service._client = mock.MagicMock()

        self.service.send_message(other_user,
                                  ChannelType.USER,
                                  contents)

        self.service._client.publish.assert_called_with(
            "/service/privatechat",
            dict(
                room=self.service._room_channel,
                user=self.service.username,
                chat=contents,
                peer=other_user
            )
        )

    def test_send_message_sets_error_on_no_client(self):
        self.service._client = None
        expected_message = "Uninitialized _client attribute."

        with self.assertLogs(self.logger, "ERROR") as logs:
            self.service.send_message("user", ChannelType.USER, "contents")

        self.assertEqual(logs.output, [
            f"ERROR:{self.logger_name}:{expected_message}"
        ])
        self.assertEqual(self.service.last_error, expected_message)
