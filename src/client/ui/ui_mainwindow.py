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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QProgressBar, QPushButton, QSizePolicy,
    QSlider, QSpacerItem, QSpinBox, QStackedWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(900, 650)
        MainWindow.setMinimumSize(QSize(800, 550))
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
        self.verticalSpacer_top = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_top)

        self.logoLabel = QLabel(self.mainScreen)
        self.logoLabel.setObjectName(u"logoLabel")
        self.logoLabel.setAlignment(Qt.AlignCenter)
        self.logoLabel.setStyleSheet(u"font-size: 48pt; color: #cccccc; border: 2px dashed #cccccc; padding: 40px; margin: 20px;")

        self.verticalLayout_2.addWidget(self.logoLabel)

        self.appTitleLabel = QLabel(self.mainScreen)
        self.appTitleLabel.setObjectName(u"appTitleLabel")
        self.appTitleLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout_2.addWidget(self.appTitleLabel)

        self.verticalSpacer_1 = QSpacerItem(20, 30, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_1)

        self.descriptionLabel = QLabel(self.mainScreen)
        self.descriptionLabel.setObjectName(u"descriptionLabel")
        self.descriptionLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout_2.addWidget(self.descriptionLabel)

        self.verticalSpacer_2 = QSpacerItem(20, 50, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_2)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer_left = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_left)

        self.aboutProjectBtn = QPushButton(self.mainScreen)
        self.aboutProjectBtn.setObjectName(u"aboutProjectBtn")
        self.aboutProjectBtn.setMinimumSize(QSize(120, 40))

        self.horizontalLayout_2.addWidget(self.aboutProjectBtn)

        self.horizontalSpacer_mid = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_mid)

        self.instructionBtn = QPushButton(self.mainScreen)
        self.instructionBtn.setObjectName(u"instructionBtn")
        self.instructionBtn.setMinimumSize(QSize(120, 40))

        self.horizontalLayout_2.addWidget(self.instructionBtn)

        self.horizontalSpacer_mid2 = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_mid2)

        self.licenseBtn = QPushButton(self.mainScreen)
        self.licenseBtn.setObjectName(u"licenseBtn")
        self.licenseBtn.setMinimumSize(QSize(120, 40))

        self.horizontalLayout_2.addWidget(self.licenseBtn)

        self.horizontalSpacer_right = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_right)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.verticalSpacer_bottom = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_bottom)

        self.stackedWidget.addWidget(self.mainScreen)
        self.connectionScreen = QWidget()
        self.connectionScreen.setObjectName(u"connectionScreen")
        self.verticalLayout_4 = QVBoxLayout(self.connectionScreen)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalSpacer_connection_top = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_connection_top)

        self.connectionTitleLabel = QLabel(self.connectionScreen)
        self.connectionTitleLabel.setObjectName(u"connectionTitleLabel")
        self.connectionTitleLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout_4.addWidget(self.connectionTitleLabel)

        self.verticalSpacer_9 = QSpacerItem(20, 30, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_9)

        self.modeGroupBox = QGroupBox(self.connectionScreen)
        self.modeGroupBox.setObjectName(u"modeGroupBox")
        font = QFont()
        font.setPointSize(10)
        self.modeGroupBox.setFont(font)
        self.verticalLayout_3 = QVBoxLayout(self.modeGroupBox)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.modeComboBox = QComboBox(self.modeGroupBox)
        self.modeComboBox.addItem("")
        self.modeComboBox.addItem("")
        self.modeComboBox.setObjectName(u"modeComboBox")
        self.modeComboBox.setFont(font)
        self.modeComboBox.setMinimumSize(QSize(0, 35))

        self.verticalLayout_3.addWidget(self.modeComboBox)

        self.localModeWidget = QWidget(self.modeGroupBox)
        self.localModeWidget.setObjectName(u"localModeWidget")
        self.gridLayout = QGridLayout(self.localModeWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.localModeInfoLabel = QLabel(self.localModeWidget)
        self.localModeInfoLabel.setObjectName(u"localModeInfoLabel")
        self.localModeInfoLabel.setFont(font)
        self.localModeInfoLabel.setStyleSheet(u"color: gray; padding: 5px;")

        self.gridLayout.addWidget(self.localModeInfoLabel, 0, 0, 1, 2)

        self.startLocalBtn = QPushButton(self.localModeWidget)
        self.startLocalBtn.setObjectName(u"startLocalBtn")
        self.startLocalBtn.setFont(font)
        self.startLocalBtn.setMinimumSize(QSize(0, 40))

        self.gridLayout.addWidget(self.startLocalBtn, 1, 0, 1, 2)

        self.localStatusLabel = QLabel(self.localModeWidget)
        self.localStatusLabel.setObjectName(u"localStatusLabel")
        self.localStatusLabel.setFont(font)
        self.localStatusLabel.setStyleSheet(u"color: gray;")

        self.gridLayout.addWidget(self.localStatusLabel, 2, 0, 1, 2)


        self.verticalLayout_3.addWidget(self.localModeWidget)

        self.remoteModeWidget = QWidget(self.modeGroupBox)
        self.remoteModeWidget.setObjectName(u"remoteModeWidget")
        self.gridLayout_2 = QGridLayout(self.remoteModeWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.hostLabel = QLabel(self.remoteModeWidget)
        self.hostLabel.setObjectName(u"hostLabel")
        self.hostLabel.setFont(font)

        self.gridLayout_2.addWidget(self.hostLabel, 0, 0, 1, 1)

        self.hostLineEdit = QLineEdit(self.remoteModeWidget)
        self.hostLineEdit.setObjectName(u"hostLineEdit")
        self.hostLineEdit.setFont(font)
        self.hostLineEdit.setMinimumSize(QSize(0, 30))

        self.gridLayout_2.addWidget(self.hostLineEdit, 0, 1, 1, 1)

        self.portLabel = QLabel(self.remoteModeWidget)
        self.portLabel.setObjectName(u"portLabel")
        self.portLabel.setFont(font)

        self.gridLayout_2.addWidget(self.portLabel, 1, 0, 1, 1)

        self.remotePortSpinBox = QSpinBox(self.remoteModeWidget)
        self.remotePortSpinBox.setObjectName(u"remotePortSpinBox")
        self.remotePortSpinBox.setFont(font)
        self.remotePortSpinBox.setMinimumSize(QSize(0, 30))
        self.remotePortSpinBox.setMinimum(1024)
        self.remotePortSpinBox.setMaximum(65535)
        self.remotePortSpinBox.setValue(8080)

        self.gridLayout_2.addWidget(self.remotePortSpinBox, 1, 1, 1, 1)

        self.connectBtn = QPushButton(self.remoteModeWidget)
        self.connectBtn.setObjectName(u"connectBtn")
        self.connectBtn.setFont(font)
        self.connectBtn.setMinimumSize(QSize(0, 40))

        self.gridLayout_2.addWidget(self.connectBtn, 2, 0, 1, 2)

        self.remoteStatusLabel = QLabel(self.remoteModeWidget)
        self.remoteStatusLabel.setObjectName(u"remoteStatusLabel")
        self.remoteStatusLabel.setFont(font)
        self.remoteStatusLabel.setStyleSheet(u"color: gray;")

        self.gridLayout_2.addWidget(self.remoteStatusLabel, 3, 0, 1, 2)

        self.serverVersionLabel = QLabel(self.remoteModeWidget)
        self.serverVersionLabel.setObjectName(u"serverVersionLabel")
        self.serverVersionLabel.setFont(font)
        self.serverVersionLabel.setStyleSheet(u"color: green;")

        self.gridLayout_2.addWidget(self.serverVersionLabel, 4, 0, 1, 2)


        self.verticalLayout_3.addWidget(self.remoteModeWidget)

        self.errorLabel = QLabel(self.modeGroupBox)
        self.errorLabel.setObjectName(u"errorLabel")
        self.errorLabel.setFont(font)
        self.errorLabel.setStyleSheet(u"color: red; padding: 5px;")
        self.errorLabel.setWordWrap(True)

        self.verticalLayout_3.addWidget(self.errorLabel)


        self.verticalLayout_4.addWidget(self.modeGroupBox)

        self.verticalSpacer_10 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_10)

        self.stackedWidget.addWidget(self.connectionScreen)
        self.processingScreen = QWidget()
        self.processingScreen.setObjectName(u"processingScreen")
        self.verticalLayout_5 = QVBoxLayout(self.processingScreen)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.processingTitleLabel = QLabel(self.processingScreen)
        self.processingTitleLabel.setObjectName(u"processingTitleLabel")
        self.processingTitleLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout_5.addWidget(self.processingTitleLabel)

        self.verticalSpacer_process_mid1 = QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer_process_mid1)

        self.processingGroupBox = QGroupBox(self.processingScreen)
        self.processingGroupBox.setObjectName(u"processingGroupBox")
        self.processingGroupBox.setFont(font)
        self.gridLayout_3 = QGridLayout(self.processingGroupBox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.dspMethodsLabel = QLabel(self.processingGroupBox)
        self.dspMethodsLabel.setObjectName(u"dspMethodsLabel")
        self.dspMethodsLabel.setFont(font)

        self.gridLayout_3.addWidget(self.dspMethodsLabel, 0, 0, 1, 2)

        self.noiseReductionCheck = QCheckBox(self.processingGroupBox)
        self.noiseReductionCheck.setObjectName(u"noiseReductionCheck")
        self.noiseReductionCheck.setFont(font)

        self.gridLayout_3.addWidget(self.noiseReductionCheck, 1, 0, 1, 1)

        self.noiseReductionSlider = QSlider(self.processingGroupBox)
        self.noiseReductionSlider.setObjectName(u"noiseReductionSlider")
        self.noiseReductionSlider.setOrientation(Qt.Horizontal)
        self.noiseReductionSlider.setMinimum(1)
        self.noiseReductionSlider.setMaximum(10)
        self.noiseReductionSlider.setValue(5)

        self.gridLayout_3.addWidget(self.noiseReductionSlider, 1, 1, 1, 1)

        self.humRemovalCheck = QCheckBox(self.processingGroupBox)
        self.humRemovalCheck.setObjectName(u"humRemovalCheck")
        self.humRemovalCheck.setFont(font)

        self.gridLayout_3.addWidget(self.humRemovalCheck, 2, 0, 1, 1)

        self.humFrequencyCombo = QComboBox(self.processingGroupBox)
        self.humFrequencyCombo.addItem("")
        self.humFrequencyCombo.addItem("")
        self.humFrequencyCombo.setObjectName(u"humFrequencyCombo")
        self.humFrequencyCombo.setFont(font)

        self.gridLayout_3.addWidget(self.humFrequencyCombo, 2, 1, 1, 1)

        self.deEsserCheck = QCheckBox(self.processingGroupBox)
        self.deEsserCheck.setObjectName(u"deEsserCheck")
        self.deEsserCheck.setFont(font)

        self.gridLayout_3.addWidget(self.deEsserCheck, 3, 0, 1, 1)

        self.deEsserSlider = QSlider(self.processingGroupBox)
        self.deEsserSlider.setObjectName(u"deEsserSlider")
        self.deEsserSlider.setOrientation(Qt.Horizontal)
        self.deEsserSlider.setMinimum(1)
        self.deEsserSlider.setMaximum(10)
        self.deEsserSlider.setValue(5)

        self.gridLayout_3.addWidget(self.deEsserSlider, 3, 1, 1, 1)

        self.eqCheck = QCheckBox(self.processingGroupBox)
        self.eqCheck.setObjectName(u"eqCheck")
        self.eqCheck.setFont(font)

        self.gridLayout_3.addWidget(self.eqCheck, 4, 0, 1, 1)

        self.mlMethodsLabel = QLabel(self.processingGroupBox)
        self.mlMethodsLabel.setObjectName(u"mlMethodsLabel")
        self.mlMethodsLabel.setFont(font)

        self.gridLayout_3.addWidget(self.mlMethodsLabel, 5, 0, 1, 2)

        self.mlModelCombo = QComboBox(self.processingGroupBox)
        self.mlModelCombo.addItem("")
        self.mlModelCombo.addItem("")
        self.mlModelCombo.addItem("")
        self.mlModelCombo.setObjectName(u"mlModelCombo")
        self.mlModelCombo.setFont(font)

        self.gridLayout_3.addWidget(self.mlModelCombo, 6, 0, 1, 2)

        self.generalSettingsLabel = QLabel(self.processingGroupBox)
        self.generalSettingsLabel.setObjectName(u"generalSettingsLabel")
        self.generalSettingsLabel.setFont(font)

        self.gridLayout_3.addWidget(self.generalSettingsLabel, 7, 0, 1, 2)

        self.normalizationCheck = QCheckBox(self.processingGroupBox)
        self.normalizationCheck.setObjectName(u"normalizationCheck")
        self.normalizationCheck.setFont(font)

        self.gridLayout_3.addWidget(self.normalizationCheck, 8, 0, 1, 1)

        self.lufsSpinBox = QSpinBox(self.processingGroupBox)
        self.lufsSpinBox.setObjectName(u"lufsSpinBox")
        self.lufsSpinBox.setFont(font)
        self.lufsSpinBox.setMinimum(-30)
        self.lufsSpinBox.setMaximum(-10)
        self.lufsSpinBox.setValue(-16)

        self.gridLayout_3.addWidget(self.lufsSpinBox, 8, 1, 1, 1)


        self.verticalLayout_5.addWidget(self.processingGroupBox)

        self.verticalSpacer_process_mid2 = QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer_process_mid2)

        self.sourcesGroupBox = QGroupBox(self.processingScreen)
        self.sourcesGroupBox.setObjectName(u"sourcesGroupBox")
        self.sourcesGroupBox.setFont(font)
        self.verticalLayout_6 = QVBoxLayout(self.sourcesGroupBox)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.selectFilesBtn = QPushButton(self.sourcesGroupBox)
        self.selectFilesBtn.setObjectName(u"selectFilesBtn")
        self.selectFilesBtn.setFont(font)
        self.selectFilesBtn.setMinimumSize(QSize(0, 35))

        self.horizontalLayout_3.addWidget(self.selectFilesBtn)

        self.horizontalSpacer_btn = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_btn)

        self.selectFolderBtn = QPushButton(self.sourcesGroupBox)
        self.selectFolderBtn.setObjectName(u"selectFolderBtn")
        self.selectFolderBtn.setFont(font)
        self.selectFolderBtn.setMinimumSize(QSize(0, 35))

        self.horizontalLayout_3.addWidget(self.selectFolderBtn)


        self.verticalLayout_6.addLayout(self.horizontalLayout_3)

        self.fileListWidget = QListWidget(self.sourcesGroupBox)
        self.fileListWidget.setObjectName(u"fileListWidget")
        self.fileListWidget.setFont(font)
        self.fileListWidget.setMinimumSize(QSize(0, 120))

        self.verticalLayout_6.addWidget(self.fileListWidget)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.outputFolderLabel = QLabel(self.sourcesGroupBox)
        self.outputFolderLabel.setObjectName(u"outputFolderLabel")
        self.outputFolderLabel.setFont(font)

        self.horizontalLayout_4.addWidget(self.outputFolderLabel)

        self.outputFolderLineEdit = QLineEdit(self.sourcesGroupBox)
        self.outputFolderLineEdit.setObjectName(u"outputFolderLineEdit")
        self.outputFolderLineEdit.setFont(font)
        self.outputFolderLineEdit.setMinimumSize(QSize(0, 30))

        self.horizontalLayout_4.addWidget(self.outputFolderLineEdit)

        self.browseOutputBtn = QPushButton(self.sourcesGroupBox)
        self.browseOutputBtn.setObjectName(u"browseOutputBtn")
        self.browseOutputBtn.setFont(font)
        self.browseOutputBtn.setMinimumSize(QSize(80, 30))

        self.horizontalLayout_4.addWidget(self.browseOutputBtn)


        self.verticalLayout_6.addLayout(self.horizontalLayout_4)

        self.overwriteCheck = QCheckBox(self.sourcesGroupBox)
        self.overwriteCheck.setObjectName(u"overwriteCheck")
        self.overwriteCheck.setFont(font)

        self.verticalLayout_6.addWidget(self.overwriteCheck)


        self.verticalLayout_5.addWidget(self.sourcesGroupBox)

        self.verticalSpacer_process_mid3 = QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer_process_mid3)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalSpacer_process_left = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_process_left)

        self.startProcessingBtn = QPushButton(self.processingScreen)
        self.startProcessingBtn.setObjectName(u"startProcessingBtn")
        font1 = QFont()
        font1.setPointSize(11)
        self.startProcessingBtn.setFont(font1)
        self.startProcessingBtn.setMinimumSize(QSize(180, 40))

        self.horizontalLayout_5.addWidget(self.startProcessingBtn)

        self.horizontalSpacer_process_mid = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_process_mid)

        self.clearQueueBtn = QPushButton(self.processingScreen)
        self.clearQueueBtn.setObjectName(u"clearQueueBtn")
        self.clearQueueBtn.setFont(font1)
        self.clearQueueBtn.setMinimumSize(QSize(180, 40))

        self.horizontalLayout_5.addWidget(self.clearQueueBtn)

        self.horizontalSpacer_process_right = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_process_right)


        self.verticalLayout_5.addLayout(self.horizontalLayout_5)

        self.formatsLabel = QLabel(self.processingScreen)
        self.formatsLabel.setObjectName(u"formatsLabel")
        self.formatsLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout_5.addWidget(self.formatsLabel)

        self.verticalSpacer_process_bottom = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer_process_bottom)

        self.stackedWidget.addWidget(self.processingScreen)
        self.progressScreen = QWidget()
        self.progressScreen.setObjectName(u"progressScreen")
        self.verticalLayout_7 = QVBoxLayout(self.progressScreen)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.progressTitleLabel = QLabel(self.progressScreen)
        self.progressTitleLabel.setObjectName(u"progressTitleLabel")
        self.progressTitleLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout_7.addWidget(self.progressTitleLabel)

        self.verticalSpacer_progress_mid1 = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_progress_mid1)

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
        self.taskTable.setObjectName(u"taskTable")
        self.taskTable.setMinimumSize(QSize(0, 200))
        self.taskTable.setFont(font)
        self.taskTable.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.verticalLayout_7.addWidget(self.taskTable)

        self.verticalSpacer_progress_mid2 = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_progress_mid2)

        self.progressGroupBox = QGroupBox(self.progressScreen)
        self.progressGroupBox.setObjectName(u"progressGroupBox")
        self.progressGroupBox.setFont(font)
        self.verticalLayout_8 = QVBoxLayout(self.progressGroupBox)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.currentFileLabel = QLabel(self.progressGroupBox)
        self.currentFileLabel.setObjectName(u"currentFileLabel")
        self.currentFileLabel.setFont(font)

        self.verticalLayout_8.addWidget(self.currentFileLabel)

        self.currentFileProgress = QProgressBar(self.progressGroupBox)
        self.currentFileProgress.setObjectName(u"currentFileProgress")
        self.currentFileProgress.setFont(font)
        self.currentFileProgress.setValue(0)

        self.verticalLayout_8.addWidget(self.currentFileProgress)

        self.totalProgressLabel = QLabel(self.progressGroupBox)
        self.totalProgressLabel.setObjectName(u"totalProgressLabel")
        self.totalProgressLabel.setFont(font)

        self.verticalLayout_8.addWidget(self.totalProgressLabel)

        self.totalProgress = QProgressBar(self.progressGroupBox)
        self.totalProgress.setObjectName(u"totalProgress")
        self.totalProgress.setFont(font)
        self.totalProgress.setValue(0)

        self.verticalLayout_8.addWidget(self.totalProgress)

        self.timeRemainingLabel = QLabel(self.progressGroupBox)
        self.timeRemainingLabel.setObjectName(u"timeRemainingLabel")
        self.timeRemainingLabel.setFont(font)

        self.verticalLayout_8.addWidget(self.timeRemainingLabel)


        self.verticalLayout_7.addWidget(self.progressGroupBox)

        self.errorNotificationLabel = QLabel(self.progressScreen)
        self.errorNotificationLabel.setObjectName(u"errorNotificationLabel")
        self.errorNotificationLabel.setFont(font)
        self.errorNotificationLabel.setStyleSheet(u"color: red; padding: 5px;")
        self.errorNotificationLabel.setWordWrap(True)

        self.verticalLayout_7.addWidget(self.errorNotificationLabel)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.pauseTasksBtn = QPushButton(self.progressScreen)
        self.pauseTasksBtn.setObjectName(u"pauseTasksBtn")
        self.pauseTasksBtn.setFont(font)
        self.pauseTasksBtn.setMinimumSize(QSize(0, 35))

        self.horizontalLayout_6.addWidget(self.pauseTasksBtn)

        self.horizontalSpacer_progress_mid1 = QSpacerItem(10, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_progress_mid1)

        self.cancelSelectedBtn = QPushButton(self.progressScreen)
        self.cancelSelectedBtn.setObjectName(u"cancelSelectedBtn")
        self.cancelSelectedBtn.setFont(font)
        self.cancelSelectedBtn.setMinimumSize(QSize(0, 35))

        self.horizontalLayout_6.addWidget(self.cancelSelectedBtn)

        self.horizontalSpacer_progress_mid2 = QSpacerItem(10, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_progress_mid2)

        self.clearFinishedBtn = QPushButton(self.progressScreen)
        self.clearFinishedBtn.setObjectName(u"clearFinishedBtn")
        self.clearFinishedBtn.setFont(font)
        self.clearFinishedBtn.setMinimumSize(QSize(0, 35))

        self.horizontalLayout_6.addWidget(self.clearFinishedBtn)


        self.verticalLayout_7.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.openLogBtn = QPushButton(self.progressScreen)
        self.openLogBtn.setObjectName(u"openLogBtn")
        self.openLogBtn.setFont(font)
        self.openLogBtn.setMinimumSize(QSize(0, 35))

        self.horizontalLayout_7.addWidget(self.openLogBtn)

        self.horizontalSpacer_progress_mid3 = QSpacerItem(10, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_progress_mid3)

        self.cancelCurrentBtn = QPushButton(self.progressScreen)
        self.cancelCurrentBtn.setObjectName(u"cancelCurrentBtn")
        self.cancelCurrentBtn.setFont(font)
        self.cancelCurrentBtn.setMinimumSize(QSize(0, 35))

        self.horizontalLayout_7.addWidget(self.cancelCurrentBtn)


        self.verticalLayout_7.addLayout(self.horizontalLayout_7)

        self.verticalSpacer_progress_bottom = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_progress_bottom)

        self.stackedWidget.addWidget(self.progressScreen)

        self.verticalLayout.addWidget(self.stackedWidget)

        self.navWidget = QWidget(self.centralwidget)
        self.navWidget.setObjectName(u"navWidget")
        self.navWidget.setStyleSheet(u"background-color: #f0f0f0; padding: 5px;")
        self.horizontalLayout_8 = QHBoxLayout(self.navWidget)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalSpacer_nav_left = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_nav_left)

        self.mainScreenBtn = QPushButton(self.navWidget)
        self.mainScreenBtn.setObjectName(u"mainScreenBtn")
        font2 = QFont()
        font2.setPointSize(11)
        font2.setBold(True)
        self.mainScreenBtn.setFont(font2)
        self.mainScreenBtn.setMinimumSize(QSize(0, 40))
        self.mainScreenBtn.setStyleSheet(u"padding: 8px 20px;")

        self.horizontalLayout_8.addWidget(self.mainScreenBtn)

        self.horizontalSpacer_nav_mid1 = QSpacerItem(15, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_nav_mid1)

        self.connectionScreenBtn = QPushButton(self.navWidget)
        self.connectionScreenBtn.setObjectName(u"connectionScreenBtn")
        self.connectionScreenBtn.setFont(font2)
        self.connectionScreenBtn.setMinimumSize(QSize(0, 40))
        self.connectionScreenBtn.setStyleSheet(u"padding: 8px 20px;")

        self.horizontalLayout_8.addWidget(self.connectionScreenBtn)

        self.horizontalSpacer_nav_mid2 = QSpacerItem(15, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_nav_mid2)

        self.processingScreenBtn = QPushButton(self.navWidget)
        self.processingScreenBtn.setObjectName(u"processingScreenBtn")
        self.processingScreenBtn.setFont(font2)
        self.processingScreenBtn.setMinimumSize(QSize(0, 40))
        self.processingScreenBtn.setStyleSheet(u"padding: 8px 20px;")

        self.horizontalLayout_8.addWidget(self.processingScreenBtn)

        self.horizontalSpacer_nav_mid3 = QSpacerItem(15, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_nav_mid3)

        self.progressScreenBtn = QPushButton(self.navWidget)
        self.progressScreenBtn.setObjectName(u"progressScreenBtn")
        self.progressScreenBtn.setFont(font2)
        self.progressScreenBtn.setMinimumSize(QSize(0, 40))
        self.progressScreenBtn.setStyleSheet(u"padding: 8px 20px;")

        self.horizontalLayout_8.addWidget(self.progressScreenBtn)

        self.horizontalSpacer_nav_right = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_nav_right)


        self.verticalLayout.addWidget(self.navWidget)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.stackedWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"SpeechEQ v1.0", None))
        self.logoLabel.setText(QCoreApplication.translate("MainWindow", u"[\u042d\u043c\u0431\u043b\u0435\u043c\u0430 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f]", None))
        self.appTitleLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:28pt; font-weight:700;\">SpeechEQ</span><br/><span style=\" font-size:12pt; color:gray;\">\u0412\u0435\u0440\u0441\u0438\u044f 1.0</span></p></body></html>", None))
        self.descriptionLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:14pt;\">\u041f\u0440\u043e\u0444\u0435\u0441\u0441\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u0430\u044f \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u0438 \u0443\u043b\u0443\u0447\u0448\u0435\u043d\u0438\u0435 \u0430\u0443\u0434\u0438\u043e</span></p></body></html>", None))
        self.aboutProjectBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e \u043f\u0440\u043e\u0435\u043a\u0442\u0435", None))
        self.instructionBtn.setText(QCoreApplication.translate("MainWindow", u"\u0418\u043d\u0441\u0442\u0440\u0443\u043a\u0446\u0438\u044f", None))
        self.licenseBtn.setText(QCoreApplication.translate("MainWindow", u"\u041b\u0438\u0446\u0435\u043d\u0437\u0438\u044f", None))
        self.connectionTitleLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:20pt; font-weight:700;\">\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u043a \u0441\u0435\u0440\u0432\u0435\u0440\u0443 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438</span></p></body></html>", None))
        self.modeGroupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u0420\u0435\u0436\u0438\u043c \u0440\u0430\u0431\u043e\u0442\u044b", None))
        self.modeComboBox.setItemText(0, QCoreApplication.translate("MainWindow", u"\u041b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0440\u0435\u0436\u0438\u043c", None))
        self.modeComboBox.setItemText(1, QCoreApplication.translate("MainWindow", u"\u0423\u0434\u0430\u043b\u0451\u043d\u043d\u044b\u0439 \u0441\u0435\u0440\u0432\u0435\u0440", None))

        self.localModeInfoLabel.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u043d\u0430 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u043c \u043a\u043e\u043c\u043f\u044c\u044e\u0442\u0435\u0440\u0435 \u0431\u0435\u0437 \u0441\u0435\u0440\u0432\u0435\u0440\u0430", None))
        self.startLocalBtn.setText(QCoreApplication.translate("MainWindow", u"\u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0440\u0435\u0436\u0438\u043c", None))
        self.localStatusLabel.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0442\u0430\u0442\u0443\u0441: \u043d\u0435 \u0437\u0430\u043f\u0443\u0449\u0435\u043d", None))
        self.hostLabel.setText(QCoreApplication.translate("MainWindow", u"\u0410\u0434\u0440\u0435\u0441/\u0445\u043e\u0441\u0442:", None))
        self.hostLineEdit.setText(QCoreApplication.translate("MainWindow", u"localhost", None))
        self.portLabel.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0440\u0442:", None))
        self.connectBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c\u0441\u044f", None))
        self.remoteStatusLabel.setText(QCoreApplication.translate("MainWindow", u"\u041d\u0435 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u043e", None))
        self.serverVersionLabel.setText("")
        self.errorLabel.setText("")
        self.processingTitleLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:20pt; font-weight:700;\">\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438 \u0438 \u0432\u044b\u0431\u043e\u0440 \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u043e\u0432</span></p></body></html>", None))
        self.processingGroupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u041c\u0435\u0442\u043e\u0434\u044b \u0443\u043b\u0443\u0447\u0448\u0435\u043d\u0438\u044f \u0430\u0443\u0434\u0438\u043e", None))
        self.dspMethodsLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><b>DSP-\u043c\u0435\u0442\u043e\u0434\u044b:</b></p></body></html>", None))
        self.noiseReductionCheck.setText(QCoreApplication.translate("MainWindow", u"\u0428\u0443\u043c\u043e\u043f\u043e\u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435", None))
        self.humRemovalCheck.setText(QCoreApplication.translate("MainWindow", u"\u0423\u0434\u0430\u043b\u0435\u043d\u0438\u0435 \u0433\u0443\u043b\u0430 50/60 \u0413\u0446", None))
        self.humFrequencyCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"50 \u0413\u0446", None))
        self.humFrequencyCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"60 \u0413\u0446", None))

        self.deEsserCheck.setText(QCoreApplication.translate("MainWindow", u"\u0414\u0435\u2011\u044d\u0441\u0441\u0435\u0440", None))
        self.eqCheck.setText(QCoreApplication.translate("MainWindow", u"\u042d\u043a\u0432\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u043f\u043e\u0434 \u0440\u0435\u0447\u044c", None))
        self.mlMethodsLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><b>ML-\u043c\u0435\u0442\u043e\u0434\u044b:</b></p></body></html>", None))
        self.mlModelCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"\u041d\u0435 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c ML-\u043c\u043e\u0434\u0435\u043b\u0438", None))
        self.mlModelCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"\u041c\u043e\u0434\u0435\u043b\u044c \u0443\u043b\u0443\u0447\u0448\u0435\u043d\u0438\u044f \u0440\u0435\u0447\u0438 v1", None))
        self.mlModelCombo.setItemText(2, QCoreApplication.translate("MainWindow", u"\u041c\u043e\u0434\u0435\u043b\u044c \u0432\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f \u0440\u0435\u0447\u0438 v2", None))

        self.generalSettingsLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><b>\u041e\u0431\u0449\u0438\u0435 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438:</b></p></body></html>", None))
        self.normalizationCheck.setText(QCoreApplication.translate("MainWindow", u"\u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0433\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u0438", None))
        self.lufsSpinBox.setSuffix(QCoreApplication.translate("MainWindow", u" LUFS", None))
        self.sourcesGroupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u043e\u0440 \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u043e\u0432", None))
        self.selectFilesBtn.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0444\u0430\u0439\u043b\u044b...", None))
        self.selectFolderBtn.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u043f\u0430\u043f\u043a\u0443...", None))
        self.outputFolderLabel.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0430\u043f\u043a\u0430 \u0434\u043b\u044f \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f:", None))
        self.browseOutputBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u0437\u043e\u0440...", None))
        self.overwriteCheck.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043e\u0445\u0440\u0430\u043d\u044f\u0442\u044c \u0432 \u0442\u043e\u0442 \u0436\u0435 \u0444\u0430\u0439\u043b (\u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u044c)", None))
        self.startProcessingBtn.setText(QCoreApplication.translate("MainWindow", u"\u041d\u0430\u0447\u0430\u0442\u044c \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0443", None))
        self.clearQueueBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u043e\u0447\u0435\u0440\u0435\u0434\u044c", None))
        self.formatsLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-style:italic; color:gray;\">\u041f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u0435\u043c\u044b\u0435 \u0444\u043e\u0440\u043c\u0430\u0442\u044b: MP4, MOV, MKV</span></p></body></html>", None))
        self.progressTitleLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:20pt; font-weight:700;\">\u041e\u0447\u0435\u0440\u0435\u0434\u044c \u0438 \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438</span></p></body></html>", None))
        ___qtablewidgetitem = self.taskTable.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MainWindow", u"\u0424\u0430\u0439\u043b", None));
        ___qtablewidgetitem1 = self.taskTable.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MainWindow", u"\u0414\u043b\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0441\u0442\u044c", None));
        ___qtablewidgetitem2 = self.taskTable.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("MainWindow", u"\u0424\u043e\u0440\u043c\u0430\u0442", None));
        ___qtablewidgetitem3 = self.taskTable.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435", None));
        self.progressGroupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441", None))
        self.currentFileLabel.setText(QCoreApplication.translate("MainWindow", u"\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0444\u0430\u0439\u043b:", None))
        self.totalProgressLabel.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u0449\u0438\u0439 \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441:", None))
        self.timeRemainingLabel.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0441\u0442\u0430\u0432\u0448\u0435\u0435\u0441\u044f \u0432\u0440\u0435\u043c\u044f: --", None))
        self.errorNotificationLabel.setText("")
        self.pauseTasksBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0430\u0443\u0437\u0430", None))
        self.cancelSelectedBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0435", None))
        self.clearFinishedBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0433\u043e\u0442\u043e\u0432\u044b\u0435", None))
        self.openLogBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043b\u043e\u0433", None))
        self.cancelCurrentBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c \u0442\u0435\u043a\u0443\u0449\u0438\u0439", None))
        self.mainScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0422\u0410\u0420\u0422", None))
        self.connectionScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u041e\u0414\u041a\u041b\u042e\u0427\u0415\u041d\u0418\u0415", None))
        self.processingScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0411\u0420\u0410\u0411\u041e\u0422\u041a\u0410", None))
        self.progressScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0420\u041e\u0413\u0420\u0415\u0421\u0421", None))
    # retranslateUi

