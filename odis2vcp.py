#!/usr/bin/python
# ODIS2VCP
# Dataset extractor
# Converts datasets from ODIS XML format to VCP XML format
# by Jille

import xml.dom.minidom as mdom

import argparse
import logging
import binascii
import sys
import signal
import os

import resource_rc  # noqa

from PySide2.QtCore import QUrl, Qt, QObject, Property, Signal, Slot
from PySide2.QtGui import QFontDatabase
from PySide2.QtQml import QQmlApplicationEngine
from PySide2.QtWidgets import QFileDialog, QApplication

# variables
dataset_counter = 0
extracted_dataset_counter = 0
_VERSION = "1.0"


def main() -> None:
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="ODIS2VCP Dataset extractor v%s" % _VERSION)

        parser.add_argument("-i", "--input", required=True, help="Input file path")
        parser.add_argument("-f", "--fmt", required=False, help="Output format: vcp (default) or raw.")
        parser.add_argument("-d", "--desc", required=True, help="Output file description. E.g. \"Seat Leon 2016\"")

        parser.add_argument("-v", "--verbose", action='count', default=0, help="Be more verbose")
        parser.add_argument("-q", "--quiet", action='count', default=0, help="Be less verbose")

        args = parser.parse_args()

        level = logging.WARN + (args.quiet - args.verbose) * 10

        logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")

        _run(args.fmt, args.desc, args.input)
    else:
        _run_gui()


class _Model(QObject):
    versionChanged = Signal(str)
    isValidChanged = Signal(bool)

    pathChanged = Signal(str)
    descriptionChanged = Signal(str)
    isRawChanged = Signal(str)

    logChanged = Signal(str)

    def __init__(self):
        self.__path = ""
        self.__description = ""

        self.__is_raw = False

        self.__log = ""

        super().__init__()

        self.pathChanged.connect(self.__check_valid)
        self.descriptionChanged.connect(self.__check_valid)

    @Property(str, notify=versionChanged)
    def version(self):
        return _VERSION

    @Property(bool, notify=isValidChanged)
    def isValid(self):
        return bool(self.__path) and bool(self.__description)

    def __check_valid(self):
        self.isValidChanged.emit(self.isValid)

    @Property(str, notify=pathChanged)
    def path(self):
        return self.__path

    @path.setter
    def set_path(self, value):
        self.__path = value
        self.description = os.path.splitext(os.path.basename(value))[0]
        self.pathChanged.emit(value)

    @Property(str, notify=descriptionChanged)
    def description(self):
        return self.__description

    @description.setter
    def set_description(self, value):
        self.__description = value
        self.descriptionChanged.emit(value)

    @Property(bool, notify=isRawChanged)
    def isRaw(self):
        return self.__is_raw

    @isRaw.setter
    def set_isRaw(self, value):
        self.__is_raw = value
        self.isRawChanged.emit(value)

    @Property(str, notify=logChanged)
    def log(self):
        return self.__log

    @log.setter
    def set_log(self, value):
        self.__log = value
        self.logChanged.emit(value)

    @Slot()
    def browse(self):
        path, filter_ = QFileDialog.getOpenFileName(None, "Choose ODIS file", "", "*.xml;;*.txt;;*.*")

        if path:
            self.path = path

    @Slot()
    def run(self):
        if not self.isValid:
            return

        _run(self.__is_raw and "raw" or "vcp", self.__description, self.__path)


class _LogHandler(logging.Handler):
    def __init__(self, model):
        self.__model = model
        super().__init__()

    def emit(self, record):
        self.__model.log += self.format(record) + "\n"


def _run_gui():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setOrganizationName("NiiFAQ")
    QApplication.setOrganizationDomain("niifaq.ru")

    app = QApplication(sys.argv)

    engine = QQmlApplicationEngine()

    model = _Model()
    handler = _LogHandler(model)

    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    fixed_font = QFontDatabase.systemFont(QFontDatabase.FixedFont)

    root_context = engine.rootContext()

    root_context.setContextProperty("_fixedFont", fixed_font)
    root_context.setContextProperty("_model", model)

    engine.load(QUrl("qrc:/main.qml"))

    if len(engine.rootObjects()) == 0:
        return 1

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        app.shutdown()


def _run(file_output_format, description, path):
    try:
        _parse_small_oe_file(file_output_format, description, path)
    except Exception:
        logging.exception("Fatal error")
        return

    if file_output_format == "raw":
        logging.info(
            "%s of %s datasets extracted to %s format",
            extracted_dataset_counter, dataset_counter, file_output_format
        )
    else:
        logging.info("%s of %s datasets extracted to VCP format", extracted_dataset_counter, dataset_counter)


