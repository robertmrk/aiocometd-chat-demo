import QtQuick 2.11
import QtQuick.Window 2.4
import QtQuick.Controls 2.4
import QtQuick.Layouts 1.4
import ConversationModel 1.0

Pane {
    id: root
    property ConversationModel model
    property string username: ""
    background: Rectangle {color: root.palette.window}

    Page {
        anchors.fill: parent

        header: ToolBar {
            id: header

            Label {
                anchors.fill: parent
                anchors.margins: 6
                elide: Text.ElideRight
                anchors.verticalCenter: parent.verticalCenter
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                text: root.model ? root.model.channel : ""
            }
        }

        Rectangle {
            anchors.fill: parent
            color: root.palette.window

            ListView {
                id: conversationView
                spacing: 2
                anchors.fill: parent
                anchors.margins: 6
                model: root.model

                ScrollBar.vertical: ScrollBar { }

                add: Transition {
                    NumberAnimation {
                        properties: "opacity";
                        from: 0; to: 1;
                        duration: 1000
                    }
                }

                delegate: MessageDelegate {
                    username: root.username
                }

                onCountChanged: {
                    var newIndex = count - 1
                    positionViewAtEnd()
                    currentIndex = newIndex
                }
            }
        }

        footer: Pane {
            id: footerItem
            background: Rectangle {color: root.palette.window}
            padding: 6

            TextField {
                id: messageField
                anchors.fill: parent
                placeholderText: qsTr("Message ") +
                                 (root.model ? root.model.channel: "")
                focus: true
                onAccepted: {
                    if (root.model && messageField.text.length) {
                        root.model.sendMessage(messageField.text)
                        messageField.text = ""
                    }
                }
            }
        }
    }
}