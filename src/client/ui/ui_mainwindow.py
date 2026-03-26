# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'ui_main.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
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
from PySide6.QtWidgets import (QAbstractItemView, QAbstractSpinBox, QApplication, QCheckBox,
    QComboBox, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QProgressBar, QPushButton,
    QSizePolicy, QSlider, QSpacerItem, QSpinBox,
    QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1300, 850)
        MainWindow.setMinimumSize(QSize(1000, 700))
        MainWindow.setStyleSheet(u"\n"
"    /* \u0413\u043b\u043e\u0431\u0430\u043b\u044c\u043d\u044b\u0435 \u0441\u0442\u0438\u043b\u0438 */\n"
"    QMainWindow {\n"
"        background-color: #f5f7fa;\n"
"    }\n"
"    \n"
"    QLabel {\n"
"        color: #2c3e50;\n"
"    }\n"
"    \n"
"    QGroupBox {\n"
"        font-weight: bold;\n"
"        border: 1px solid #d0d7de;\n"
"        border-radius: 8px;\n"
"        margin-top: 12px;\n"
"        padding-top: 12px;\n"
"        background-color: #ffffff;\n"
"    }\n"
"    \n"
"    QGroupBox::title {\n"
"        subcontrol-origin: margin;\n"
"        left: 16px;\n"
"        padding: 0 8px 0 8px;\n"
"        color: #1f2d3d;\n"
"    }\n"
"    \n"
"    QPushButton {\n"
"        background-color: #ffffff;\n"
"        border: 1.5px solid #cbd5e1;\n"
"        border-radius: 8px;\n"
"        padding: 8px 20px;\n"
"        font-weight: 500;\n"
"        font-size: 13px;\n"
"        color: #1f2d3d;\n"
"    }\n"
"    \n"
"    QPushButton:hover {\n"
"        background-color: #f1f5f9;\n"
"        border-color"
                        ": #94a3b8;\n"
"    }\n"
"    \n"
"    QPushButton:pressed {\n"
"        background-color: #e2e8f0;\n"
"    }\n"
"    \n"
"    QPushButton#startProcessingBtn, QPushButton#startLocalBtn, QPushButton#connectBtn {\n"
"        background-color: #3b82f6;\n"
"        border: 1.5px solid #3b82f6;\n"
"        color: white;\n"
"        font-size: 14px;\n"
"        font-weight: bold;\n"
"    }\n"
"    \n"
"    QPushButton#startProcessingBtn:hover, QPushButton#startLocalBtn:hover, QPushButton#connectBtn:hover {\n"
"        background-color: #2563eb;\n"
"        border-color: #2563eb;\n"
"    }\n"
"    \n"
"    QPushButton#clearQueueBtn, QPushButton#cancelSelectedBtn {\n"
"        background-color: #ef4444;\n"
"        border: 1.5px solid #ef4444;\n"
"        color: white;\n"
"        font-size: 14px;\n"
"        font-weight: bold;\n"
"    }\n"
"    \n"
"    QPushButton#clearQueueBtn:hover, QPushButton#cancelSelectedBtn:hover {\n"
"        background-color: #dc2626;\n"
"        border-color: #dc2626;\n"
"    }\n"
"    \n"
""
                        "    QPushButton#openLogBtn {\n"
"        background-color: #f1f5f9;\n"
"        border-color: #cbd5e1;\n"
"        color: #475569;\n"
"        font-size: 12px;\n"
"        padding: 6px 16px;\n"
"    }\n"
"    \n"
"    QPushButton#openLogBtn:hover {\n"
"        background-color: #e2e8f0;\n"
"        border-color: #94a3b8;\n"
"        color: #1f2d3d;\n"
"    }\n"
"    \n"
"    /* \u0421\u0442\u0438\u043b\u0438 \u0434\u043b\u044f QLineEdit, QSpinBox */\n"
"    QLineEdit, QSpinBox {\n"
"        border: 1px solid #cbd5e1;\n"
"        border-radius: 6px;\n"
"        padding: 8px 10px;\n"
"        background-color: #ffffff;\n"
"        selection-background-color: #3b82f6;\n"
"        font-size: 12px;\n"
"        color: #1f2d3d;\n"
"    }\n"
"    \n"
"    /* \u0421\u0442\u0438\u043b\u0438 \u0434\u043b\u044f QListWidget - \u0447\u0435\u0440\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442 */\n"
"    QListWidget {\n"
"        border: 1px solid #cbd5e1;\n"
"        border-radius: 6px;\n"
"        padding: 8px 10px;\n"
" "
                        "       background-color: #ffffff;\n"
"        selection-background-color: #3b82f6;\n"
"        selection-color: #ffffff;\n"
"        font-size: 12px;\n"
"        color: #1f2d3d;\n"
"    }\n"
"    \n"
"    QListWidget::item {\n"
"        color: #1f2d3d;\n"
"        padding: 5px;\n"
"    }\n"
"    \n"
"    QListWidget::item:selected {\n"
"        background-color: #3b82f6;\n"
"        color: #ffffff;\n"
"    }\n"
"    \n"
"    QListWidget::item:hover {\n"
"        background-color: #f1f5f9;\n"
"        color: #1f2d3d;\n"
"    }\n"
"    \n"
"    /* \u0421\u0442\u0438\u043b\u0438 \u0434\u043b\u044f QTableWidget - \u0447\u0435\u0440\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442 */\n"
"    QTableWidget {\n"
"        border: 1px solid #cbd5e1;\n"
"        border-radius: 6px;\n"
"        background-color: #ffffff;\n"
"        alternate-background-color: #f8fafc;\n"
"        gridline-color: #e2e8f0;\n"
"        font-size: 12px;\n"
"        color: #1f2d3d;\n"
"    }\n"
"    \n"
"    QTableWidget::item {\n"
"        c"
                        "olor: #1f2d3d;\n"
"        padding: 8px;\n"
"    }\n"
"    \n"
"    QTableWidget::item:selected {\n"
"        background-color: #3b82f6;\n"
"        color: #ffffff;\n"
"    }\n"
"    \n"
"    QTableWidget::item:hover {\n"
"        background-color: #f1f5f9;\n"
"    }\n"
"    \n"
"    QHeaderView::section {\n"
"        background-color: #f1f5f9;\n"
"        padding: 10px;\n"
"        border: none;\n"
"        border-bottom: 1px solid #e2e8f0;\n"
"        font-weight: bold;\n"
"        color: #1e293b;\n"
"        font-size: 12px;\n"
"    }\n"
"    \n"
"    /* \u0421\u0442\u0438\u043b\u0438 \u0434\u043b\u044f QProgressBar \u0432\u043d\u0443\u0442\u0440\u0438 \u0442\u0430\u0431\u043b\u0438\u0446\u044b */\n"
"    QProgressBar {\n"
"        border: 1px solid #cbd5e1;\n"
"        background-color: #f1f5f9;\n"
"        border-radius: 4px;\n"
"        text-align: center;\n"
"        color: #1f2d3d;\n"
"        height: 20px;\n"
"        font-size: 11px;\n"
"    }\n"
"    \n"
"    QProgressBar::chunk {\n"
"        backgr"
                        "ound-color: #3b82f6;\n"
"        border-radius: 3px;\n"
"    }\n"
"    \n"
"    /* \u0421\u043f\u0435\u0446\u0438\u0430\u043b\u044c\u043d\u044b\u0435 \u0441\u0442\u0438\u043b\u0438 \u0434\u043b\u044f QComboBox \u0441 \u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u044b\u043c \u043f\u043e\u0432\u0435\u0434\u0435\u043d\u0438\u0435\u043c \u0432\u044b\u043f\u0430\u0434\u0430\u044e\u0449\u0435\u0433\u043e \u0441\u043f\u0438\u0441\u043a\u0430 */\n"
"    QComboBox {\n"
"        border: 1px solid #cbd5e1;\n"
"        border-radius: 6px;\n"
"        padding: 8px 10px;\n"
"        background-color: #ffffff;\n"
"        color: #1f2d3d;\n"
"        font-size: 12px;\n"
"        min-height: 20px;\n"
"    }\n"
"    \n"
"    QComboBox:hover {\n"
"        border-color: #94a3b8;\n"
"    }\n"
"    \n"
"    QComboBox:focus {\n"
"        border-color: #3b82f6;\n"
"        outline: none;\n"
"    }\n"
"    \n"
"    QComboBox::drop-down {\n"
"        border: none;\n"
"        width: 24px;\n"
"        background: transparent;\n"
"  "
                        "  }\n"
"    \n"
"    QComboBox::down-arrow {\n"
"        image: none;\n"
"        border-left: 5px solid transparent;\n"
"        border-right: 5px solid transparent;\n"
"        border-top: 5px solid #64748b;\n"
"        margin-right: 8px;\n"
"    }\n"
"    \n"
"    QComboBox::down-arrow:hover {\n"
"        border-top-color: #3b82f6;\n"
"    }\n"
"    \n"
"    /* \u0421\u0442\u0438\u043b\u0438 \u0434\u043b\u044f \u0432\u044b\u043f\u0430\u0434\u0430\u044e\u0449\u0435\u0433\u043e \u0441\u043f\u0438\u0441\u043a\u0430 QComboBox - \u0447\u0435\u0440\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442 */\n"
"    QComboBox QAbstractItemView {\n"
"        border: 1px solid #cbd5e1;\n"
"        border-radius: 6px;\n"
"        background-color: #ffffff;\n"
"        selection-background-color: #3b82f6;\n"
"        selection-color: #ffffff;\n"
"        outline: none;\n"
"        margin: 0px;\n"
"        padding: 0px;\n"
"    }\n"
"    \n"
"    QComboBox QAbstractItemView::item {\n"
"        padding: 8px 12px;\n"
"        mi"
                        "n-height: 24px;\n"
"        background-color: #ffffff;\n"
"        color: #1f2d3d;\n"
"    }\n"
"    \n"
"    QComboBox QAbstractItemView::item:hover {\n"
"        background-color: #f1f5f9;\n"
"        color: #1f2d3d;\n"
"    }\n"
"    \n"
"    QComboBox QAbstractItemView::item:selected {\n"
"        background-color: #3b82f6;\n"
"        color: #ffffff;\n"
"    }\n"
"    \n"
"    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QListWidget:focus, QTableWidget:focus {\n"
"        border-color: #3b82f6;\n"
"        outline: none;\n"
"    }\n"
"    \n"
"    /* \u0421\u0442\u0438\u043b\u0438 \u0434\u043b\u044f QSpinBox \u0441 \u043a\u043d\u043e\u043f\u043a\u0430\u043c\u0438 \u0432\u0432\u0435\u0440\u0445/\u0432\u043d\u0438\u0437 */\n"
"    QSpinBox {\n"
"        padding-right: 20px;\n"
"        color: #1f2d3d;\n"
"    }\n"
"    \n"
"    QSpinBox::up-button {\n"
"        subcontrol-origin: border;\n"
"        subcontrol-position: top right;\n"
"        width: 20px;\n"
"        height: 18px;\n"
"        border-le"
                        "ft: 1px solid #cbd5e1;\n"
"        border-bottom: 1px solid #cbd5e1;\n"
"        border-radius: 0px;\n"
"        background-color: #f8fafc;\n"
"    }\n"
"    \n"
"    QSpinBox::up-button:hover {\n"
"        background-color: #e2e8f0;\n"
"    }\n"
"    \n"
"    QSpinBox::down-button {\n"
"        subcontrol-origin: border;\n"
"        subcontrol-position: bottom right;\n"
"        width: 20px;\n"
"        height: 18px;\n"
"        border-left: 1px solid #cbd5e1;\n"
"        border-top: 1px solid #cbd5e1;\n"
"        border-radius: 0px;\n"
"        background-color: #f8fafc;\n"
"    }\n"
"    \n"
"    QSpinBox::down-button:hover {\n"
"        background-color: #e2e8f0;\n"
"    }\n"
"    \n"
"    QSlider::groove:horizontal {\n"
"        border: none;\n"
"        height: 5px;\n"
"        background: #e2e8f0;\n"
"        border-radius: 3px;\n"
"    }\n"
"    \n"
"    QSlider::handle:horizontal {\n"
"        background: #3b82f6;\n"
"        width: 16px;\n"
"        height: 16px;\n"
"        margin: -5px 0;\n"
"     "
                        "   border-radius: 8px;\n"
"        border: 1px solid #3b82f6;\n"
"    }\n"
"    \n"
"    QSlider::handle:horizontal:hover {\n"
"        background: #2563eb;\n"
"    }\n"
"    \n"
"    QSlider::sub-page:horizontal {\n"
"        background: #3b82f6;\n"
"        border-radius: 3px;\n"
"    }\n"
"    \n"
"    QProgressBar {\n"
"        border: 1px solid #cbd5e1;\n"
"        background-color: #f1f5f9;\n"
"        border-radius: 6px;\n"
"        text-align: center;\n"
"        color: #1f2d3d;\n"
"        height: 24px;\n"
"        font-size: 12px;\n"
"    }\n"
"    \n"
"    QProgressBar::chunk {\n"
"        background-color: #3b82f6;\n"
"        border-radius: 5px;\n"
"    }\n"
"    \n"
"    /* \u0421\u0442\u0438\u043b\u0438 \u0434\u043b\u044f QCheckBox */\n"
"    QCheckBox {\n"
"        spacing: 10px;\n"
"        color: #1f2d3d;\n"
"        font-size: 12px;\n"
"    }\n"
"    \n"
"    QCheckBox::indicator {\n"
"        width: 18px;\n"
"        height: 18px;\n"
"        border-radius: 4px;\n"
"        border: 1.5px so"
                        "lid #cbd5e1;\n"
"        background-color: #ffffff;\n"
"    }\n"
"    \n"
"    QCheckBox::indicator:checked {\n"
"        background-color: #3b82f6;\n"
"        border-color: #3b82f6;\n"
"    }\n"
"    \n"
"    QCheckBox::indicator:checked:hover {\n"
"        background-color: #2563eb;\n"
"    }\n"
"    \n"
"    QCheckBox::indicator:unchecked:hover {\n"
"        border-color: #94a3b8;\n"
"    }\n"
"    \n"
"    QCheckBox::indicator:disabled {\n"
"        background-color: #f1f5f9;\n"
"        border-color: #e2e8f0;\n"
"    }\n"
"    \n"
"    /* \u041d\u0430\u0432\u0438\u0433\u0430\u0446\u0438\u043e\u043d\u043d\u0430\u044f \u043f\u0430\u043d\u0435\u043b\u044c */\n"
"    #navWidget {\n"
"        background-color: #ffffff;\n"
"        border-top: 1px solid #e2e8f0;\n"
"        border-bottom: 1px solid #e2e8f0;\n"
"    }\n"
"    \n"
"    #navWidget QPushButton {\n"
"        background-color: transparent;\n"
"        border: 1.5px solid transparent;\n"
"        padding: 14px 24px;\n"
"        font-weight: 600;\n"
""
                        "        font-size: 14px;\n"
"        color: #475569;\n"
"    }\n"
"    \n"
"    #navWidget QPushButton:hover {\n"
"        color: #3b82f6;\n"
"        border-color: #3b82f6;\n"
"        background-color: #f8fafc;\n"
"    }\n"
"   ")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.stackedWidget = QStackedWidget(self.centralwidget)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.mainScreen = QWidget()
        self.mainScreen.setObjectName(u"mainScreen")
        self.verticalLayout_2 = QVBoxLayout(self.mainScreen)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(50, 50, 50, 50)
        self.verticalSpacer_top = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_top)

        self.logoLabel = QLabel(self.mainScreen)
        self.logoLabel.setObjectName(u"logoLabel")
        self.logoLabel.setAlignment(Qt.AlignCenter)
        self.logoLabel.setStyleSheet(u"font-size: 72pt; font-weight: bold; color: #3b82f6; border: none; padding: 0px; margin: 0px; letter-spacing: 4px;")

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
        self.aboutProjectBtn.setMinimumSize(QSize(180, 55))
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        self.aboutProjectBtn.setFont(font)

        self.horizontalLayout_2.addWidget(self.aboutProjectBtn)

        self.horizontalSpacer_mid = QSpacerItem(30, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_mid)

        self.instructionBtn = QPushButton(self.mainScreen)
        self.instructionBtn.setObjectName(u"instructionBtn")
        self.instructionBtn.setMinimumSize(QSize(180, 55))
        self.instructionBtn.setFont(font)

        self.horizontalLayout_2.addWidget(self.instructionBtn)

        self.horizontalSpacer_mid2 = QSpacerItem(30, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_mid2)

        self.licenseBtn = QPushButton(self.mainScreen)
        self.licenseBtn.setObjectName(u"licenseBtn")
        self.licenseBtn.setMinimumSize(QSize(180, 55))
        self.licenseBtn.setFont(font)

        self.horizontalLayout_2.addWidget(self.licenseBtn)

        self.horizontalSpacer_right = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_right)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.verticalSpacer_bottom = QSpacerItem(20, 50, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_bottom)

        self.stackedWidget.addWidget(self.mainScreen)
        self.connectionScreen = QWidget()
        self.connectionScreen.setObjectName(u"connectionScreen")
        self.verticalLayout_4 = QVBoxLayout(self.connectionScreen)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(50, 40, 50, 40)
        self.verticalSpacer_connection_top = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_connection_top)

        self.connectionTitleLabel = QLabel(self.connectionScreen)
        self.connectionTitleLabel.setObjectName(u"connectionTitleLabel")
        self.connectionTitleLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout_4.addWidget(self.connectionTitleLabel)

        self.verticalSpacer_9 = QSpacerItem(20, 30, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer_9)

        self.modeGroupBox = QGroupBox(self.connectionScreen)
        self.modeGroupBox.setObjectName(u"modeGroupBox")
        font1 = QFont()
        font1.setPointSize(11)
        self.modeGroupBox.setFont(font1)
        self.verticalLayout_3 = QVBoxLayout(self.modeGroupBox)
        self.verticalLayout_3.setSpacing(20)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(25, 25, 25, 25)
        self.modeComboBox = QComboBox(self.modeGroupBox)
        self.modeComboBox.addItem("")
        self.modeComboBox.addItem("")
        self.modeComboBox.setObjectName(u"modeComboBox")
        font2 = QFont()
        font2.setPointSize(12)
        self.modeComboBox.setFont(font2)
        self.modeComboBox.setMinimumSize(QSize(0, 42))
        self.modeComboBox.setMaxVisibleItems(8)

        self.verticalLayout_3.addWidget(self.modeComboBox)

        self.localModeWidget = QWidget(self.modeGroupBox)
        self.localModeWidget.setObjectName(u"localModeWidget")
        self.gridLayout = QGridLayout(self.localModeWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 10, 0, 0)
        self.localModeInfoLabel = QLabel(self.localModeWidget)
        self.localModeInfoLabel.setObjectName(u"localModeInfoLabel")
        self.localModeInfoLabel.setFont(font2)
        self.localModeInfoLabel.setStyleSheet(u"color: #64748b; padding: 5px;")

        self.gridLayout.addWidget(self.localModeInfoLabel, 0, 0, 1, 2)

        self.startLocalBtn = QPushButton(self.localModeWidget)
        self.startLocalBtn.setObjectName(u"startLocalBtn")
        self.startLocalBtn.setFont(font)
        self.startLocalBtn.setMinimumSize(QSize(0, 50))

        self.gridLayout.addWidget(self.startLocalBtn, 1, 0, 1, 2)

        self.localStatusLabel = QLabel(self.localModeWidget)
        self.localStatusLabel.setObjectName(u"localStatusLabel")
        self.localStatusLabel.setFont(font2)
        self.localStatusLabel.setStyleSheet(u"color: #64748b;")

        self.gridLayout.addWidget(self.localStatusLabel, 2, 0, 1, 2)


        self.verticalLayout_3.addWidget(self.localModeWidget)

        self.remoteModeWidget = QWidget(self.modeGroupBox)
        self.remoteModeWidget.setObjectName(u"remoteModeWidget")
        self.gridLayout_2 = QGridLayout(self.remoteModeWidget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(20)
        self.gridLayout_2.setVerticalSpacing(12)
        self.gridLayout_2.setContentsMargins(0, 10, 0, 0)
        self.hostLabel = QLabel(self.remoteModeWidget)
        self.hostLabel.setObjectName(u"hostLabel")
        self.hostLabel.setFont(font2)
        self.hostLabel.setMinimumSize(QSize(100, 0))

        self.gridLayout_2.addWidget(self.hostLabel, 0, 0, 1, 1)

        self.hostLineEdit = QLineEdit(self.remoteModeWidget)
        self.hostLineEdit.setObjectName(u"hostLineEdit")
        self.hostLineEdit.setFont(font2)
        self.hostLineEdit.setMinimumSize(QSize(300, 40))

        self.gridLayout_2.addWidget(self.hostLineEdit, 0, 1, 1, 1)

        self.portLabel = QLabel(self.remoteModeWidget)
        self.portLabel.setObjectName(u"portLabel")
        self.portLabel.setFont(font2)

        self.gridLayout_2.addWidget(self.portLabel, 1, 0, 1, 1)

        self.remotePortSpinBox = QSpinBox(self.remoteModeWidget)
        self.remotePortSpinBox.setObjectName(u"remotePortSpinBox")
        self.remotePortSpinBox.setFont(font2)
        self.remotePortSpinBox.setMinimumSize(QSize(0, 40))
        self.remotePortSpinBox.setMinimum(1024)
        self.remotePortSpinBox.setMaximum(65535)
        self.remotePortSpinBox.setValue(8080)

        self.gridLayout_2.addWidget(self.remotePortSpinBox, 1, 1, 1, 1)

        self.connectBtn = QPushButton(self.remoteModeWidget)
        self.connectBtn.setObjectName(u"connectBtn")
        self.connectBtn.setFont(font)
        self.connectBtn.setMinimumSize(QSize(0, 50))

        self.gridLayout_2.addWidget(self.connectBtn, 2, 0, 1, 2)

        self.remoteStatusLabel = QLabel(self.remoteModeWidget)
        self.remoteStatusLabel.setObjectName(u"remoteStatusLabel")
        self.remoteStatusLabel.setFont(font2)
        self.remoteStatusLabel.setStyleSheet(u"color: #64748b;")

        self.gridLayout_2.addWidget(self.remoteStatusLabel, 3, 0, 1, 2)

        self.serverVersionLabel = QLabel(self.remoteModeWidget)
        self.serverVersionLabel.setObjectName(u"serverVersionLabel")
        self.serverVersionLabel.setFont(font1)
        self.serverVersionLabel.setStyleSheet(u"color: #22c55e;")

        self.gridLayout_2.addWidget(self.serverVersionLabel, 4, 0, 1, 2)


        self.verticalLayout_3.addWidget(self.remoteModeWidget)

        self.errorLabel = QLabel(self.modeGroupBox)
        self.errorLabel.setObjectName(u"errorLabel")
        self.errorLabel.setFont(font2)
        self.errorLabel.setStyleSheet(u"color: #ef4444; padding: 5px;")
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
        self.verticalLayout_5.setContentsMargins(35, 25, 35, 25)
        self.processingTitleLabel = QLabel(self.processingScreen)
        self.processingTitleLabel.setObjectName(u"processingTitleLabel")
        self.processingTitleLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout_5.addWidget(self.processingTitleLabel)

        self.verticalSpacer_process_mid1 = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer_process_mid1)

        self.processingGroupBox = QGroupBox(self.processingScreen)
        self.processingGroupBox.setObjectName(u"processingGroupBox")
        self.processingGroupBox.setFont(font1)
        self.gridLayout_3 = QGridLayout(self.processingGroupBox)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.gridLayout_3.setHorizontalSpacing(25)
        self.gridLayout_3.setVerticalSpacing(12)
        self.gridLayout_3.setContentsMargins(25, 25, 25, 25)
        self.dspMethodsLabel = QLabel(self.processingGroupBox)
        self.dspMethodsLabel.setObjectName(u"dspMethodsLabel")

        self.gridLayout_3.addWidget(self.dspMethodsLabel, 0, 0, 1, 2)

        self.noiseReductionCheck = QCheckBox(self.processingGroupBox)
        self.noiseReductionCheck.setObjectName(u"noiseReductionCheck")
        self.noiseReductionCheck.setFont(font2)
        self.noiseReductionCheck.setChecked(True)

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
        self.humRemovalCheck.setFont(font2)
        self.humRemovalCheck.setChecked(True)

        self.gridLayout_3.addWidget(self.humRemovalCheck, 2, 0, 1, 1)

        self.humFrequencyCombo = QComboBox(self.processingGroupBox)
        self.humFrequencyCombo.addItem("")
        self.humFrequencyCombo.addItem("")
        self.humFrequencyCombo.setObjectName(u"humFrequencyCombo")
        self.humFrequencyCombo.setFont(font2)
        self.humFrequencyCombo.setMinimumSize(QSize(100, 37))
        self.humFrequencyCombo.setMaxVisibleItems(8)

        self.gridLayout_3.addWidget(self.humFrequencyCombo, 2, 1, 1, 1)

        self.deEsserCheck = QCheckBox(self.processingGroupBox)
        self.deEsserCheck.setObjectName(u"deEsserCheck")
        self.deEsserCheck.setFont(font2)
        self.deEsserCheck.setChecked(True)

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
        self.eqCheck.setFont(font2)
        self.eqCheck.setChecked(True)

        self.gridLayout_3.addWidget(self.eqCheck, 4, 0, 1, 1)

        self.eqPlaceholder = QLabel(self.processingGroupBox)
        self.eqPlaceholder.setObjectName(u"eqPlaceholder")

        self.gridLayout_3.addWidget(self.eqPlaceholder, 4, 1, 1, 1)

        self.mlMethodsLabel = QLabel(self.processingGroupBox)
        self.mlMethodsLabel.setObjectName(u"mlMethodsLabel")

        self.gridLayout_3.addWidget(self.mlMethodsLabel, 5, 0, 1, 2)

        self.mlModelCombo = QComboBox(self.processingGroupBox)
        self.mlModelCombo.addItem("")
        self.mlModelCombo.addItem("")
        self.mlModelCombo.addItem("")
        self.mlModelCombo.setObjectName(u"mlModelCombo")
        self.mlModelCombo.setFont(font2)
        self.mlModelCombo.setMinimumSize(QSize(0, 40))
        self.mlModelCombo.setMaxVisibleItems(8)

        self.gridLayout_3.addWidget(self.mlModelCombo, 6, 0, 1, 2)

        self.generalSettingsLabel = QLabel(self.processingGroupBox)
        self.generalSettingsLabel.setObjectName(u"generalSettingsLabel")

        self.gridLayout_3.addWidget(self.generalSettingsLabel, 7, 0, 1, 2)

        self.normalizationCheck = QCheckBox(self.processingGroupBox)
        self.normalizationCheck.setObjectName(u"normalizationCheck")
        self.normalizationCheck.setFont(font2)
        self.normalizationCheck.setChecked(True)
        self.normalizationCheck.setMinimumSize(QSize(0, 35))

        self.gridLayout_3.addWidget(self.normalizationCheck, 8, 0, 1, 1)

        self.lufsSpinBox = QSpinBox(self.processingGroupBox)
        self.lufsSpinBox.setObjectName(u"lufsSpinBox")
        self.lufsSpinBox.setFont(font2)
        self.lufsSpinBox.setMinimumSize(QSize(120, 37))
        self.lufsSpinBox.setMinimum(-30)
        self.lufsSpinBox.setMaximum(-10)
        self.lufsSpinBox.setValue(-16)
        self.lufsSpinBox.setButtonSymbols(QAbstractSpinBox.UpDownArrows)

        self.gridLayout_3.addWidget(self.lufsSpinBox, 8, 1, 1, 1)


        self.verticalLayout_5.addWidget(self.processingGroupBox)

        self.verticalSpacer_process_mid2 = QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer_process_mid2)

        self.sourcesGroupBox = QGroupBox(self.processingScreen)
        self.sourcesGroupBox.setObjectName(u"sourcesGroupBox")
        self.sourcesGroupBox.setFont(font1)
        self.verticalLayout_6 = QVBoxLayout(self.sourcesGroupBox)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(25, 15, 25, 15)
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.selectFilesBtn = QPushButton(self.sourcesGroupBox)
        self.selectFilesBtn.setObjectName(u"selectFilesBtn")
        self.selectFilesBtn.setFont(font2)
        self.selectFilesBtn.setMinimumSize(QSize(0, 40))

        self.horizontalLayout_3.addWidget(self.selectFilesBtn)

        self.horizontalSpacer_btn = QSpacerItem(30, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_btn)

        self.selectFolderBtn = QPushButton(self.sourcesGroupBox)
        self.selectFolderBtn.setObjectName(u"selectFolderBtn")
        self.selectFolderBtn.setFont(font2)
        self.selectFolderBtn.setMinimumSize(QSize(0, 40))

        self.horizontalLayout_3.addWidget(self.selectFolderBtn)


        self.verticalLayout_6.addLayout(self.horizontalLayout_3)

        self.fileListWidget = QListWidget(self.sourcesGroupBox)
        self.fileListWidget.setObjectName(u"fileListWidget")
        self.fileListWidget.setFont(font2)
        self.fileListWidget.setMinimumSize(QSize(0, 100))

        self.verticalLayout_6.addWidget(self.fileListWidget)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.outputFolderLabel = QLabel(self.sourcesGroupBox)
        self.outputFolderLabel.setObjectName(u"outputFolderLabel")
        self.outputFolderLabel.setFont(font2)

        self.horizontalLayout_4.addWidget(self.outputFolderLabel)

        self.outputFolderLineEdit = QLineEdit(self.sourcesGroupBox)
        self.outputFolderLineEdit.setObjectName(u"outputFolderLineEdit")
        self.outputFolderLineEdit.setFont(font2)
        self.outputFolderLineEdit.setMinimumSize(QSize(0, 38))

        self.horizontalLayout_4.addWidget(self.outputFolderLineEdit)

        self.browseOutputBtn = QPushButton(self.sourcesGroupBox)
        self.browseOutputBtn.setObjectName(u"browseOutputBtn")
        self.browseOutputBtn.setFont(font2)
        self.browseOutputBtn.setMinimumSize(QSize(90, 38))

        self.horizontalLayout_4.addWidget(self.browseOutputBtn)


        self.verticalLayout_6.addLayout(self.horizontalLayout_4)

        self.overwriteCheck = QCheckBox(self.sourcesGroupBox)
        self.overwriteCheck.setObjectName(u"overwriteCheck")
        self.overwriteCheck.setFont(font2)

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
        font3 = QFont()
        font3.setPointSize(14)
        font3.setBold(True)
        self.startProcessingBtn.setFont(font3)
        self.startProcessingBtn.setMinimumSize(QSize(240, 52))

        self.horizontalLayout_5.addWidget(self.startProcessingBtn)

        self.horizontalSpacer_process_mid = QSpacerItem(30, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_process_mid)

        self.clearQueueBtn = QPushButton(self.processingScreen)
        self.clearQueueBtn.setObjectName(u"clearQueueBtn")
        self.clearQueueBtn.setFont(font3)
        self.clearQueueBtn.setMinimumSize(QSize(240, 52))

        self.horizontalLayout_5.addWidget(self.clearQueueBtn)

        self.horizontalSpacer_process_right = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_process_right)


        self.verticalLayout_5.addLayout(self.horizontalLayout_5)

        self.formatsLabel = QLabel(self.processingScreen)
        self.formatsLabel.setObjectName(u"formatsLabel")
        self.formatsLabel.setAlignment(Qt.AlignCenter)

        self.verticalLayout_5.addWidget(self.formatsLabel)

        self.verticalSpacer_process_bottom = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer_process_bottom)

        self.stackedWidget.addWidget(self.processingScreen)
        self.progressScreen = QWidget()
        self.progressScreen.setObjectName(u"progressScreen")
        self.verticalLayout_7 = QVBoxLayout(self.progressScreen)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(35, 25, 35, 25)
        self.titleLayout = QHBoxLayout()
        self.titleLayout.setSpacing(0)
        self.titleLayout.setObjectName(u"titleLayout")
        self.titleLeftSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.titleLayout.addItem(self.titleLeftSpacer)

        self.progressTitleLabel = QLabel(self.progressScreen)
        self.progressTitleLabel.setObjectName(u"progressTitleLabel")
        self.progressTitleLabel.setAlignment(Qt.AlignCenter)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.progressTitleLabel.sizePolicy().hasHeightForWidth())
        self.progressTitleLabel.setSizePolicy(sizePolicy)

        self.titleLayout.addWidget(self.progressTitleLabel)

        self.openLogBtn = QPushButton(self.progressScreen)
        self.openLogBtn.setObjectName(u"openLogBtn")
        self.openLogBtn.setFont(font2)
        self.openLogBtn.setMinimumSize(QSize(120, 32))
        self.openLogBtn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.titleLayout.addWidget(self.openLogBtn)

        self.titleRightSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.titleLayout.addItem(self.titleRightSpacer)


        self.verticalLayout_7.addLayout(self.titleLayout)

        self.verticalSpacer_progress_mid1 = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_progress_mid1)

        self.taskTable = QTableWidget(self.progressScreen)
        if (self.taskTable.columnCount() < 5):
            self.taskTable.setColumnCount(5)
        __qtablewidgetitem = QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.taskTable.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        self.taskTable.setObjectName(u"taskTable")
        self.taskTable.setMinimumSize(QSize(0, 200))
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(1)
        sizePolicy1.setHeightForWidth(self.taskTable.sizePolicy().hasHeightForWidth())
        self.taskTable.setSizePolicy(sizePolicy1)
        self.taskTable.setFont(font1)
        self.taskTable.setAlternatingRowColors(True)
        self.taskTable.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.verticalLayout_7.addWidget(self.taskTable)

        self.verticalSpacer_progress_mid2 = QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_progress_mid2)

        self.progressGroupBox = QGroupBox(self.progressScreen)
        self.progressGroupBox.setObjectName(u"progressGroupBox")
        self.progressGroupBox.setFont(font1)
        self.gridLayout_progress = QGridLayout(self.progressGroupBox)
        self.gridLayout_progress.setObjectName(u"gridLayout_progress")
        self.gridLayout_progress.setHorizontalSpacing(20)
        self.gridLayout_progress.setVerticalSpacing(10)
        self.gridLayout_progress.setContentsMargins(20, 15, 20, 15)
        self.filesProgressLabel = QLabel(self.progressGroupBox)
        self.filesProgressLabel.setObjectName(u"filesProgressLabel")
        self.filesProgressLabel.setFont(font2)

        self.gridLayout_progress.addWidget(self.filesProgressLabel, 0, 0, 1, 1)

        self.filesProgress = QProgressBar(self.progressGroupBox)
        self.filesProgress.setObjectName(u"filesProgress")
        self.filesProgress.setFont(font1)
        self.filesProgress.setValue(0)

        self.gridLayout_progress.addWidget(self.filesProgress, 0, 1, 1, 1)

        self.totalSegmentsLabel = QLabel(self.progressGroupBox)
        self.totalSegmentsLabel.setObjectName(u"totalSegmentsLabel")
        self.totalSegmentsLabel.setFont(font2)

        self.gridLayout_progress.addWidget(self.totalSegmentsLabel, 1, 0, 1, 1)

        self.totalSegmentsProgress = QProgressBar(self.progressGroupBox)
        self.totalSegmentsProgress.setObjectName(u"totalSegmentsProgress")
        self.totalSegmentsProgress.setFont(font1)
        self.totalSegmentsProgress.setValue(0)

        self.gridLayout_progress.addWidget(self.totalSegmentsProgress, 1, 1, 1, 1)

        self.timeRemainingLabel = QLabel(self.progressGroupBox)
        self.timeRemainingLabel.setObjectName(u"timeRemainingLabel")
        self.timeRemainingLabel.setFont(font2)

        self.gridLayout_progress.addWidget(self.timeRemainingLabel, 2, 0, 1, 1)

        self.timeRemainingValueLabel = QLabel(self.progressGroupBox)
        self.timeRemainingValueLabel.setObjectName(u"timeRemainingValueLabel")
        self.timeRemainingValueLabel.setFont(font2)

        self.gridLayout_progress.addWidget(self.timeRemainingValueLabel, 2, 1, 1, 1)

        self.statsLabel = QLabel(self.progressGroupBox)
        self.statsLabel.setObjectName(u"statsLabel")
        self.statsLabel.setFont(font2)

        self.gridLayout_progress.addWidget(self.statsLabel, 3, 0, 1, 1)

        self.statsValueLabel = QLabel(self.progressGroupBox)
        self.statsValueLabel.setObjectName(u"statsValueLabel")
        self.statsValueLabel.setFont(font1)
        self.statsValueLabel.setStyleSheet(u"color: #475569;")

        self.gridLayout_progress.addWidget(self.statsValueLabel, 3, 1, 1, 1)


        self.verticalLayout_7.addWidget(self.progressGroupBox)

        self.errorNotificationLabel = QLabel(self.progressScreen)
        self.errorNotificationLabel.setObjectName(u"errorNotificationLabel")
        self.errorNotificationLabel.setFont(font2)
        self.errorNotificationLabel.setStyleSheet(u"color: #ef4444; padding: 5px;")
        self.errorNotificationLabel.setWordWrap(True)

        self.verticalLayout_7.addWidget(self.errorNotificationLabel)

        self.mainButtonsLayout = QHBoxLayout()
        self.mainButtonsLayout.setSpacing(0)
        self.mainButtonsLayout.setObjectName(u"mainButtonsLayout")
        self.leftMainSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.mainButtonsLayout.addItem(self.leftMainSpacer)

        self.pauseTasksBtn = QPushButton(self.progressScreen)
        self.pauseTasksBtn.setObjectName(u"pauseTasksBtn")
        font4 = QFont()
        font4.setPointSize(13)
        self.pauseTasksBtn.setFont(font4)
        self.pauseTasksBtn.setMinimumSize(QSize(180, 48))
        self.pauseTasksBtn.setVisible(False)

        self.mainButtonsLayout.addWidget(self.pauseTasksBtn)

        self.midSpacer1 = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.mainButtonsLayout.addItem(self.midSpacer1)

        self.pauseSelectedBtn = QPushButton(self.progressScreen)
        self.pauseSelectedBtn.setObjectName(u"pauseSelectedBtn")
        self.pauseSelectedBtn.setFont(font4)
        self.pauseSelectedBtn.setMinimumSize(QSize(220, 48))
        self.pauseSelectedBtn.setEnabled(False)

        self.mainButtonsLayout.addWidget(self.pauseSelectedBtn)

        self.midSpacer2 = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.mainButtonsLayout.addItem(self.midSpacer2)

        self.resumeSelectedBtn = QPushButton(self.progressScreen)
        self.resumeSelectedBtn.setObjectName(u"resumeSelectedBtn")
        self.resumeSelectedBtn.setFont(font4)
        self.resumeSelectedBtn.setMinimumSize(QSize(220, 48))
        self.resumeSelectedBtn.setEnabled(False)

        self.mainButtonsLayout.addWidget(self.resumeSelectedBtn)

        self.midSpacer3 = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.mainButtonsLayout.addItem(self.midSpacer3)

        self.cancelSelectedBtn = QPushButton(self.progressScreen)
        self.cancelSelectedBtn.setObjectName(u"cancelSelectedBtn")
        self.cancelSelectedBtn.setFont(font4)
        self.cancelSelectedBtn.setMinimumSize(QSize(220, 48))
        self.cancelSelectedBtn.setEnabled(False)

        self.mainButtonsLayout.addWidget(self.cancelSelectedBtn)

        self.midSpacer4 = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.mainButtonsLayout.addItem(self.midSpacer4)

        self.clearFinishedBtn = QPushButton(self.progressScreen)
        self.clearFinishedBtn.setObjectName(u"clearFinishedBtn")
        self.clearFinishedBtn.setFont(font4)
        self.clearFinishedBtn.setMinimumSize(QSize(200, 48))

        self.mainButtonsLayout.addWidget(self.clearFinishedBtn)

        self.rightMainSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.mainButtonsLayout.addItem(self.rightMainSpacer)


        self.verticalLayout_7.addLayout(self.mainButtonsLayout)

        self.verticalSpacer_progress_bottom = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_progress_bottom)

        self.stackedWidget.addWidget(self.progressScreen)

        self.verticalLayout.addWidget(self.stackedWidget)

        self.navWidget = QWidget(self.centralwidget)
        self.navWidget.setObjectName(u"navWidget")
        self.horizontalLayout_8 = QHBoxLayout(self.navWidget)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(30, 12, 30, 12)
        self.mainScreenBtn = QPushButton(self.navWidget)
        self.mainScreenBtn.setObjectName(u"mainScreenBtn")
        self.mainScreenBtn.setFont(font3)
        self.mainScreenBtn.setMinimumSize(QSize(0, 56))
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(1)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.mainScreenBtn.sizePolicy().hasHeightForWidth())
        self.mainScreenBtn.setSizePolicy(sizePolicy2)

        self.horizontalLayout_8.addWidget(self.mainScreenBtn)

        self.connectionScreenBtn = QPushButton(self.navWidget)
        self.connectionScreenBtn.setObjectName(u"connectionScreenBtn")
        self.connectionScreenBtn.setFont(font3)
        self.connectionScreenBtn.setMinimumSize(QSize(0, 56))
        sizePolicy2.setHeightForWidth(self.connectionScreenBtn.sizePolicy().hasHeightForWidth())
        self.connectionScreenBtn.setSizePolicy(sizePolicy2)

        self.horizontalLayout_8.addWidget(self.connectionScreenBtn)

        self.processingScreenBtn = QPushButton(self.navWidget)
        self.processingScreenBtn.setObjectName(u"processingScreenBtn")
        self.processingScreenBtn.setFont(font3)
        self.processingScreenBtn.setMinimumSize(QSize(0, 56))
        sizePolicy2.setHeightForWidth(self.processingScreenBtn.sizePolicy().hasHeightForWidth())
        self.processingScreenBtn.setSizePolicy(sizePolicy2)

        self.horizontalLayout_8.addWidget(self.processingScreenBtn)

        self.progressScreenBtn = QPushButton(self.navWidget)
        self.progressScreenBtn.setObjectName(u"progressScreenBtn")
        self.progressScreenBtn.setFont(font3)
        self.progressScreenBtn.setMinimumSize(QSize(0, 56))
        sizePolicy2.setHeightForWidth(self.progressScreenBtn.sizePolicy().hasHeightForWidth())
        self.progressScreenBtn.setSizePolicy(sizePolicy2)

        self.horizontalLayout_8.addWidget(self.progressScreenBtn)


        self.verticalLayout.addWidget(self.navWidget)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.stackedWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"SpeechEQ v1.0", None))
        self.logoLabel.setText(QCoreApplication.translate("MainWindow", u"SPEECH EQ", None))
        self.appTitleLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:32pt; font-weight:700; color:#1e293b;\">SpeechEQ</span><br/><span style=\" font-size:14pt; color:#64748b;\">\u0412\u0435\u0440\u0441\u0438\u044f 1.0</span></p></body></html>", None))
        self.descriptionLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:16pt; color:#334155;\">\u041f\u0440\u043e\u0444\u0435\u0441\u0441\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u0430\u044f \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u0438 \u0443\u043b\u0443\u0447\u0448\u0435\u043d\u0438\u0435 \u0430\u0443\u0434\u0438\u043e</span></p><p align=\"center\"><span style=\" font-size:12pt; color:#64748b;\">\u041f\u043e\u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0448\u0443\u043c\u0430, \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0433\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u0438, \u0443\u0434\u0430\u043b\u0435\u043d\u0438\u0435 \u0433\u0443\u043b\u0430 \u0438 \u044d\u0445\u0430</span></p></body></html>", None))
        self.aboutProjectBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e \u041f\u0420\u041e\u0415\u041a\u0422\u0415", None))
        self.instructionBtn.setText(QCoreApplication.translate("MainWindow", u"\u0418\u041d\u0421\u0422\u0420\u0423\u041a\u0426\u0418\u042f", None))
        self.licenseBtn.setText(QCoreApplication.translate("MainWindow", u"\u041b\u0418\u0426\u0415\u041d\u0417\u0418\u042f", None))
        self.connectionTitleLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:24pt; font-weight:700; color:#1e293b;\">\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u043a \u0441\u0435\u0440\u0432\u0435\u0440\u0443 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438</span></p></body></html>", None))
        self.modeGroupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u0420\u0435\u0436\u0438\u043c \u0440\u0430\u0431\u043e\u0442\u044b", None))
        self.modeComboBox.setItemText(0, QCoreApplication.translate("MainWindow", u"\u041b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0440\u0435\u0436\u0438\u043c", None))
        self.modeComboBox.setItemText(1, QCoreApplication.translate("MainWindow", u"\u0423\u0434\u0430\u043b\u0451\u043d\u043d\u044b\u0439 \u0441\u0435\u0440\u0432\u0435\u0440", None))

        self.localModeInfoLabel.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0430 \u043d\u0430 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u043c \u043a\u043e\u043c\u043f\u044c\u044e\u0442\u0435\u0440\u0435 \u0431\u0435\u0437 \u0441\u0435\u0440\u0432\u0435\u0440\u0430", None))
        self.startLocalBtn.setText(QCoreApplication.translate("MainWindow", u"\u0417\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0440\u0435\u0436\u0438\u043c", None))
        self.localStatusLabel.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0442\u0430\u0442\u0443\u0441: \u043d\u0435 \u0437\u0430\u043f\u0443\u0449\u0435\u043d", None))
        self.hostLabel.setText(QCoreApplication.translate("MainWindow", u"\u0410\u0434\u0440\u0435\u0441 / \u0445\u043e\u0441\u0442:", None))
        self.hostLineEdit.setText(QCoreApplication.translate("MainWindow", u"localhost", None))
        self.portLabel.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0440\u0442:", None))
        self.connectBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u043e\u0434\u043a\u043b\u044e\u0447\u0438\u0442\u044c\u0441\u044f", None))
        self.remoteStatusLabel.setText(QCoreApplication.translate("MainWindow", u"\u041d\u0435 \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u043e", None))
        self.serverVersionLabel.setText("")
        self.errorLabel.setText("")
        self.processingTitleLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:22pt; font-weight:700; color:#1e293b;\">\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0430 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438 \u0438 \u0432\u044b\u0431\u043e\u0440 \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u043e\u0432</span></p></body></html>", None))
        self.processingGroupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u041c\u0435\u0442\u043e\u0434\u044b \u0443\u043b\u0443\u0447\u0448\u0435\u043d\u0438\u044f \u0430\u0443\u0434\u0438\u043e", None))
        self.dspMethodsLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:14pt; font-weight:700;\">DSP-\u043c\u0435\u0442\u043e\u0434\u044b:</span></p></body></html>", None))
        self.noiseReductionCheck.setText(QCoreApplication.translate("MainWindow", u"\u0428\u0443\u043c\u043e\u043f\u043e\u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435", None))
        self.humRemovalCheck.setText(QCoreApplication.translate("MainWindow", u"\u0423\u0434\u0430\u043b\u0435\u043d\u0438\u0435 \u0433\u0443\u043b\u0430 50/60 \u0413\u0446", None))
        self.humFrequencyCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"50 \u0413\u0446", None))
        self.humFrequencyCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"60 \u0413\u0446", None))

        self.deEsserCheck.setText(QCoreApplication.translate("MainWindow", u"\u0414\u0435-\u044d\u0441\u0441\u0435\u0440", None))
        self.eqCheck.setText(QCoreApplication.translate("MainWindow", u"\u042d\u043a\u0432\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u043f\u043e\u0434 \u0440\u0435\u0447\u044c", None))
        self.eqPlaceholder.setText("")
        self.mlMethodsLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:14pt; font-weight:700;\">ML-\u043c\u0435\u0442\u043e\u0434\u044b:</span></p></body></html>", None))
        self.mlModelCombo.setItemText(0, QCoreApplication.translate("MainWindow", u"\u041d\u0435 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u044c ML-\u043c\u043e\u0434\u0435\u043b\u0438", None))
        self.mlModelCombo.setItemText(1, QCoreApplication.translate("MainWindow", u"\u041c\u043e\u0434\u0435\u043b\u044c \u0443\u043b\u0443\u0447\u0448\u0435\u043d\u0438\u044f \u0440\u0435\u0447\u0438 v1", None))
        self.mlModelCombo.setItemText(2, QCoreApplication.translate("MainWindow", u"\u041c\u043e\u0434\u0435\u043b\u044c \u0432\u043e\u0441\u0441\u0442\u0430\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f \u0440\u0435\u0447\u0438 v2", None))

        self.generalSettingsLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p><span style=\" font-size:14pt; font-weight:700;\">\u041e\u0431\u0449\u0438\u0435 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438:</span></p></body></html>", None))
        self.normalizationCheck.setText(QCoreApplication.translate("MainWindow", u"\u0410\u0432\u0442\u043e\u043c\u0430\u0442\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u043d\u043e\u0440\u043c\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f \u0433\u0440\u043e\u043c\u043a\u043e\u0441\u0442\u0438 (LUFS)", None))
        self.lufsSpinBox.setSuffix(QCoreApplication.translate("MainWindow", u" LUFS", None))
        self.sourcesGroupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u043e\u0440 \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u043e\u0432", None))
        self.selectFilesBtn.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u0444\u0430\u0439\u043b\u044b...", None))
        self.selectFolderBtn.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0431\u0440\u0430\u0442\u044c \u043f\u0430\u043f\u043a\u0443...", None))
        self.outputFolderLabel.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0430\u043f\u043a\u0430 \u0434\u043b\u044f \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0438\u044f:", None))
        self.browseOutputBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u0437\u043e\u0440...", None))
        self.overwriteCheck.setText(QCoreApplication.translate("MainWindow", u"\u0421\u043e\u0445\u0440\u0430\u043d\u044f\u0442\u044c \u0432 \u0442\u043e\u0442 \u0436\u0435 \u0444\u0430\u0439\u043b (\u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441\u044c)", None))
        self.startProcessingBtn.setText(QCoreApplication.translate("MainWindow", u"\u041d\u0410\u0427\u0410\u0422\u042c \u041e\u0411\u0420\u0410\u0411\u041e\u0422\u041a\u0423", None))
        self.clearQueueBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0427\u0418\u0421\u0422\u0418\u0422\u042c \u041e\u0427\u0415\u0420\u0415\u0414\u042c", None))
        self.formatsLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:11px; color:#64748b;\">\u041f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u0435\u043c\u044b\u0435 \u0444\u043e\u0440\u043c\u0430\u0442\u044b: MP4, MOV, MKV, AVI, FLV, WMV</span></p></body></html>", None))
        self.progressTitleLabel.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p align=\"center\"><span style=\" font-size:22pt; font-weight:700; color:#1e293b;\">\u041e\u0447\u0435\u0440\u0435\u0434\u044c \u0438 \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0438</span></p></body></html>", None))
        self.openLogBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043b\u043e\u0433", None))
        ___qtablewidgetitem = self.taskTable.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("MainWindow", u"\u0424\u0430\u0439\u043b (\u0432\u0445\u043e\u0434\u043d\u043e\u0439)", None));
        ___qtablewidgetitem1 = self.taskTable.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("MainWindow", u"\u0412\u044b\u0445\u043e\u0434\u043d\u043e\u0439 \u0444\u0430\u0439\u043b", None));
        ___qtablewidgetitem2 = self.taskTable.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 (\u0441\u0435\u0433\u043c\u0435\u043d\u0442\u044b)", None));
        ___qtablewidgetitem3 = self.taskTable.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("MainWindow", u"\u0414\u043b\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0441\u0442\u044c", None));
        ___qtablewidgetitem4 = self.taskTable.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0442\u0430\u0442\u0443\u0441", None));
        self.progressGroupBox.setTitle(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u0449\u0438\u0439 \u043f\u0440\u043e\u0433\u0440\u0435\u0441\u0441", None))
        self.filesProgressLabel.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u043f\u043e \u0444\u0430\u0439\u043b\u0430\u043c:", None))
        self.totalSegmentsLabel.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u043e\u0433\u0440\u0435\u0441\u0441 \u043f\u043e \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u0430\u043c:", None))
        self.timeRemainingLabel.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0441\u0442\u0430\u0432\u0448\u0435\u0435\u0441\u044f \u0432\u0440\u0435\u043c\u044f:", None))
        self.timeRemainingValueLabel.setText(QCoreApplication.translate("MainWindow", u"--", None))
        self.statsLabel.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430:", None))
        self.statsValueLabel.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0431\u0440\u0430\u0431\u043e\u0442\u0430\u043d\u043e: 0 / 0 \u0444\u0430\u0439\u043b\u043e\u0432, \u0441\u0435\u0433\u043c\u0435\u043d\u0442\u043e\u0432: 0 / 0", None))
        self.errorNotificationLabel.setText("")
        self.pauseTasksBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0430\u0443\u0437\u0430 (\u0433\u043b\u043e\u0431\u0430\u043b\u044c\u043d\u0430\u044f)", None))
        self.pauseSelectedBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0440\u0438\u043e\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u044c \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0435", None))
        self.resumeSelectedBtn.setText(QCoreApplication.translate("MainWindow", u"\u0412\u043e\u0437\u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0435", None))
        self.cancelSelectedBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u044b\u0435", None))
        self.clearFinishedBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c \u0433\u043e\u0442\u043e\u0432\u044b\u0435", None))
        self.mainScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u0421\u0422\u0410\u0420\u0422", None))
        self.connectionScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u041e\u0414\u041a\u041b\u042e\u0427\u0415\u041d\u0418\u0415", None))
        self.processingScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u041e\u0411\u0420\u0410\u0411\u041e\u0422\u041a\u0410", None))
        self.progressScreenBtn.setText(QCoreApplication.translate("MainWindow", u"\u041f\u0420\u041e\u0413\u0420\u0415\u0421\u0421", None))
    # retranslateUi

