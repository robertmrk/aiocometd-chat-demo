import QtQuick 2.11
import QtQuick.Window 2.4
import QtQuick.Controls 2.4
import QtQuick.Controls 1.4 as Controls1
import QtQuick.Layouts 1.4
import QtQuick.Dialogs 1.3
import ChatDemo 1.0
import ChatService 1.0

Controls1.SplitView {
    property alias channelsModel: channelsView.model
    property alias username: conversationView.username
    orientation: Qt.Horizontal

    ChannelsView {
        id: channelsView
        width: 200
        Layout.minimumWidth: 100
    }

    ConversationView {
        id: conversationView
        height: parent.height
        Layout.fillWidth: true
        Layout.minimumWidth: 100
        model: channelsView.currentConversation
    }
}
