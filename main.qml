import QtQuick 2.14
import QtQuick.Dialogs 1.0
import QtQuick.Controls 2.14
import QtQuick.Controls.Material 2.14
import QtQuick.Layouts 1.14

ApplicationWindow {
	id: window
	visible: true

	Material.theme: Material.Dark
	Material.accent: Material.Indigo

	title: "ODIS2VCP Dataset Extractor v" + _model.version
	
	minimumWidth: layout.Layout.minimumWidth
	minimumHeight: layout.Layout.minimumHeight

	width: layout.implicitWidth
	height: layout.implicitHeight

	maximumWidth: 1000
	maximumHeight: 1000

	ColumnLayout {
		id: layout
		anchors.fill: parent

		GridLayout {
			columns: 2
			Layout.margins: 30

			TextField {
				Layout.fillWidth: true
				Layout.preferredWidth: 400
				Layout.minimumWidth: 150

				text: _model.path
				onTextEdited: _model.path = text

				placeholderText: "Input File"
			}

			Button {
				text: "&Browse"

				onClicked: _model.browse()
			}

			TextField {
				Layout.fillWidth: true
				placeholderText: "Ouput File Suffix"

				text: _model.description
				onTextEdited: _model.description = text
			}
			RowLayout {
				Label { text: "Raw:" }
				Switch {
					checked: _model.isRaw
					onToggled: _model.isRaw = checked
				}
			}
		}

		Button {
			Layout.alignment: Qt.AlignHCenter
			Layout.preferredWidth: window.width / 1.5
			text: "Run"
			enabled: _model.isValid

			onClicked: _model.run()
		}

		Label {
			Layout.leftMargin: 30
			text: "Log"
		}

		ScrollView {
			Layout.leftMargin: 20
			Layout.rightMargin: 20
			Layout.bottomMargin: 10

			Layout.fillWidth: true
			Layout.fillHeight: true

			Layout.minimumHeight: 200
			Layout.preferredHeight: 300

			TextArea {
				readOnly: true
				text: _model.log
				font: _fixedFont
				textMargin: 10
				color: "grey"
				wrapMode: TextEdit.NoWrap
			}

			background: Rectangle {
				color: "black"
				border.color: Material.accent
			}
		}
	}
}
