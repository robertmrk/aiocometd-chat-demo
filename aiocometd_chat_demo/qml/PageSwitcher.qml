import QtQuick 2.11
import QtQuick.Window 2.4
import QtQuick.Controls 2.4

SwipeView {
    id: root
    interactive: false

    contentItem: ListView {
        model: root.contentModel
        interactive: root.interactive
        currentIndex: root.currentIndex

        spacing: root.spacing
        orientation: root.orientation
        snapMode: ListView.SnapOneItem
        boundsBehavior: Flickable.StopAtBounds

        highlightRangeMode: ListView.StrictlyEnforceRange
        preferredHighlightBegin: 0
        preferredHighlightEnd: 0
        highlightMoveDuration: 2000
    }
}
