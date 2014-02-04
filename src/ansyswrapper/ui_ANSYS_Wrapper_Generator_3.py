# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'C:\Projects_KRL\OpenMDAO\Plugins\Plugin GUIs\ANSYS_Wrapper_Generator_3.ui'
#
# Created: Tue Jun 18 08:52:06 2013
#      by: PyQt4 UI code generator 4.9.6
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(583, 213)
        Dialog.setMinimumSize(QtCore.QSize(583, 213))
        Dialog.setMaximumSize(QtCore.QSize(583, 213))
        Dialog.setSizeGripEnabled(False)
        self.gridLayout_2 = QtGui.QGridLayout(Dialog)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.groupBox = QtGui.QGroupBox(Dialog)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.groupBox.setFont(font)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.layoutWidget = QtGui.QWidget(self.groupBox)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 30, 521, 111))
        self.layoutWidget.setObjectName(_fromUtf8("layoutWidget"))
        self.gridLayout = QtGui.QGridLayout(self.layoutWidget)
        self.gridLayout.setMargin(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.genWrapName = QtGui.QLineEdit(self.layoutWidget)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.genWrapName.setFont(font)
        self.genWrapName.setObjectName(_fromUtf8("genWrapName"))
        self.gridLayout.addWidget(self.genWrapName, 3, 1, 1, 1)
        self.label_3 = QtGui.QLabel(self.layoutWidget)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.label_3.setFont(font)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout.addWidget(self.label_3, 3, 0, 1, 1)
        self.label_2 = QtGui.QLabel(self.layoutWidget)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.label_2.setFont(font)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 1, 2, 3, 1)
        self.label = QtGui.QLabel(self.layoutWidget)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.label.setFont(font)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridLayout.addWidget(self.label, 1, 0, 1, 1)
        self.label_4 = QtGui.QLabel(self.layoutWidget)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.label_4.setFont(font)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1)
        self.ansysFileName = QtGui.QLineEdit(self.layoutWidget)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.ansysFileName.setFont(font)
        self.ansysFileName.setObjectName(_fromUtf8("ansysFileName"))
        self.gridLayout.addWidget(self.ansysFileName, 2, 1, 1, 1)
        self.dirBrowse = QtGui.QPushButton(self.layoutWidget)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.dirBrowse.setFont(font)
        self.dirBrowse.setObjectName(_fromUtf8("dirBrowse"))
        self.gridLayout.addWidget(self.dirBrowse, 1, 3, 1, 1)
        self.ansysFileDir = QtGui.QLineEdit(self.layoutWidget)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.ansysFileDir.setFont(font)
        self.ansysFileDir.setObjectName(_fromUtf8("ansysFileDir"))
        self.gridLayout.addWidget(self.ansysFileDir, 1, 1, 1, 1)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.ansysVer = QtGui.QLineEdit(self.layoutWidget)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.ansysVer.setFont(font)
        self.ansysVer.setObjectName(_fromUtf8("ansysVer"))
        self.horizontalLayout.addWidget(self.ansysVer)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 1, 1, 1)
        self.nameBrowse = QtGui.QPushButton(self.layoutWidget)
        font = QtGui.QFont()
        font.setPointSize(8)
        self.nameBrowse.setFont(font)
        self.nameBrowse.setObjectName(_fromUtf8("nameBrowse"))
        self.gridLayout.addWidget(self.nameBrowse, 2, 3, 1, 1)
        self.generateWrap = QtGui.QPushButton(self.groupBox)
        self.generateWrap.setGeometry(QtCore.QRect(410, 160, 121, 21))
        font = QtGui.QFont()
        font.setPointSize(8)
        self.generateWrap.setFont(font)
        self.generateWrap.setObjectName(_fromUtf8("generateWrap"))
        self.gridLayout_2.addWidget(self.groupBox, 0, 0, 1, 1)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)
        Dialog.setTabOrder(self.ansysVer, self.ansysFileDir)
        Dialog.setTabOrder(self.ansysFileDir, self.dirBrowse)
        Dialog.setTabOrder(self.dirBrowse, self.ansysFileName)
        Dialog.setTabOrder(self.ansysFileName, self.nameBrowse)
        Dialog.setTabOrder(self.nameBrowse, self.genWrapName)
        Dialog.setTabOrder(self.genWrapName, self.generateWrap)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "ANSYS Wrapper Generator", None))
        self.groupBox.setTitle(_translate("Dialog", "ANSYS Wrapper Generator", None))
        self.label_3.setText(_translate("Dialog", "Generated Wrapper Name:", None))
        self.label_2.setText(_translate("Dialog", "ANSYS File Name:", None))
        self.label.setText(_translate("Dialog", "ANSYS File Directory:", None))
        self.label_4.setText(_translate("Dialog", "ANSYS Version:", None))
        self.dirBrowse.setText(_translate("Dialog", "Browse...", None))
        self.nameBrowse.setText(_translate("Dialog", "Browse...", None))
        self.generateWrap.setText(_translate("Dialog", "Generate Wrapper", None))

