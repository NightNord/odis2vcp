resource_rc.py: resource.qrc main.qml qtquickcontrols2.conf
	pyside2-rcc resource.qrc -o resource_rc.py

run: resource_rc.py
	./odis2vcp.py
