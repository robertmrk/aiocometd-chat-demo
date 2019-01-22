import QtQuick 2.11
import QtQuick.Window 2.4
import QtQuick.Controls 2.4
import QtQuick.Layouts 1.4

Item {
    id: root
    property string username
    property bool sentMessage: model.sender == root.username
    width: parent.width
    height: childrenRect.height

    BorderImage {
        id: bubbleImage
        property int horizontalPadding: parent.width -
            Math.max(messageText.contentWidth, headerTextLayout.width) - 12
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.leftMargin: !sentMessage ? 0 : horizontalPadding
        anchors.rightMargin: sentMessage ? 0 : horizontalPadding
        height: textLayout.height + 18
        border { left: 10; top: 10; right: 10; bottom: 12 }
        smooth: true
        source: sentMessage ? "images/chat-right.svg" : "images/chat-left.svg"
        opacity: 0.5
    }

    ColumnLayout {
        id: textLayout
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: 6
        anchors.leftMargin: 6
        anchors.rightMargin: 6

        RowLayout {
            id: headerTextLayout
            Layout.leftMargin: sentMessage ? bubbleImage.horizontalPadding : 0

            Label {
                id: senderText
                text: sender
                font.bold: true
            }
            Label {
                id: timeText
                Layout.alignment: Qt.AlignBottom
                text: Qt.formatTime(time)
                font.pointSize: senderText.font.pointSize - 4
                font.italic: true
            }
        }
        Label {
            id: messageText
            leftPadding: sentMessage ? bubbleImage.horizontalPadding : 0
            Layout.maximumWidth: parent.width
            wrapMode: Text.WordWrap
            text: contents ? contents : ""
        }
    }
}