# extract dataset to a raw export of the dataset
def _extract_to_raw(dataset, filename, diagnostic_address):
    global extracted_dataset_counter
    extracted_dataset_counter = extracted_dataset_counter + 1

    filename = diagnostic_address + " " + filename + ".bin"

    logging.info("Extracting raw data to \"%s\"", filename)

    output_file = open(filename, "wb")
    binary_data = binascii.unhexlify(dataset)
    output_file.write(binary_data)

    output_file.close()


# extract dataset to VCP dataset XML format
def _convert_to_vcp(dataset_data, diagnostic_address, start_address, zdc_name, zdc_version, login, filename):
    global extracted_dataset_counter
    extracted_dataset_counter = extracted_dataset_counter + 1

    doc = mdom.Document()
    root = doc.createElement("SW-CNT")
    doc.appendChild(root)

    ident = doc.createElement("IDENT")
    root.appendChild(ident)

    login_data = doc.createElement("LOGIN")
    dateiid = doc.createElement("DATEIID")
    version_inhalt = doc.createElement("VERSION-INHALT")

    ident.appendChild(login_data)
    ident.appendChild(dateiid)
    ident.appendChild(version_inhalt)

    login_data.appendChild(doc.createTextNode(login))
    dateiid.appendChild(doc.createTextNode(zdc_name))
    version_inhalt.appendChild(doc.createTextNode(zdc_version))

    datasets = doc.createElement("DATENBEREICHE")
    root.appendChild(datasets)

    dataset = doc.createElement("DATENBEREICH")
    datasets.appendChild(dataset)

    dataset_name = doc.createElement("DATEN-NAME")
    dataset.appendChild(dataset_name)
    dataset_name.appendChild(doc.createTextNode(zdc_name))

    dataset_format = doc.createElement("DATEN-FORMAT-NAME")
    dataset.appendChild(dataset_format)
    dataset_format.appendChild(doc.createTextNode("DFN_HEX"))

    dataset_start = doc.createElement("START-ADR")
    dataset.appendChild(dataset_start)
    dataset_start.appendChild(doc.createTextNode(start_address))

    dataset_raw = dataset_data.replace("0x", "")
    dataset_raw = dataset_raw.replace(",", "")

    # some quick and dirty calculations to determine the right size and string format for file size
    dataset_size_calc = len(dataset_raw.encode('utf-8'))
    dataset_size_calc = dataset_size_calc // 2

    dataset_size = doc.createElement("GROESSE-DEKOMPRIMIERT")
    dataset.appendChild(dataset_size)
    dataset_size.appendChild(doc.createTextNode(str(hex(dataset_size_calc))))

    data_data = doc.createElement("DATEN")
    dataset.appendChild(data_data)
    data_data.appendChild(doc.createTextNode(dataset_data))

    # write xml data
    filename = diagnostic_address + " VCP " + filename + ".xml"

    logging.info("Extracting VCP data to \"%s\"", filename)

    doc.writexml(open(filename, 'w'), indent="  ", addindent="  ", newl='\n')


# Parse single OE XML file
# Print detail of each dataset in small OE XML file
def _parse_small_oe_file(file_output_format, file_prefix, input_file):
    global dataset_counter

    # Open XML document using minidom parser
    DOMTree = mdom.parse(input_file)
    collection = DOMTree.documentElement

    parameter_datas = collection.getElementsByTagName("PARAMETER_DATA")
    for parameter_data in parameter_datas:
        if parameter_data.hasAttribute("DIAGNOSTIC_ADDRESS"):
            diagnostic_address = parameter_data.getAttribute("DIAGNOSTIC_ADDRESS")
            diagnostic_address = diagnostic_address.replace("0x00", "")

            logging.info("Module: %s", diagnostic_address)

        if parameter_data.hasAttribute("START_ADDRESS"):
            start_address = parameter_data.getAttribute("START_ADDRESS")
            logging.info("Start_Address: %s", start_address)

        if parameter_data.hasAttribute("ZDC_NAME"):
            zdc_name = parameter_data.getAttribute("ZDC_NAME")
            logging.info("ZDC Name: %s", zdc_name)

        if parameter_data.hasAttribute("ZDC_VERSION"):
            zdc_version = parameter_data.getAttribute("ZDC_VERSION")
            logging.info("ZDC version: %s", zdc_version)

        if parameter_data.hasAttribute("LOGIN"):
            login = parameter_data.getAttribute("LOGIN")
            logging.info("Login: %s", login)
            filename = start_address + " " + zdc_name + " - " + file_prefix

        dataset_counter = dataset_counter+1
        dataset = parameter_data.childNodes[0].data

        # clean the data from all the 0x and commas
        if file_output_format == "raw":
            dataset = dataset.replace('0x', '')
            dataset = dataset.replace(",", "")
            _extract_to_raw(dataset, filename, diagnostic_address)
        else:
            _convert_to_vcp(dataset, diagnostic_address, start_address, zdc_name, zdc_version, login, filename)


if __name__ == '__main__':
    main()
