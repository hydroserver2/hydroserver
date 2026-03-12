import os
import json
import sys
import logging
import webbrowser
import subprocess
import hydroserverpy
from scheduler import DataLoaderScheduler
from logging.handlers import RotatingFileHandler
from appdirs import user_data_dir
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout, QLabel, \
     QLineEdit, QHBoxLayout, QPushButton, QMessageBox, QCheckBox


class StreamingDataLoader(QMainWindow):

    def __init__(self):
        super(StreamingDataLoader, self).__init__()

        self.service = None
        self.scheduler = None

        self.instance_name = None
        self.workspace_name = None
        self.hydroserver_url = None
        self.hydroserver_api_key = None
        self.hydroserver_username = None
        self.hydroserver_password = None
        self.connected = False
        self.paused = False

        self.status_action = None
        self.connection_action = None
        self.dashboard_action = None
        self.logging_action = None
        self.pause_action = None
        self.quit_action = None

        self.url_input = None
        self.workspace_input = None
        self.instance_input = None
        self.api_key_input = None
        self.email_input = None
        self.password_input = None
        self.auth_toggle_checkbox = None

        self.api_key_input_widget = None
        self.basic_auth_input_widget = None

        self.assets_path = getattr(sys, '_MEIPASS', 'assets')
        self.app_dir = user_data_dir('Streaming Data Loader', 'CIROH')
        self.app_version = 'dev'

        if not os.path.exists(self.app_dir):
            os.makedirs(self.app_dir)

        try:
            with open(os.path.join(self.assets_path, 'version.txt')) as f:
                self.app_version = f.read().strip()
        except FileNotFoundError:
            pass

        self.init_ui()
        self.get_settings()

        data_loader = self.connect_to_hydroserver()

        self.update_gui()

        if self.connected:
            self.scheduler = DataLoaderScheduler(
                hs_api=self.service,
                data_loader=data_loader
            )

        if not self.connected:
            self.show()

    def init_ui(self):
        """Builds the app UI including system tray menu and connection window"""

        # System Tray Icon
        tray_icon = QSystemTrayIcon(self)
        tray_icon_image = QIcon(os.path.join(self.assets_path, "app_icon.png"))
        tray_icon_image.setIsMask(True)
        tray_icon.setIcon(tray_icon_image)

        # System Tray Menu
        tray_menu = QMenu(self)
        self.setup_tray_menu_status(tray_menu)
        tray_menu.addSeparator()
        self.setup_tray_menu_actions(tray_menu)
        tray_menu.addSeparator()
        self.setup_tray_menu_controls(tray_menu)
        tray_icon.setContextMenu(tray_menu)
        tray_icon.show()

        # HydroServer Connection Window
        self.setWindowTitle(f'Streaming Data Loader ({self.app_version})')
        self.setGeometry(300, 300, 550, 550)
        self.setFixedSize(550, 550)
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        self.setup_connection_dialog(layout)

    def setup_tray_menu_status(self, tray_menu):
        """Components to build menu status"""

        # System Tray Menu Status
        self.status_action = QAction(self)
        self.status_action.setEnabled(False)
        tray_menu.addAction(self.status_action)

    def setup_tray_menu_actions(self, tray_menu):
        """Components to build menu actions"""

        # System Tray Menu Open Connection Window
        self.connection_action = QAction('HydroServer Connection', self)
        self.connection_action.triggered.connect(lambda: self.show())
        tray_menu.addAction(self.connection_action)

        # System Tray Menu View Tasks
        self.dashboard_action = QAction('View Tasks', self)
        dashboard_icon = QIcon(os.path.join(self.assets_path, 'database.png'))
        dashboard_icon.setIsMask(True)
        self.dashboard_action.setIcon(dashboard_icon)
        self.dashboard_action.triggered.connect(self.open_orchestration_dashboard)
        tray_menu.addAction(self.dashboard_action)

        # System Tray Menu View Logs
        self.logging_action = QAction('View Log Output', self)
        logging_icon = QIcon(os.path.join(self.assets_path, 'description.png'))
        logging_icon.setIsMask(True)
        self.logging_action.setIcon(logging_icon)
        self.logging_action.triggered.connect(self.open_logs)
        tray_menu.addAction(self.logging_action)

    def setup_tray_menu_controls(self, tray_menu):
        """Components to build menu controls"""

        # System Tray Menu Pause/Resume App
        self.pause_action = QAction('Pause', self)
        self.pause_action.triggered.connect(self.toggle_paused)
        tray_menu.addAction(self.pause_action)

        # System Tray Menu Shut Down App
        self.quit_action = QAction('Shut Down', self)
        quit_icon = QIcon(os.path.join(self.assets_path, 'exit.png'))
        quit_icon.setIsMask(True)
        self.quit_action.setIcon(quit_icon)
        self.quit_action.triggered.connect(app.quit)
        tray_menu.addAction(self.quit_action)

    def setup_connection_dialog(self, layout):
        """Components to build connection window"""

        # HydroServer Logo
        logo_label = QLabel(self)
        logo_label.setPixmap(
            QPixmap(os.path.join(self.assets_path, 'setup_icon.png')).scaledToWidth(500, Qt.SmoothTransformation)
        )
        logo_layout = QVBoxLayout()
        logo_layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        logo_layout.setContentsMargins(10, 10, 10, 10)
        layout.addLayout(logo_layout)

        # Window Settings
        label_width = 150
        input_layout = QVBoxLayout()
        input_layout.setContentsMargins(20, 20, 20, 20)

        # HydroServer URL Input
        url_box_layout = QHBoxLayout()
        url_label = QLabel(f'HydroServer URL:', self)
        url_label.setFixedWidth(label_width)
        url_box_layout.addWidget(url_label, alignment=Qt.AlignRight)
        self.url_input = QLineEdit(self)
        self.url_input.setStyleSheet('padding: 5px;')
        self.url_input.setPlaceholderText('Enter the HydroServer URL to connect to.')
        url_box_layout.addWidget(self.url_input)
        layout.addLayout(url_box_layout)

        # Workspace Name Input
        workspace_box_layout = QHBoxLayout()
        workspace_label = QLabel(f'Workspace Name:', self)
        workspace_label.setFixedWidth(label_width)
        workspace_box_layout.addWidget(workspace_label, alignment=Qt.AlignRight)
        self.workspace_input = QLineEdit(self)
        self.workspace_input.setStyleSheet('padding: 5px;')
        self.workspace_input.setPlaceholderText('Enter the name of the workspace to use.')
        workspace_box_layout.addWidget(self.workspace_input)
        layout.addLayout(workspace_box_layout)

        # Instance Name Input
        instance_box_layout = QHBoxLayout()
        instance_label = QLabel(f'Instance Name:', self)
        instance_label.setFixedWidth(label_width)
        instance_box_layout.addWidget(instance_label, alignment=Qt.AlignRight)
        self.instance_input = QLineEdit(self)
        self.instance_input.setStyleSheet('padding: 5px;')
        self.instance_input.setPlaceholderText('Enter a name for this streaming data loader.')
        instance_box_layout.addWidget(self.instance_input)
        layout.addLayout(instance_box_layout)

        # API Key Authentication Input
        self.api_key_input_widget = QWidget(self)
        api_key_input_layout = QVBoxLayout()
        self.api_key_input_widget.setLayout(api_key_input_layout)
        api_key_input_layout.setContentsMargins(0, 0, 0, 0)

        api_key_box_layout = QHBoxLayout()
        api_key_label = QLabel('HydroServer API Key:', self)
        api_key_label.setFixedWidth(label_width)
        api_key_box_layout.addWidget(api_key_label, alignment=Qt.AlignRight)
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setStyleSheet('padding: 5px;')
        self.api_key_input.setEchoMode(getattr(QLineEdit, 'Password'))
        self.api_key_input.setPlaceholderText('Enter your HydroServer API key.')
        api_key_box_layout.addWidget(self.api_key_input)
        api_key_input_layout.addLayout(api_key_box_layout)

        layout.addWidget(self.api_key_input_widget, alignment=Qt.AlignTop)

        # Basic Authentication Input
        self.basic_auth_input_widget = QWidget(self)
        basic_auth_input_layout = QVBoxLayout()
        self.basic_auth_input_widget.setLayout(basic_auth_input_layout)
        basic_auth_input_layout.setContentsMargins(0, 0, 0, 0)

        email_box_layout = QHBoxLayout()
        email_label = QLabel('HydroServer Email:', self)
        email_label.setFixedWidth(label_width)
        email_box_layout.addWidget(email_label, alignment=Qt.AlignRight)
        self.email_input = QLineEdit(self)
        self.email_input.setStyleSheet('padding: 5px;')
        self.email_input.setPlaceholderText('Enter your HydroServer Email.')
        email_box_layout.addWidget(self.email_input)
        basic_auth_input_layout.addLayout(email_box_layout)

        password_box_layout = QHBoxLayout()
        password_label = QLabel('HydroServer Password:', self)
        password_label.setFixedWidth(label_width)
        password_box_layout.addWidget(password_label, alignment=Qt.AlignRight)
        self.password_input = QLineEdit(self)
        self.password_input.setStyleSheet('padding: 5px;')
        self.password_input.setEchoMode(getattr(QLineEdit, 'Password'))
        self.password_input.setPlaceholderText('Enter your HydroServer Password.')
        password_box_layout.addWidget(self.password_input)
        basic_auth_input_layout.addLayout(password_box_layout)

        layout.addWidget(self.basic_auth_input_widget)

        # Authentication Mode Toggle
        self.auth_toggle_checkbox = QCheckBox("Authenticate with username and password", self)
        self.auth_toggle_checkbox.setStyleSheet('padding: 5px;')
        self.auth_toggle_checkbox.stateChanged.connect(lambda: self.toggle_auth_input())
        layout.addWidget(self.auth_toggle_checkbox)

        # Window Actions Settings
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 20, 20)
        actions_layout.addStretch(1)

        # Confirm Button
        confirm_button = QPushButton('Confirm', self)
        confirm_button.clicked.connect(lambda: self.confirm_settings())
        confirm_button.setStyleSheet(
            'background-color: #007BFF; color: white; border: 1px solid #007BFF; border-radius: 8px; padding: 8px;'
            'hover { background-color: #0056b3; }'
        )
        confirm_button.setCursor(Qt.PointingHandCursor)
        confirm_button.setFixedSize(80, 30)
        actions_layout.addWidget(confirm_button)

        # Cancel Button
        cancel_button = QPushButton('Cancel', self)
        cancel_button.clicked.connect(lambda: self.hide())
        cancel_button.setStyleSheet(
            'border: 1px solid #707070; border-radius: 8px; padding: 8px;'
            'hover { background-color: #e0e0e0; }'
        )
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setFixedSize(80, 30)
        actions_layout.addWidget(cancel_button)

        layout.addLayout(actions_layout)

    def toggle_auth_input(self):
        """Switches between API key and email/password authentication inputs."""

        if self.auth_toggle_checkbox.isChecked():
            self.api_key_input_widget.setVisible(False)
            self.basic_auth_input_widget.setVisible(True)
        else:
            self.basic_auth_input_widget.setVisible(False)
            self.api_key_input_widget.setVisible(True)

    def open_orchestration_dashboard(self):
        """Opens user's Orchestration Dashboard in a browser window"""

        webbrowser.open(f'{self.hydroserver_url}/orchestration')

    def open_logs(self):
        """Opens app log file in a text viewer"""

        subprocess.call(['open', os.path.join(self.app_dir, 'streaming_data_loader.log')])

    def toggle_paused(self):
        """Toggles whether the app is paused or not"""

        self.paused = not self.paused
        if self.connected and self.paused is True:
            self.scheduler.pause()
        elif self.connected and self.paused is False:
            self.scheduler.resume()
        self.update_gui()

    def connect_to_hydroserver(self):
        """Uses connection settings to register app on HydroServer"""

        if not all([
            self.hydroserver_url, self.workspace_name, self.instance_name
        ]) or (
            not (self.hydroserver_username and self.hydroserver_password) and not self.hydroserver_api_key
        ):
            self.connected = False
            return 'Missing required connection parameters.'

        try:
            if self.hydroserver_api_key:
                self.service = hydroserverpy.HydroServer(
                    host=self.hydroserver_url,
                    apikey=self.hydroserver_api_key
                )
            else:
                self.service = hydroserverpy.HydroServer(
                    host=self.hydroserver_url,
                    email=self.hydroserver_username,
                    password=self.hydroserver_password
                )
        except:
            self.connected = False
            return 'Failed to connect to HydroServer.'

        workspaces = self.service.workspaces.list(is_associated=True, fetch_all=True)
        workspace = next((workspace for workspace in workspaces.items if workspace.name == self.workspace_name), None)

        orchestration_systems = self.service.orchestrationsystems.list(workspace=workspace, fetch_all=True)
        orchestration_system = next((
            orchestration_system for orchestration_system in orchestration_systems.items
            if orchestration_system.name == self.instance_name
        ), None)

        if not workspace:
            self.connected = False
            return 'The provided workspace was not found.'

        if not orchestration_system:
            try:
                orchestration_system = self.service.orchestrationsystems.create(
                    name=self.instance_name,
                    workspace=workspace,
                    orchestration_system_type="SDL"
                )
            except (Exception,) as e:
                print(e)
                return 'Failed to register Streaming Data Loader instance.'

        self.connected = True

        return orchestration_system

    def get_settings(self):
        """Get settings from settings file"""

        settings_path = os.path.join(self.app_dir, 'settings.json')
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as settings_file:
                settings = json.loads(settings_file.read() or 'null') or {}
                self.hydroserver_url = settings.get('url')
                self.hydroserver_api_key = settings.get('apikey')
                self.hydroserver_username = settings.get('username')
                self.hydroserver_password = settings.get('password')
                self.workspace_name = settings.get('workspace')
                self.instance_name = settings.get('name')
                self.paused = settings.get('paused')

    def update_settings(
            self,
            hydroserver_url=None,
            instance_name=None,
            workspace_name=None,
            hydroserver_api_key=None,
            hydroserver_username=None,
            hydroserver_password=None,
            use_api_key=True,
            paused=None
    ):
        """Update settings file with new settings"""

        if use_api_key is True:
            api_key = hydroserver_api_key if hydroserver_api_key is not None else self.hydroserver_api_key
            username = None
            password = None
        else:
            api_key = None
            username = hydroserver_username if hydroserver_username is not None else self.hydroserver_username
            password = hydroserver_password if hydroserver_password is not None else self.hydroserver_password

        settings_path = os.path.join(self.app_dir, 'settings.json')
        with open(settings_path, 'w') as settings_file:
            settings_file.write(json.dumps({
                'url': hydroserver_url if hydroserver_url is not None else self.hydroserver_url,
                'name': instance_name if instance_name is not None else self.instance_name,
                'workspace': workspace_name if workspace_name is not None else self.workspace_name,
                'apikey': api_key,
                'username': username,
                'password': password,
                'paused': paused if paused is not None else self.paused
            }))
        self.get_settings()

    def confirm_settings(self):
        """Handle the user updating connection settings"""

        if not all([
            self.url_input.text(), self.workspace_input.text(), self.instance_input.text()
        ]) or (
            not (self.email_input.text() and self.password_input.text()) and not self.api_key_input.text()
        ):
            return self.show_message(
                title='Missing Required Fields',
                message='All fields are required to register the Streaming Data Loader app on HydroServer.'
            )

        self.update_settings(
            hydroserver_url=self.url_input.text(),
            instance_name=self.instance_input.text(),
            workspace_name=self.workspace_input.text(),
            hydroserver_api_key=self.api_key_input.text(),
            hydroserver_username=self.email_input.text(),
            hydroserver_password=self.password_input.text(),
            use_api_key=not self.auth_toggle_checkbox.isChecked(),
        )

        connection_message = self.connect_to_hydroserver()
        self.update_gui()

        if self.connected is False:
            return self.show_message(
                title='Connection Failed',
                message=connection_message
            )

        if self.scheduler:
            self.scheduler.terminate()

        self.scheduler = DataLoaderScheduler(
            hs_api=self.service,
            data_loader=connection_message
        )

        if self.paused is True:
            self.scheduler.pause()

        self.show_message(
            title='Streaming Data Loader Setup Complete',
            message='The Streaming Data Loader has been successfully registered and is now running.'
        )

        self.hide()

    @staticmethod
    def show_message(title, message):
        """Show a message window to the user"""

        message_box = QMessageBox()
        message_box.setWindowTitle(title)
        message_box.setText(message)
        message_box.exec_()

    def update_gui(self):
        """Update UI elements when settings/state changes"""

        if self.paused:
            pause_action_text = 'Resume'
            pause_action_icon = 'resume.png'
        else:
            pause_action_text = 'Pause'
            pause_action_icon = 'pause.png'

        if self.connected and not self.paused:
            status = 'Running'
            connection_icon = 'connected.png'
            data_sources_enabled = True
        elif self.connected and self.paused:
            status = 'Paused'
            connection_icon = 'connected.png'
            data_sources_enabled = True
        else:
            status = 'Not Connected'
            connection_icon = 'disconnected.png'
            data_sources_enabled = False

        self.status_action.setText(f'Status: {status}')

        connected_icon = QIcon(os.path.join(self.assets_path, connection_icon))
        connected_icon.setIsMask(True)
        self.connection_action.setIcon(connected_icon)
        self.dashboard_action.setEnabled(data_sources_enabled)

        self.pause_action.setText(pause_action_text)
        pause_icon = QIcon(os.path.join(self.assets_path, pause_action_icon))
        pause_icon.setIsMask(True)
        self.pause_action.setIcon(pause_icon)

        if self.isHidden():
            self.url_input.setText(self.hydroserver_url if self.hydroserver_url else 'https://www.hydroserver.org')
            self.instance_input.setText(self.instance_name if self.instance_name else '')
            self.workspace_input.setText(self.workspace_name if self.workspace_name else '')
            self.api_key_input.setText(self.hydroserver_api_key if self.hydroserver_api_key else '')
            self.email_input.setText(self.hydroserver_username if self.hydroserver_username else '')
            self.password_input.setText(self.hydroserver_password if self.hydroserver_password else '')
            self.auth_toggle_checkbox.setChecked(bool(self.email_input.text()))
            self.api_key_input_widget.setVisible(not bool(self.email_input.text()))
            self.basic_auth_input_widget.setVisible(bool(self.email_input.text()))


if __name__ == '__main__':

    hydroloader_logger = logging.getLogger('hydroloader')
    scheduler_logger = logging.getLogger('scheduler')

    stream_handler = logging.StreamHandler()
    hydroloader_logger.addHandler(stream_handler)
    scheduler_logger.addHandler(stream_handler)

    user_dir = user_data_dir('Streaming Data Loader', 'CIROH')

    if not os.path.exists(user_dir):
        os.makedirs(user_dir)

    log_path = os.path.join(user_dir, 'streaming_data_loader.log')

    log_handler = RotatingFileHandler(
        filename=log_path,
        mode='a',
        maxBytes=20 * 1024 * 1024,
        backupCount=3
    )
    hydroloader_logger.addHandler(log_handler)
    scheduler_logger.addHandler(log_handler)

    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,
        handlers=[
            log_handler, stream_handler
        ]
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = StreamingDataLoader()
    sys.exit(app.exec_())
