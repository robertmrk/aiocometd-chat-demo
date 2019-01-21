"""Application entry point"""
import sys
import asyncio
import logging
import os.path

from quamash import QEventLoop  # type: ignore
# pylint: disable=no-name-in-module
from PyQt5.QtGui import QGuiApplication  # type: ignore
from PyQt5.QtQml import (  # type: ignore
    QQmlApplicationEngine,
    qmlRegisterType,
    qmlRegisterUncreatableType
)
# pylint: enable=no-name-in-module

from aiocometd_chat_demo.chat_service import ChatService
from aiocometd_chat_demo.channels import ChannelsModel
from aiocometd_chat_demo.conversation import ConversationModel


#: Name of the main QML file
MAIN_QML_FILE = "main.qml"
#: Directory path of file
HERE = os.path.dirname(os.path.abspath(__file__))
#: Path of the main QML file
MAIN_QML_PATH = os.path.join(HERE, "qml")
#: QML application control style
QUICK_CONTROLS2_STYLE = "imagine"


def register_types() -> None:
    """Register custom QML types"""
    qmlRegisterType(ConversationModel, "ChatDemo", 1, 0, "Conversation")
    qmlRegisterType(ChatService, "ChatService", 1, 0, "ChatService")
    qmlRegisterUncreatableType(ChannelsModel, "ChannelsModel", 1, 0,
                               "ChannelsModel",
                               "ChannelsModel can't be created in QML!")
    qmlRegisterUncreatableType(ConversationModel, "ConversationModel", 1, 0,
                               "ConversationModel",
                               "ConversationModel can't be created in QML!")


def main() -> None:
    """Application entry point"""
    # configure logging
    logging.basicConfig(level=logging.INFO)

    # create the App ant the event loop
    app = QGuiApplication(sys.argv + ["--style", QUICK_CONTROLS2_STYLE])
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    # register custom types
    register_types()

    # create the QML engine
    engine = QQmlApplicationEngine()
    # load the main QML file
    engine.load(MAIN_QML_PATH)

    # start the event loop
    with loop:
        loop.run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
