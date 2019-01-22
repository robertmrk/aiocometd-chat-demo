import QtQuick 2.11
import QtQuick.Window 2.4
import QtQuick.Controls 2.4
import QtQuick.Layouts 1.4
import ChannelsModel 1.0
import ConversationModel 1.0

Pane {
    id: root
    property ChannelsModel model
    property alias currentIndex: channelsView.currentIndex
    property ConversationModel currentConversation

    padding: 0
    background: Rectangle {color: root.palette.mid}

    ListView {
        id: channelsView
        anchors.fill: parent
        spacing: 0
        focus: true
        boundsBehavior: Flickable.StopAtBounds
        model: root.model

        ScrollBar.vertical: ScrollBar {}

        delegate: Rectangle {
            id: delegateRoot
            color: ListView.isCurrentItem ? root.palette.highlight :
                (hovering ? root.palette.dark : "transparent")
            width: parent.width
            height: itemText.height + 12
            property bool hasUnreadMessages: false
            property bool hovering: false

            Connections {
                target: if (model.conversation) model.conversation
                onRowsInserted: {
                    if (!delegateRoot.ListView.isCurrentItem) {
                        delegateRoot.hasUnreadMessages = true
                    }
                }
            }

            ListView.onIsCurrentItemChanged: {
                root.currentConversation = conversation
                delegateRoot.hasUnreadMessages = false
            }

            RowLayout {
                id: delegateRow
                width: parent.width
                anchors.verticalCenter: parent.verticalCenter
                spacing: 6

                Rectangle {
                    id: messageIndicator
                    Layout.leftMargin: 6
                    width: 16; height: 16
                    radius: 8
                    color: root.palette.buttonText
                    opacity: 0.2

                    states: [
                        State {
                            name: "highlighted"
                            when: delegateRoot.hasUnreadMessages
                            PropertyChanges {
                                target: messageIndicator;
                                color: root.palette.highlight
                                opacity: 1
                            }
                        }
                    ]

                    transitions: [
                        Transition {
                            to: "highlighted"
                            PropertyAnimation {
                                target: messageIndicator
                                properties: "opacity"
                                easing.type: Easing.OutElastic
                                duration: 2000
                            }
                            ColorAnimation {
                                target: messageIndicator
                                easing.type: Easing.OutElastic
                                duration: 2000
                            }
                        }
                    ]
                }
                Text {
                    id: itemText
                    Layout.fillWidth: true
                    color: root.palette.buttonText
                    clip: true
                    elide: Text.ElideRight
                    text: name ? name: ""
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    parent.ListView.view.currentIndex = index
                }
                hoverEnabled: true
                onEntered: delegateRoot.hovering = true
                onExited: delegateRoot.hovering = false
            }
        }

        section.property: "type"
        section.criteria: ViewSection.FullString
        section.labelPositioning: ViewSection.InlineLabels
        section.delegate: Rectangle {
            clip: true
            width: parent.width
            height: sectionText.height + 12
            color: root.background.color

            Text {
                id: sectionText
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 6
                anchors.left: parent.left
                anchors.rightMargin: 6
                anchors.right: parent.right
                clip: true
                text: (section == "group") ? qsTr("Group Chat") :
                                             qsTr("Direct Messages")
                color: root.palette.buttonText
            }
        }
    }
}