import QtQuick 2.11
import QtQuick.Window 2.4
import QtQuick.Controls 2.4
import ChatService 1.0

ApplicationWindow {
    id: root
    width: 640; height: 480
    minimumWidth: 300; minimumHeight: 300
    visible: true
    title: qsTr("aiocometd chat demo")

    ChatService {
        id: chatService
        username: connectionPage.username
        url: connectionPage.url
        onConnected: {
             swipeView.currentIndex = 1;
             connectionPage.state = "connected"
        }
        onDisconnected: {
             swipeView.currentIndex = 0;
             connectionPage.state = "error"
        }
        onError: {
            connectionPage.state = "error"
        }
    }

    PageSwitcher {
        id: swipeView
        anchors.fill: parent

        ConnectionPage {
            id: connectionPage
            onConnect: {
                connectionPage.state = "connecting"
                chatService.connect_()
            }
            errorText: chatService.last_error
        }

        ChatPage{
            id: chatPage
            channelsModel: chatService.channels_model
            username: connectionPage.username
        }
    }
}