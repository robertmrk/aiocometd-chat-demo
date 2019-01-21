import QtQuick 2.11
import QtQuick.Controls 2.4
import QtQuick.Layouts 1.4

Pane {
    id: root
    property alias url: urlField.text
    property alias username: usernameField.text
    property string errorText
    property bool connectionEnabled: true
    signal connect

    padding: 12
    background: Rectangle {color: root.palette.window}

    states: [
        State {
            name: "connecting"
            PropertyChanges { target: busyIndicator; running: true }
            PropertyChanges { target: root; connectionEnabled: false }
        },
        State {
            name: "connected"
            PropertyChanges { target: root; connectionEnabled: false }
        },
        State {
            name: "error"
            PropertyChanges { target: errorLabel; text: root.errorText}
            PropertyChanges { target: errorFrame; visible: true}
        }
    ]

    ColumnLayout {
        anchors.fill: parent

        Label {
            id: introLabel

            Layout.alignment: Qt.AlignHCenter
            Layout.fillWidth: true

            text: qsTr("aiocometd_chat_demo is a client application for the CometD \
             chat service demo. \
             It demonstrates the usage of \
             <a href='https://github.com/robertmrk/aiocometd'>aiocometd</a> \
             in a GUI application with \
             <a href='https://www.riverbankcomputing.com/software/pyqt/intro'>PyQt5</a> and \
             <a href='http://doc.qt.io/qt-5/qmlapplications.html'>QML</a>. \
             To use the application, first create/run a container from the \
             <a href='https://hub.docker.com/r/robertmrk/cometd-demos'>\
             cometd-demos</a> docker image.")
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignJustify
            onLinkActivated: Qt.openUrlExternally(link)
            elide: Text.ElideRight
            font.pointSize: 10
        }

        GridLayout {
            columns: 2
            rows: 2

            Label {
                text: qsTr("URL")
                horizontalAlignment: Text.AlignRight
                Layout.fillWidth: true
            }
            TextField {
                id: urlField
                text: "http://localhost:8080/cometd"
                Layout.preferredWidth: 300
                Layout.fillWidth: true
                placeholderText: qsTr("chat service URL")
                validator: RegExpValidator{ regExp: /.+/ }
            }

            Label {
                text: qsTr("Username")
                horizontalAlignment: Text.AlignRight
                Layout.fillWidth: true
            }
            TextField {
                id: usernameField
                text: "user"
                Layout.preferredWidth: 300
                Layout.fillWidth: true
                placeholderText: qsTr("username")
                validator: RegExpValidator{ regExp: /\w+/ }
            }
        }

        Item {
            height: 100
            Layout.fillWidth: true

            BusyIndicator {
                id: busyIndicator
                anchors.centerIn: parent
                running: false
            }
            GroupBox {
                id: errorFrame
                visible: false
                anchors.fill: parent
                title: qsTr("Connection error:")
                padding: 0

                ScrollView {
                    id: errorView
                    anchors.fill: parent
                    clip: true
                    padding: 0

                    Label {
                        id: errorLabel
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignJustify
                        onLinkActivated: Qt.openUrlExternally(link)
                        color: "red"
                    }
                }
            }
        }

        Button {
            id: connectButton
            Layout.fillHeight: false
            Layout.alignment: Qt.AlignHCenter

            text: qsTr("Connect")
            enabled: url.length && username.length && root.connectionEnabled
            onClicked: root.connect()
        }
    }
}
