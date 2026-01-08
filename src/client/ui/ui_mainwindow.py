# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ui_main.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QProgressBar, QPushButton, QSizePolicy, QSlider,
    QSpacerItem, QSpinBox, QStackedWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1000, 700)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.stackedWidget = QStackedWidget(self.centralwidget)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.mainScreen = QWidget()
        self.mainScreen.setObjectName(u"mainScreen")
        self.verticalLayout_2 = QVBoxLayout(self.mainScreen)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.label = QLabel(self.mainScreen)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignCenter)

        self.verticalLayout_2.addWidget(self.label)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer)

        self.label_2 = QLabel(self.mainScreen)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setAlignment(Qt.AlignCenter)

        self.verticalLayout_2.addWidget(self.label_2)

        self.label_3 = QLabel(self.mainScreen)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setAlignment(Qt.AlignCenter)

        self.verticalLayout_2.addWidget(self.label_3)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_2)

        self.groupBox = QGroupBox(self.mainScreen)
        self.groupBox.setObjectName(u"groupBox")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.modeComboBox = QComboBox(self.groupBox)
        self.modeComboBox.addItem("")
        self.modeComboBox.addItem("")
        self.modeComboBox.setObjectName(u"modeComboBox")

        self.verticalLayout_3.addWidget(self.modeComboBox)

        self.localModeWidget = QWidget(self.groupBox)
        self.localModeWidget.setObjectName(u"localModeWidget")
        self.horizontalLayout = QHBoxLayout(self.localModeWidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.startLocalServerBtn = QPushButton(self.localModeWidget)
        self.startLocalServerBtn.setObjectName(u"startLocalServerBtn")

        self.horizontalLayout.addWidget(self.startLocalServerBtn)

        self.localStatusLabel = QLabel(self.localModeWidget)
        self.localStatusLabel.setObjectName(u"localStatusLabel")

        self.horizontalLayout.addWidget(self.localStatusLabel)

        self.portSpinBox = QSpinBox(self.localModeWidget)
        self.portSpinBox.setObjectName(u"portSpinBox")
        self.portSpinBox.setMinimum(1024)
        self.portSpinBox.setMaximum(65535)
        self.portSpinBox.setValue(8080)

        self.horizontalLayout.addWidget(self.portSpinBox)


        self.verticalLayout_3.addWidget(self.localModeWidget)

        self.remoteModeWidget = QWidget(self.groupBox)
        self.remoteModeWidget.setObjectName(u"remoteModeWidget")
        self.gridLayout = QGridLayout(self.remoteModeWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.label_4 = QLabel(self.remoteModeWidget)
        self.label_4.setObjectName(u"label_4")

        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1)

        self.hostLineEdit = QLineEdit(self.remoteModeWidget)
        self.hostLineEdit.setObjectName(u"hostLineEdit")

        self.gridLayout.addWidget(self.hostLineEdit, 0, 1, 1, 1)

        self.label_5 = QLabel(self.remoteModeWidget)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout.addWidget(self.label_5, 1, 0, 1, 1)

        self.remotePortSpinBox = QSpinBox(self.remoteModeWidget)
        self.remotePortSpinBox.setObjectName(u"remotePortSpinBox")
        self.remotePortSpinBox.setMinimum(1024)
        self.remotePortSpinBox.setMaximum(65535)
        self.remotePortSpinBox.setValue(8080)

        self.gridLayout.addWidget(self.remotePortSpinBox, 1, 1, 1, 1)

        self.connectBtn = QPushButton(self.remoteModeWidget)
        self.connectBtn.setObjectName(u"connectBtn")

        self.gridLayout.addWidget(self.connectBtn, 2, 0, 1, 2)

        self.remoteStatusLabel = QLabel(self.remoteModeWidget)
        self.remoteStatusLabel.setObjectName(u"remoteStatusLabel")

        self.gridLayout.addWidget(self.remoteStatusLabel, 3, 0, 1, 2)


        self.verticalLayout_3.addWidget(self.remoteModeWidget)


        self.verticalLayout_2.addWidget(self.groupBox)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_3)

        self.goToProcessingBtn = QPushButton(self.mainScreen)
        self.goToProcessingBtn.setObjectName(u"goToProcessingBtn")
        self.goToProcessingBtn.setMinimumSize(QSize(0, 40))

        self.verticalLayout_2.addWidget(self.goToProcessingBtn)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.aboutProjectBtn = QPushButton(self.mainScreen)
        self.aboutProjectBtn.setObjectName(u"aboutProjectBtn")

        self.horizontalLayout_2.addWidget(self.aboutProjectBtn)

        self.licenseBtn = QPushButton(self.mainScreen)
        self.licenseBtn.setObjectName(u"licenseBtn")

        self.horizontalLayout_2.addWidget(self.licenseBtn)

        self.aboutAppBtn = QPushButton(self.mainScreen)
        self.aboutAppBtn.setObjectName(u"aboutAppBtn")

        self.horizontalLayout_2.addWidget(self.aboutAppBtn)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.stackedWidget.addWidget(self.mainScreen)
        self.processingScreen = QWidget()
        self.processingScreen.setObjectName(u"processingScreen")
        self.verticalLayout_4 = QVBoxLayout(self.processingScreen)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.label_6 = QLabel(self.processingScreen)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setAlignment(Qt.AlignCenter)

        self.verticalLayout_4.addWidget(self.label_6)

        self.groupBox_2 = QGroupBox(self.processingScreen)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.gridLayout_2 = QGridLayout(self.groupBox_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.noiseReductionCheck = QCheckBox(self.groupBox_2)
        self.noiseReductionCheck.setObjectName(u"noiseReductionCheck")

        self.gridLayout_2.addWidget(self.noiseReductionCheck, 0, 0, 1, 1)

        self.noiseReductionSlider = QSlider(self.groupBox_2)
        self.noiseReductionSlider.setObjectName(u"noiseReductionSlider")
        self.noiseReductionSlider.setOrientation(Qt.Horizontal)
        self.noiseReductionSlider.setMinimum(1)
        self.noiseReductionSlider.setMaximum(10)
        self.noiseReductionSlider.setValue(5)

        self.gridLayout_2.addWidget(self.noiseReductionSlider, 0, 1, 1, 1)

        self.humRemovalCheck = QCheckBox(self.groupBox_2)
        self.humRemovalCheck.setObjectName(u"humRemovalCheck")

        self.gridLayout_2.addWidget(self.humRemovalCheck, 1, 0, 1, 1)

        self.humFrequencyCombo = QComboBox(self.groupBox_2)
        self.humFrequencyCombo.addItem("")
        self.humFrequencyCombo.addItem("")
        self.humFrequencyCombo.setObjectName(u"humFrequencyCombo")

        self.gridLayout_2.addWidget(self.humFrequencyCombo, 1, 1, 1, 1)

        self.deEsserCheck = QCheckBox(self.groupBox_2)
        self.deEsserCheck.setObjectName(u"deEsserCheck")

        self.gridLayout_2.addWidget(self.deEsserCheck, 2, 0, 1, 1)

        self.deEsserSlider = QSlider(self.groupBox_2)
        self.deEsserSlider.setObjectName(u"deEsserSlider")
        self.deEsserSlider.setOrientation(Qt.Horizontal)
        self.deEsserSlider.setMinimum(1)
        self.deEsserSlider.setMaximum(10)
        self.deEsserSlider.setValue(5)

        self.gridLayout_2.addWidget(self.deEsserSlider, 2, 1, 1, 1)

        self.eqCheck = QCheckBox(self.groupBox_2)
        self.eqCheck.setObjectName(u"eqCheck")

        self.gridLayout_2.addWidget(self.eqCheck, 3, 0, 1, 1)

        self.normalizationCheck = QCheckBox(self.groupBox_2)
        self.normalizationCheck.setObjectName(u"normalizationCheck")

        self.gridLayout_2.addWidget(self.normalizationCheck, 4, 0, 1, 1)

        self.lufsSpinBox = QSpinBox(self.groupBox_2)
        self.lufsSpinBox.setObjectName(u"lufsSpinBox")
        self.lufsSpinBox.setMinimum(-30)
        self.lufsSpinBox.setMaximum(-10)
        self.lufsSpinBox.setValue(-16)

        self.gridLayout_2.addWidget(self.lufsSpinBox, 4, 1, 1, 1)


        self.verticalLayout_4.addWidget(self.groupBox_2)

        self.groupBox_3 = QGroupBox(self.processingScreen)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_5 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.selectFilesBtn = QPushButton(self.groupBox_3)
        self.selectFilesBtn.setObjectName(u"selectFilesBtn")

        self.horizontalLayout_3.addWidget(self.selectFilesBtn)

        self.selectFolderBtn = QPushButton(self.groupBox_3)
        self.selectFolderBtn.setObjectName(u"selectFolderBtn")

        self.horizontalLayout_3.addWidget(self.selectFolderBtn)


        self.verticalLayout_5.addLayout(self.horizontalLayout_3)

        self.fileListWidget = QListWidget(self.groupBox_3)
        self.fileListWidget.setObjectName(u"fileListWidget")

        self.verticalLayout_5.addWidget(self.fileListWidget)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_7 = QLabel(self.groupBox_3)
        self.label_7.setObjectName(u"label_7")

        self.horizontalLayout_4.addWidget(self.label_7)

        self.outputFolderLineEdit = QLineEdit(self.groupBox_3)
        self.outputFolderLineEdit.setObjectName(u"outputFolderLineEdit")

        self.horizontalLayout_4.addWidget(self.outputFolderLineEdit)

        self.browseOutputBtn = QPushButton(self.groupBox_3)
        self.browseOutputBtn.setObjectName(u"browseOutputBtn")

        self.horizontalLayout_4.addWidget(self.browseOutputBtn)


        self.verticalLayout_5.addLayout(self.horizontalLayout_4)

        self.overwriteCheck = QCheckBox(self.groupBox_3)
        self.overwriteCheck.setObjectName(u"overwriteCheck")

        self.verticalLayout_5.addWidget(self.overwriteCheck)


        self.verticalLayout_4.addWidget(self.groupBox_3)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.startProcessingBtn = QPushButton(self.processingScreen)
        self.startProcessingBtn.setObjectName(u"startProcessingBtn")

        self.horizontalLayout_5.addWidget(self.startProcessingBtn)

        self.clearQueueBtn = QPushButton(self.processingScreen)
        self.clearQueueBtn.setObjectName(u"clearQueueBtn")

        self.horizontalLayout_5.addWidget(self.clearQueueBtn)


        self.verticalLayout_4.addLayout(self.horizontalLayout_5)

        self.label_8 = QLabel(self.processingScreen)
        self.label_8.setObjectName(u"label_8")

        self.verticalLayout_4.addWidget(self.label_8)

        self.stackedWidget.addWidget(self.processingScreen)
        self.progressScreen = QWidget()
        self.progressScreen.setObjectName(u"progressScreen")
        self.verticalLayout_6 = QVBoxLayout(self.progressScreen)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.label_9 = QLabel(self.progressScreen)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setAlignment(Qt.AlignCenter)

        self.verticalLayout_6.addWidget(self.label_9)

        self.taskTable = QTableWidget(self.progressScreen)
        if (self.taskTable.columnCount() < 4):
            self.taskTable.setColumnCount(4)
        __qtablewidgetitem = QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        if (self.taskTable.rowCount() < 1):
            self.taskTable.setRowCount(1)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.taskTable.setVerticalHeaderItem(0, __qtablewidgetitem4)
        self.taskTable.setObjectName(u"taskTable")

        self.verticalLayout_6.addWidget(self.taskTable)

        self.groupBox_4 = QGroupBox(self.progressScreen)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.verticalLayout_7 = QVBoxLayout(self.groupBox_4)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.label_10 = QLabel(self.groupBox_4)
        self.label_10.setObjectName(u"label_10")

        self.verticalLayout_7.addWidget(self.label_10)

        self.currentFileProgress = QProgressBar(self.groupBox_4)
        self.currentFileProgress.setObjectName(u"currentFileProgress")
        self.currentFileProgress.setValue(24)

        self.verticalLayout_7.addWidget(self.currentFileProgress)

        self.label_11 = QLabel(self.groupBox_4)
        self.label_11.setObjectName(u"label_11")

        self.verticalLayout_7.addWidget(self.label_11)

        self.totalProgress = QProgressBar(self.groupBox_4)
        self.totalProgress.setObjectName(u"totalProgress")
        self.totalProgress.setValue(45)

        self.verticalLayout_7.addWidget(self.totalProgress)

        self.timeRemainingLabel = QLabel(self.groupBox_4)
        self.timeRemainingLabel.setObjectName(u"timeRemainingLabel")

        self.verticalLayout_7.addWidget(self.timeRemainingLabel)


        self.verticalLayout_6.addWidget(self.groupBox_4)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.pauseTasksBtn = QPushButton(self.progressScreen)
        self.pauseTasksBtn.setObjectName(u"pauseTasksBtn")

        self.horizontalLayout_6.addWidget(self.pauseTasksBtn)

        self.cancelSelectedBtn = QPushButton(self.progressScreen)
        self.cancelSelectedBtn.setObjectName(u"cancelSelectedBtn")

        self.horizontalLayout_6.addWidget(self.cancelSelectedBtn)

        self.clearFinishedBtn = QPushButton(self.progressScreen)
        self.clearFinishedBtn.setObjectName(u"clearFinishedBtn")

        self.horizontalLayout_6.addWidget(self.clearFinishedBtn)


        self.verticalLayout_6.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.openResultsBtn = QPushButton(self.progressScreen)
        self.openResultsBtn.setObjectName(u"openResultsBtn")

        self.horizontalLayout_7.addWidget(self.openResultsBtn)

        self.openLogBtn = QPushButton(self.progressScreen)
        self.openLogBtn.setObjectName(u"openLogBtn")

        self.horizontalLayout_7.addWidget(self.openLogBtn)

        self.goToSpectrogramBtn = QPushButton(self.progressScreen)
        self.goToSpectrogramBtn.setObjectName(u"goToSpectrogramBtn")

        self.horizontalLayout_7.addWidget(self.goToSpectrogramBtn)


        self.verticalLayout_6.addLayout(self.horizontalLayout_7)

        self.stackedWidget.addWidget(self.progressScreen)
        self.emptyScreen = QWidget()
        self.emptyScreen.setObjectName(u"emptyScreen")
        self.verticalLayout_8 = QVBoxLayout(self.emptyScreen)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer_4)

        self.label_12 = QLabel(self.emptyScreen)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setAlignment(Qt.AlignCenter)

        self.verticalLayout_8.addWidget(self.label_12)

        self.label_13 = QLabel(self.emptyScreen)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setAlignment(Qt.AlignCenter)

        self.verticalLayout_8.addWidget(self.label_13)

        self.verticalSpacer_5 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer_5)

        self.stackedWidget.addWidget(self.emptyScreen)

        self.verticalLayout.addWidget(self.stackedWidget)

        self.navWidget = QWidget(self.centralwidget)
        self.navWidget.setObjectName(u"navWidget")
        self.horizontalLayout_8 = QHBoxLayout(self.navWidget)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.mainScreenBtn = QPushButton(self.navWidget)
        self.mainScreenBtn.setObjectName(u"mainScreenBtn")

        self.horizontalLayout_8.addWidget(self.mainScreenBtn)

        self.processingScreenBtn = QPushButton(self.navWidget)
        self.processingScreenBtn.setObjectName(u"processingScreenBtn")

        self.horizontalLayout_8.addWidget(self.processingScreenBtn)

        self.progressScreenBtn = QPushButton(self.navWidget)
        self.progressScreenBtn.setObjectName(u"progressScreenBtn")

        self.horizontalLayout_8.addWidget(self.progressScreenBtn)

        self.emptyScreenBtn = QPushButton(self.navWidget)
        self.emptyScreenBtn.setObjectName(u"emptyScreenBtn")

        self.horizontalLayout_8.addWidget(self.emptyScreenBtn)


        self.verticalLayout.addWidget(self.navWidget)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.stackedWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Audio Processing Application", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:24pt; font-weight:700;\">Audio Enhancement Suite</span></p></body></html>", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:12pt;\">\u041f\u0440\u043e\u0444\u0435\u0441\u0441\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u0430\u044f \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u0438 \u0443\u043b\u0443\u0447\u0448\u0435\u043d\u0438\u0435 \u0430\u0443\u0434\u0438\u043e</span></p></body></html>", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\">\u2022 \u0428\u0443\u043c\u043e\u043f\u043e\u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435<br/>\u2022 \u0423\u0434\u0430\u043b\u0435\u043d\u0438\u0435 \u0433\u0443\u043b\u0430 50/60 \u0413\u0446<br/>\u2022 \u0414\u0435\u2011\u044d\u0441\u0441\u0435\u0440<br/>\u2022 \u042d\u043a\u0432\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u043f\u043e\u0434 \u0440\u0435\u0447\u044c<br/>\u2022 \u041d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0433\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u0438</p></body></html>", None))
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u0420\u0435\u0436\u0438\u043c \u0440\u0430\u0431\u043e\u0442\u044b", None))
        self.modeComboBox.setItemText(0, QCoreApplication.translate("MainWindow", u"\u041b\u043e\u043a\u0430\u043b\u044c\u043d\u043e", None))
        self.modeComboBox.setItemText(1, QCoreApplication.translate("MainWindow", u"\u0423\u0434\u0430\u043b\u0451\u043d\u043d\u044b\u0439 \u0441\u0435\u0440\u0432\u0435\u0440", None))

        self.startLocalServerBtn.setText(QCoreApplication.translate("MainWindow", u"\u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0441\u0435\u0440\u0432\u0435\u0440", None))
        self.localStatusLabel.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0442\u0430\u0442\u0443\u0441: \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"\u0410\u0434\u0440\u0435\u0441/\u0445\u043e\u0441\u0442:", None))
        self.hostLineEdit.setText(QCoreApplication.translate("MainWindow", u"localhost", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0440\u0442:", None))
        self.connectBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c\u0441\u044f", None))
        self.remoteStatusLabel.setText(QCoreApplication.translate("MainWindow", u"\u041d\u0435 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u043e", None))
        self.goToProcessingBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0435\u0440\u0435\u0439\u0442\u0438 \u043a \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0435", None))
        self.aboutProjectBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e \u043f\u0440\u043e\u0435\u043a\u0442\u0435", None))
        self.licenseBtn.setText(QCoreApplication.translate("MainWindow", u"\u041b\u0438\u0446\u0435\u043d\u0437\u0438\u044f", None))
        self.aboutAppBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u0438", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:18pt; font-weight:700;\">\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438 \u0438 \u0432\u044b\u0431\u043e\u0440 \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u043e\u0432</span></p></body></html>", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("MainWindow", u"\u041c\u0435\u0442\u043e\u0434\u044b \u0443\u043b\u0443\u0447\u0448\u0435\u043d\u0438\u044f \u0430\u0443\u0434\u0438\u043e", None))
        self.noiseReductionCheck.setText(QCoreApplication.translate("MainWindow", u"\u0428\u0443\u043c\u043e\u043f\u043e\u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435", None))
        self.humRemovalCheck.setText(QCoreApplication.translate("MainWindow", u"\u0423\u0434\u0430\u043b\u0435\u043d\u0438\u0435 \u0433\u0443\u043b\u0430 50/60 \u0413\u0446", None))
        self.humFrequencyCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"50 \u0413\u0446", None))
        self.humFrequencyCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"60 \u0413\u0446", None))

        self.deEsserCheck.setText(QCoreApplication.translate("MainWindow", u"\u0414\u0435\u2011\u044d\u0441\u0441\u0435\u0440", None))
        self.eqCheck.setText(QCoreApplication.translate("MainWindow", u"\u042d\u043a\u0432\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u043f\u043e\u0434 \u0440\u0435\u0447\u044c", None))
        self.normalizationCheck.setText(QCoreApplication.translate("MainWindow", u"\u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0433\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u0438", None))
        self.lufsSpinBox.setSuffix(QCoreApplication.translate("MainWindow", u" LUFS", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u043e\u0440 \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u043e\u0432", None))
        self.selectFilesBtn.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0444\u0430\u0439\u043b\u044b...", None))
        self.selectFolderBtn.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u043f\u0430\u043f\u043a\u0443...", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0430\u043f\u043a\u0430 \u0434\u043b\u044f \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f:", None))
        self.browseOutputBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u0437\u043e\u0440...", None))
        self.overwriteCheck.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043e\u0445\u0440\u0430\u043d\u044f\u0442\u044c \u0432 \u0442\u043e\u0442 \u0436\u0435 \u0444\u0430\u0439\u043b (\u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u044c)", None))
        self.startProcessingBtn.setText(QCoreApplication.translate("MainWindow", u"\u041d\u0430\u0447\u0430\u0442\u044c \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0443", None))
        self.clearQueueBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u043e\u0447\u0435\u0440\u0435\u0434\u044c", None))
        self.label_8.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-style:italic;\">\u041f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u0435\u043c\u044b\u0435 \u0444\u043e\u0440\u043c\u0430\u0442\u044b: WAV, MP3, FLAC, OGG, M4A</span></p></body></html>", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:18pt; font-weight:700;\">\u041e\u0447\u0435\u0440\u0435\u0434\u044c \u0438 \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438</span></p></body></html>", None))
        ___qtablewidgetitem = self.taskTable.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MainWindow", u"\u0424\u0430\u0439\u043b", None));
        ___qtablewidgetitem1 = self.taskTable.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MainWindow", u"\u0414\u043b\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0441\u0442\u044c", None));
        ___qtablewidgetitem2 = self.taskTable.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("MainWindow", u"\u0424\u043e\u0440\u043c\u0430\u0442", None));
        ___qtablewidgetitem3 = self.taskTable.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435", None));
        ___qtablewidgetitem4 = self.taskTable.verticalHeaderItem(0)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("MainWindow", u"1", None));
        self.groupBox_4.setTitle(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0444\u0430\u0439\u043b:", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u0449\u0438\u0439 \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441:", None))
        self.timeRemainingLabel.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0441\u0442\u0430\u0432\u0448\u0435\u0435\u0441\u044f \u0432\u0440\u0435\u043c\u044f: ~5 \u043c\u0438\u043d\u0443\u0442", None))
        self.pauseTasksBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0430\u0443\u0437\u0430 \u0434\u043b\u044f \u043d\u043e\u0432\u044b\u0445 \u0437\u0430\u0434\u0430\u0447", None))
        self.cancelSelectedBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0435", None))
        self.clearFinishedBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0433\u043e\u0442\u043e\u0432\u044b\u0435", None))
        self.openResultsBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u0430\u043f\u043a\u0443 \u0441 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u0430\u043c\u0438", None))
        self.openLogBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043b\u043e\u0433", None))
        self.goToSpectrogramBtn.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043f\u0435\u043a\u0442\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u044b", None))
        self.label_12.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:36pt; font-weight:700;\">\u041f\u0443\u0441\u0442\u043e\u0439 \u044d\u043a\u0440\u0430\u043d</span></p></body></html>", None))
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:14pt;\">\u042d\u0442\u043e\u0442 \u044d\u043a\u0440\u0430\u043d \u0431\u0443\u0434\u0435\u0442 \u0437\u0430\u043f\u043e\u043b\u043d\u0435\u043d \u043f\u043e\u0437\u0436\u0435</span></p></body></html>", None))
        self.mainScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0442\u0430\u0440\u0442", None))
        self.processingScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430", None))
        self.progressScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441", None))
        self.emptyScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0443\u0441\u0442\u043e\u0439 \u044d\u043a\u0440\u0430\u043d", None))
    # retranslateUi

