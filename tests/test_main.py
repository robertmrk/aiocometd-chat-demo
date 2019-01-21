from unittest import TestCase, mock

import aiocometd_chat_demo.__main__ as main
from aiocometd_chat_demo.chat_service import ChatService
from aiocometd_chat_demo.channels import ChannelsModel
from aiocometd_chat_demo.conversation import ConversationModel


class TestMain(TestCase):
    @mock.patch("aiocometd_chat_demo.__main__.qmlRegisterUncreatableType")
    @mock.patch("aiocometd_chat_demo.__main__.qmlRegisterType")
    def test_register_types(self, register_type, register_uncreatable_type):
        main.register_types()

        register_type.assert_has_calls([
            mock.call(ConversationModel, "ChatDemo", 1, 0, "Conversation"),
            mock.call(ChatService, "ChatService", 1, 0, "ChatService")
        ], any_order=True)
        register_uncreatable_type.assert_has_calls([
            mock.call(ChannelsModel, "ChannelsModel", 1, 0,
                      "ChannelsModel",
                      "ChannelsModel can't be created in QML!"),
            mock.call(ConversationModel, "ConversationModel", 1, 0,
                      "ConversationModel",
                      "ConversationModel can't be created in QML!")
        ], any_order=True)

    @mock.patch("aiocometd_chat_demo.__main__.sys")
    @mock.patch("aiocometd_chat_demo.__main__.QQmlApplicationEngine")
    @mock.patch("aiocometd_chat_demo.__main__.register_types")
    @mock.patch("aiocometd_chat_demo.__main__.asyncio")
    @mock.patch("aiocometd_chat_demo.__main__.QEventLoop")
    @mock.patch("aiocometd_chat_demo.__main__.QGuiApplication")
    @mock.patch("aiocometd_chat_demo.__main__.logging")
    def test_main(self, logging_mod, gui_app_cls, event_loop_cls, asyncio_mod,
                  register_types_func, engine_cls, sys_mod):
        sys_mod.argv = []
        gui_app = mock.MagicMock()
        gui_app_cls.return_value = gui_app
        event_loop = mock.MagicMock()
        event_loop_cls.return_value = event_loop
        engine = engine_cls.return_value

        main.main()

        logging_mod.basicConfig.assert_called_with(level=logging_mod.INFO)
        gui_app_cls.assert_called_with(["--style", main.QUICK_CONTROLS2_STYLE])
        event_loop_cls.assert_called_with(gui_app)
        asyncio_mod.set_event_loop.assert_called_with(event_loop)
        register_types_func.assert_called()
        engine_cls.assert_called()
        engine.load.assert_called_with(main.MAIN_QML_PATH)
        event_loop.__enter__.assert_called()
        event_loop.__exit__.assert_called()
        event_loop.run_forever.assert_called()
