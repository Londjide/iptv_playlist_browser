# -*- coding: utf-8 -*-
"""
This class allows to display the main application window.
"""


from PyQt5.QtWidgets import QMainWindow, QMessageBox, QFileDialog
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt
from main_ui import Ui_MainWindow
from PyQt5.uic import loadUi
from playlist import Playlist
import subprocess
import psutil
from PyQt5 import QtCore, QtGui
from datetime import datetime
import configparser
import contextlib
import os
from OpenPreferences import OpenPreferences
from OpenLocalFile import OpenLocalFile
from OpenRemoteFile import OpenRemoteFile
from OpenXtream import OpenXtream
from GeneratePlaylist import GeneratePlaylist
import requests
import tools
from typing import Dict, Set
from datetime import datetime

MARGIN = 10
CONFIG_POSSIBLE_FALSE: Set = {"0", "", "n", "no", "false"}


class MainWindow(QMainWindow, Ui_MainWindow):
    config_file: str = "config.ini"
    main_title: str = "IPTV Playlist Browser"
    git_repo_url: str = "https://github.com/PhunkyBob/iptv_playlist_browser"
    latest_version_url = "https://raw.githubusercontent.com/PhunkyBob/iptv_playlist_browser/master/VERSION"
    pl: Playlist = None
    player_process = None
    current_categ_1: str = ""
    current_categ_2: str = ""
    current_categ_vod: str = ""
    current_categ_series: str = ""
    current_channels: Dict = {}
    current_channels_vod: Dict = {}
    current_channels_series: Dict = {}
    current_episodes: Dict = {}
    version: str = ""

    # Config
    config_remember: bool = True
    config_player: str = ""
    config_player_params: str = ""
    config_sep_1: str = ""
    config_sep_2: str = ""
    config_try_xtream_code: bool = True
    config_add_minutes: int = 0

    # Latest values
    latest_username: str = ""
    latest_password: str = ""
    latest_server: str = ""
    latest_local: str = ""
    latest_remote: str = ""

    def __init__(self, parent=None, version="unkwnown"):
        super().__init__(parent)
        loadUi(tools.resource_path("ui/main_ui.ui"), self)
        # self.setupUi(self)
        self.connect_signals_slots()
        self.pl = None
        self.lbl_wait.hide()
        self.version = version

        # Set default values
        self.set_default_values()

        # Read config
        self.read_config()

        # Alert if there is no player already set
        if not os.path.isfile(self.config_player):
            self.warning_player()

    def set_default_values(self) -> None:
        now = datetime.now()
        self.setWindowTitle(f"{self.main_title}")
        self.date_start.setDate(QtCore.QDate(now.year, now.month, now.day))
        self.time_start.setTime(QtCore.QTime(now.hour, (now.minute // 5) * 5))
        self.txt_duration.setText("80")
        self.chk_catchup.setEnabled(False)
        self.date_start.setEnabled(False)
        self.time_start.setEnabled(False)
        self.btn_watch.setEnabled(False)
        self.onlyInt = QtGui.QIntValidator()
        self.txt_duration.setValidator(self.onlyInt)

    def read_config(self) -> None:
        config = configparser.ConfigParser()
        if os.path.isfile(self.config_file):
            config.read(self.config_file, encoding="utf-8")
            if "PREFERENCES" in config and "remember_latest" in config["PREFERENCES"]:
                self.config_remember = config["PREFERENCES"]["remember_latest"].lower() not in CONFIG_POSSIBLE_FALSE
            if "PREFERENCES" in config and "player" in config["PREFERENCES"]:
                self.config_player = config["PREFERENCES"]["player"]
            if "PREFERENCES" in config and "player_params" in config["PREFERENCES"]:
                self.config_player_params = config["PREFERENCES"]["player_params"]
            if "PREFERENCES" in config and "playlist_group_separator" in config["PREFERENCES"]:
                self.config_sep_1 = config["PREFERENCES"]["playlist_group_separator"]
            if "PREFERENCES" in config and "playlist_categ_separator" in config["PREFERENCES"]:
                self.config_sep_2 = config["PREFERENCES"]["playlist_categ_separator"]
            if "PREFERENCES" in config and "try_xtream_code" in config["PREFERENCES"]:
                self.config_try_xtream_code = (
                    config["PREFERENCES"]["try_xtream_code"].lower() not in CONFIG_POSSIBLE_FALSE
                )
            if "PREFERENCES" in config and "catchup_add_minutes" in config["PREFERENCES"]:
                self.config_add_minutes = int(config["PREFERENCES"]["catchup_add_minutes"])
            if "XTREAM_CODE" in config and "username" in config["XTREAM_CODE"]:
                self.latest_username = config["XTREAM_CODE"]["username"]
            if "XTREAM_CODE" in config and "password" in config["XTREAM_CODE"]:
                self.latest_password = config["XTREAM_CODE"]["password"]
            if "XTREAM_CODE" in config and "server" in config["XTREAM_CODE"]:
                self.latest_server = config["XTREAM_CODE"]["server"]
            if "LOCAL" in config and "filepath" in config["LOCAL"]:
                self.latest_local = config["LOCAL"]["filepath"]
            if "REMOTE" in config and "filepath" in config["REMOTE"]:
                self.latest_remote = config["REMOTE"]["filepath"]
        self.update_menu_status()
        self.save_config()

    def resizeEvent(self, *args):
        """Resize and move all elements when window is resized."""
        QMainWindow.resizeEvent(self, *args)
        tab_width = int(self.width() - 2 * MARGIN)
        tab_height = int(self.height() - 140)
        self.tab_main.resize(tab_width, tab_height)
        list_width = int((tab_width - 4 * MARGIN) / 3)
        # Live
        list_height = tab_height - 140
        self.list_categ_1.resize(list_width, list_height)
        self.list_categ_2.resize(list_width, list_height)
        self.list_channels.resize(list_width, list_height)
        self.txt_filter_groups.resize(list_width - 110, 25)
        self.txt_filter_categories.resize(list_width - 110, 25)
        self.txt_filter_channels.resize(list_width - 110, 25)
        self.frm_catchup.resize(tab_width - 2 * MARGIN, self.frm_catchup.height())
        self.cmb_epg.resize(self.frm_catchup.width() - 410 - MARGIN, self.cmb_epg.height())
        self.list_categ_1.move(1 * MARGIN + 0 * list_width, 40)
        self.list_categ_2.move(2 * MARGIN + 1 * list_width, 40)
        self.list_channels.move(3 * MARGIN + 2 * list_width, 40)
        self.txt_filter_groups.move(self.list_categ_1.pos().x() + 110, MARGIN)
        self.txt_filter_categories.move(self.list_categ_2.pos().x() + 110, MARGIN)
        self.txt_filter_channels.move(self.list_channels.pos().x() + 110, MARGIN)

        self.frm_catchup.move(MARGIN, 40 + list_height + 2 * MARGIN)
        self.lbl_groups.move(self.list_categ_1.pos().x(), 15)
        self.lbl_categories.move(self.list_categ_2.pos().x(), 15)
        self.lbl_channels.move(self.list_channels.pos().x(), 15)

        # VOD
        list_height = tab_height - 90
        self.list_categ_vod.resize(list_width, list_height)
        self.list_channels_vod.resize(list_width, list_height)
        self.picture_vod.resize(list_width, list_height)
        self.txt_filter_groups_vod.resize(list_width - 110, 25)
        self.txt_filter_channels_vod.resize(list_width - 110, 25)
        self.list_categ_vod.move(1 * MARGIN + 0 * list_width, 40)
        self.list_channels_vod.move(2 * MARGIN + 1 * list_width, 40)
        self.picture_vod.move(3 * MARGIN + 2 * list_width, 40)
        self.txt_filter_groups_vod.move(self.list_categ_vod.pos().x() + 110, MARGIN)
        self.txt_filter_channels_vod.move(self.list_channels_vod.pos().x() + 110, MARGIN)
        self.lbl_groups_vod.move(self.list_categ_vod.pos().x(), 15)
        self.lbl_channels_vod.move(self.list_channels_vod.pos().x(), 15)

        # Series
        list_height = tab_height - 90
        self.list_categ_series.resize(list_width, list_height)
        self.list_channels_series.resize(list_width, list_height)
        self.list_episodes.resize(list_width, list_height)
        self.txt_filter_groups_series.resize(list_width - 110, 25)
        self.txt_filter_channels_series.resize(list_width - 110, 25)
        self.list_categ_series.move(1 * MARGIN + 0 * list_width, 40)
        self.list_channels_series.move(2 * MARGIN + 1 * list_width, 40)
        self.list_episodes.move(3 * MARGIN + 2 * list_width, 40)
        self.txt_filter_groups_series.move(self.list_categ_series.pos().x() + 110, MARGIN)
        self.txt_filter_channels_series.move(self.list_channels_series.pos().x() + 110, MARGIN)
        self.lbl_groups_series.move(self.list_categ_series.pos().x(), 15)
        self.lbl_channels_series.move(self.list_channels_series.pos().x(), 15)

        # Watch
        self.txt_url.resize(tab_width - self.btn_watch.width() - MARGIN, 25)
        self.txt_url.move(MARGIN, tab_height + 2 * MARGIN)
        self.btn_watch.move(self.width() - self.btn_watch.width() - MARGIN, tab_height + 2 * MARGIN)

    def connect_signals_slots(self):
        """Link elements signals to functions."""
        self.action_Exit.triggered.connect(self.close)
        self.action_Open_local_file.triggered.connect(self.open_local_file)
        self.action_Open_remote_file.triggered.connect(self.open_remote_file)
        self.action_api.triggered.connect(self.open_xtream)
        self.action_About.triggered.connect(self.about)
        self.action_Preferences.triggered.connect(self.preferences)
        self.action_Account_infos.triggered.connect(self.display_account_infos)
        self.action_Download_playlist_lite.triggered.connect(self.download_playlist_lite)
        self.action_Download_playlist_full.triggered.connect(self.download_playlist_full)
        self.action_Generate_playlist.triggered.connect(self.generate_playlist)
        self.btn_watch.clicked.connect(self.watch)
        self.txt_url.textChanged.connect(self.url_changed)
        self.tab_main.currentChanged.connect(self.tab_changed)

        # Live
        self.list_categ_1.itemSelectionChanged.connect(self.select_group)
        self.list_categ_2.itemSelectionChanged.connect(self.select_category)
        self.list_channels.itemSelectionChanged.connect(self.select_channel)
        self.list_channels.doubleClicked.connect(self.watch)
        self.txt_filter_groups.textChanged.connect(self.update_groups)
        self.txt_filter_categories.textChanged.connect(self.update_categories)
        self.txt_filter_channels.textChanged.connect(self.update_channels)
        self.chk_catchup.stateChanged.connect(self.change_catchup_settings)
        self.date_start.dateChanged.connect(self.change_catchup_settings)
        self.time_start.timeChanged.connect(self.change_catchup_settings)
        self.txt_duration.textChanged.connect(self.change_catchup_settings)
        self.cmb_epg.currentIndexChanged.connect(self.select_epg)

        # VOD
        self.list_categ_vod.itemSelectionChanged.connect(self.select_group_vod)
        self.list_channels_vod.itemSelectionChanged.connect(self.select_channel_vod)
        self.list_channels_vod.doubleClicked.connect(self.watch)
        self.txt_filter_groups_vod.textChanged.connect(self.update_groups_vod)
        self.txt_filter_channels_vod.textChanged.connect(self.update_channels_vod)

        # Series
        self.list_categ_series.itemSelectionChanged.connect(self.select_group_series)
        self.list_channels_series.itemSelectionChanged.connect(self.select_channel_series)
        self.list_episodes.itemSelectionChanged.connect(self.select_episode)
        self.list_episodes.doubleClicked.connect(self.watch)
        self.txt_filter_groups_series.textChanged.connect(self.update_groups_series)
        self.txt_filter_channels_series.textChanged.connect(self.update_channels_series)

    def preferences(self):
        """Open "preferences" dialog."""
        dialog = OpenPreferences(
            self,
            self.config_player,
            self.config_player_params,
            self.config_remember,
            self.config_try_xtream_code,
            self.config_sep_1,
            self.config_sep_2,
            self.config_add_minutes,
        )
        dialog.exec()
        if dialog.validated:
            # Dialog closed with "OK" --> save parameters
            self.config_player = dialog.player
            self.config_player_params = dialog.player_params
            self.config_remember = dialog.remember_latest
            self.config_try_xtream_code = dialog.try_xtream_code
            self.config_sep_1 = dialog.playlist_group_separator
            self.config_sep_2 = dialog.playlist_category_separator
            self.config_add_minutes = dialog.catchup_add_minutes
            self.save_config()

    def open_local_file(self):
        """Open "open local file" dialog."""
        dialog = OpenLocalFile(
            self,
            self.latest_local,
            self.config_remember,
            self.config_sep_1,
            self.config_sep_2,
        )
        dialog.exec()
        if dialog.remember and dialog.url:
            self.latest_local = dialog.url
            self.save_config()
        if dialog.url:
            self.open_file(
                filename=dialog.url,
                try_xtream=self.config_try_xtream_code,
                sep_lvl1=dialog.sep_lvl1,
                sep_lvl2=dialog.sep_lvl2,
            )

    def open_remote_file(self):
        """Open "open remote file" dialog."""
        dialog = OpenRemoteFile(self, self.latest_remote, self.config_remember)
        dialog.exec()
        if dialog.remember and dialog.url:
            self.latest_remote = dialog.url
            self.save_config()
        if dialog.url:
            self.open_file(
                filename=dialog.url,
                try_xtream=self.config_try_xtream_code,
                sep_lvl1=self.config_sep_1,
                sep_lvl2=self.config_sep_2,
            )

    def open_xtream(self):
        """Open "Xtream code" dialog."""
        dialog = OpenXtream(
            self,
            self.latest_username,
            self.latest_password,
            self.latest_server,
            self.config_remember,
        )
        dialog.exec()

        if dialog.username and dialog.password and dialog.server:
            self.latest_username = dialog.username
            self.latest_password = dialog.password
            self.latest_server = dialog.server
            self.update_menu_status()
            if dialog.remember:
                self.save_config()
        if dialog.username:
            self.open_file(
                server=dialog.server,
                username=dialog.username,
                password=dialog.password,
                sep_lvl1=self.config_sep_1,
                sep_lvl2=self.config_sep_2,
            )

    def open_file(
        self,
        server="",
        username="",
        password="",
        filename="",
        try_xtream=True,
        sep_lvl1="▼---",
        sep_lvl2="---●★",
    ):
        """Get the playlist from the file or the Xtream credentials."""
        self.show_loader()
        # Update title window.
        if filename:
            self.setWindowTitle(f"{self.main_title} - {filename}")
        if server:
            self.setWindowTitle(f"{self.main_title} - {username}@{server}")

        self.pl = Playlist(
            server=server,
            username=username,
            password=password,
            filename=filename,
            try_xtream=try_xtream,
            sep_lvl1=sep_lvl1,
            sep_lvl2=sep_lvl2,
        )
        # Reset current selections and content.
        self.current_categ_1 = ""
        self.current_categ_2 = ""
        self.current_channels = {}
        self.current_categ_vod = ""
        self.current_channels_vod = {}
        self.list_categ_1.setCurrentItem(None)
        self.list_categ_1.clear()
        self.list_categ_2.setCurrentItem(None)
        self.list_categ_2.clear()
        self.list_channels.setCurrentItem(None)
        self.list_channels.clear()
        self.list_categ_vod.setCurrentItem(None)
        self.list_categ_vod.clear()
        self.list_channels_vod.setCurrentItem(None)
        self.list_channels_vod.clear()
        self.action_Generate_playlist.setEnabled(True)
        self.update_groups()
        self.update_groups_vod()
        self.update_groups_series()
        if not self.pl.api_account:
            self.set_catchup_enabled(False)
        else:
            self.set_catchup_enabled(True)
        self.hide_loader()

    def set_catchup_enabled(self, enabled: bool):
        self.chk_catchup.setEnabled(enabled)
        self.date_start.setEnabled(enabled)
        self.time_start.setEnabled(enabled)

    def download_playlist(self, playlist_plus: bool = False):
        """Download playlist from xtream."""
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        if folder := QFileDialog.getExistingDirectory(
            self,
            "Download playlist in folder",
            "",
            options=options,
        ):
            self.show_loader("Downloading playlist...")
            filename = Playlist.download_m3u(
                self.latest_server, self.latest_username, self.latest_password, folder, playlist_plus
            )
            self.hide_loader()
            msgBox = QMessageBox()
            if filename:
                msgBox.setIcon(QMessageBox.Information)
                msgBox.setWindowIcon(self.windowIcon())
                msgBox.setText(f'"{filename}" downloaded successfully.')
                msgBox.setWindowTitle("Information")
            else:
                msgBox.setIcon(QMessageBox.Critical)
                msgBox.setWindowIcon(self.windowIcon())
                msgBox.setText("Can't download playlist from server.")
                msgBox.setWindowTitle("Error")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec()

    def download_playlist_lite(self):
        self.download_playlist()

    def download_playlist_full(self):
        self.download_playlist("m3u_full")

    def generate_playlist(self):
        """Open "Export playlist" dialog."""
        dialog = GeneratePlaylist(self)
        dialog.exec()
        if dialog.url:
            self.show_loader("Generating playlist...")
            self.pl.generate_m3u(
                output_file=dialog.url,
                export_live=dialog.chk_live.isChecked(),
                export_vod=dialog.chk_vod.isChecked(),
                export_series=dialog.chk_series.isChecked(),
            )
            self.hide_loader()
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setWindowIcon(self.windowIcon())
            msgBox.setText(f'"{dialog.url}" generated successfully.')
            msgBox.setWindowTitle("Information")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec()

    def display_account_infos(self) -> None:
        self.show_loader("Gathering infos...")
        infos = Playlist.get_api_infos(self.latest_server, self.latest_username, self.latest_password)
        infos = self.format_account_infos(infos)
        self.hide_loader()
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setWindowIcon(self.windowIcon())
        msgBox.setText(infos)
        msgBox.setWindowTitle("Information")
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec()

    def format_account_infos(self, infos: Dict) -> str:
        result = "User infos\n"
        if "user_info" in infos:
            for elem in ["username", "message", "status", "max_connections", "exp_date", "created_at"]:
                if elem in infos["user_info"]:
                    val = infos["user_info"][elem]
                    if elem in ["exp_date", "created_at"]:
                        val = datetime.fromtimestamp(int(val))
                    result += f"{elem}: {val}\n"
        result += "\nServer infos\n"
        if "server_info" in infos:
            for elem in ["url", "port", "https_port", "server_protocol", "rtmp_port", "timezone", "timestamp_now"]:
                if elem in infos["server_info"]:
                    val = infos["server_info"][elem]
                    if elem in ["timestamp_now"]:
                        val = datetime.fromtimestamp(int(val))
                    result += f"{elem}: {val}\n"
        return result

    def about(self):
        """Open "about" dialog."""
        # Check what is the latest version available in GitHub
        latest_msg = self.check_version()
        QMessageBox.about(
            self,
            "IPTV Playlist Browser",
            "<p>A simple app to browse your IPTV playlist.</p>"
            + f"<p>Version {self.version}{latest_msg}</p>"
            + f'<p><a href="{self.git_repo_url}">{self.git_repo_url}</a></p>',
        )

    def warning_player(self):
        """Open "warning" dialog when any player is specified."""
        QMessageBox.about(
            self,
            "IPTV Playlist Browser - WARNING",
            "<p>The application doesn't know how to play the video files. </p>"
            + '<p>Please go to "<i><b>Preferences...</b></i>" menu and set the path for your desired player. </p>',
        )

    def check_version(self):
        """Check what is the latest version on GitHub."""
        res = requests.get(self.latest_version_url)
        if res.status_code != 200:
            return ""
        latest_version = res.text.strip()
        return " (latest)" if latest_version == self.version else f" ({latest_version} available)"

    def tab_changed(self):
        self.txt_url.setText("")
        if self.tab_main.currentIndex() == 0 and self.list_channels.currentItem():
            self.select_channel()
        if self.tab_main.currentIndex() == 1 and self.list_channels_vod.currentItem():
            self.select_channel_vod()
        if self.tab_main.currentIndex() == 2 and self.list_channels_series.currentItem():
            self.select_episode()

    def update_groups(self):
        """Update the list "groups" with available / filtered elements."""
        # Live channels
        fltr = self.txt_filter_groups.text()
        self.list_categ_1.setCurrentItem(None)
        self.list_categ_1.clear()
        for categ_1 in self.pl.channels:
            if fltr.lower() in categ_1.lower() and len(self.pl.channels[categ_1]) > 0:
                self.list_categ_1.addItem(categ_1)
        self.lbl_groups.setText(f"Groups ({self.list_categ_1.count()})")

    def update_groups_vod(self):
        # VOD
        fltr = self.txt_filter_groups_vod.text()
        self.list_categ_vod.setCurrentItem(None)
        self.list_categ_vod.clear()
        for categ_1 in self.pl.vod:
            if fltr.lower() in categ_1.lower() and len(self.pl.vod[categ_1]) > 0:
                self.list_categ_vod.addItem(categ_1)
        self.update_channels_vod()
        self.lbl_groups_vod.setText(f"Groups ({self.list_categ_vod.count()})")

    def update_groups_series(self):
        # Series
        fltr = self.txt_filter_groups_series.text()
        self.list_categ_series.setCurrentItem(None)
        self.list_categ_series.clear()
        for categ_1 in self.pl.series:
            if fltr.lower() in categ_1.lower() and len(self.pl.series[categ_1]) > 0:
                self.list_categ_series.addItem(categ_1)
        self.update_channels_series()
        self.lbl_groups_series.setText(f"Groups ({self.list_categ_series.count()})")

    def update_categories(self):
        """Update the list "categories" with available / filtered elements."""
        fltr = self.txt_filter_categories.text()
        self.list_categ_2.setCurrentItem(None)
        self.list_categ_2.clear()
        if self.current_categ_1:
            for categ_2 in self.pl.channels[self.current_categ_1]:
                if fltr.lower() in categ_2.lower() and len(self.pl.channels[self.current_categ_1][categ_2]) > 0:
                    self.list_categ_2.addItem(categ_2)
        self.lbl_categories.setText(f"Categories ({self.list_categ_2.count()})")

    def update_channels(self):
        """Update the list "channels" with available / filtered elements."""
        fltr = self.txt_filter_channels.text()
        self.list_channels.setCurrentItem(None)
        self.list_channels.clear()
        self.current_channels = {}

        if self.current_categ_2:
            for channel in self.pl.channels[self.current_categ_1][self.current_categ_2]:
                if fltr.lower() in channel.lower():
                    self.list_channels.addItem(channel)
                    self.current_channels[channel] = self.pl.channels[self.current_categ_1][self.current_categ_2][
                        channel
                    ]
        else:
            # If no category is selected, display all available channels.
            for i in range(self.list_categ_2.count()):
                categ_2 = self.list_categ_2.item(i).text()
                for channel in self.pl.channels[self.current_categ_1][categ_2]:
                    if fltr.lower() in channel.lower():
                        self.list_channels.addItem(channel)
                        self.current_channels[channel] = self.pl.channels[self.current_categ_1][categ_2][channel]
        self.lbl_channels.setText(f"Channels ({self.list_channels.count()})")

    def select_group(self):
        """When a group is selected."""
        self.show_loader()
        self.current_categ_1 = ""
        if self.list_categ_1.currentItem():
            self.current_categ_1 = self.list_categ_1.currentItem().text()
        self.current_categ_2 = ""
        self.list_categ_2.setCurrentItem(None)
        self.list_categ_2.clear()
        self.update_categories()
        self.update_channels()
        self.hide_loader()

    def select_category(self):
        """When a category is selected."""
        self.show_loader()
        self.list_channels.setCurrentItem(None)
        self.list_channels.clear()
        self.txt_url.setText("")
        if self.list_categ_2.currentItem():
            self.current_categ_2 = self.list_categ_2.currentItem().text()
            # print(self.current_categ_2)
            self.update_channels()
        self.hide_loader()

    def block_epg_enable(self, status):
        self.chk_catchup.setEnabled(status)
        self.date_start.setEnabled(status)
        self.time_start.setEnabled(status)
        self.txt_duration.setEnabled(status)
        self.cmb_epg.setEnabled(status)

    def select_channel(self):
        """When a channel is selected."""
        self.show_loader()
        if self.list_channels.currentItem():
            channel = self.list_channels.currentItem().text()
            url = self.current_channels[channel]
            # Enable / disable catchup
            self.block_epg_enable(False)
            self.lbl_catchup.setText("No catchup available")
            if url in self.pl.channels_details and self.pl.channels_details[url]["tv_archive"]:
                self.block_epg_enable(True)
                self.lbl_catchup.setText("Catchup available")
                if self.pl.channels_details[url]["stream_id"]:
                    self.update_epg(self.pl.channels_details[url]["stream_id"])
                else:
                    self.cmb_epg.clear()
            else:
                self.cmb_epg.clear()

            self.change_catchup_settings()
        self.hide_loader()

    def change_catchup_settings(self):
        """Decide what URL should be displayed between live and catchup."""
        show_catchup = self.chk_catchup.isChecked()
        self.date_start.setVisible(show_catchup)
        self.time_start.setVisible(show_catchup)
        self.txt_duration.setVisible(show_catchup)
        self.cmb_epg.setVisible(show_catchup)

        if self.list_channels.currentItem():
            channel = self.list_channels.currentItem().text()
            url = self.current_channels[channel]
            if (
                self.chk_catchup.isChecked()
                and self.chk_catchup.isEnabled()
                and self.pl.channels_details[url]["stream_id"]
            ):
                stream = self.pl.channels_details[url]["stream_id"]
                server = self.pl.api_account["server_info"]["url"]
                protocol = self.pl.api_account["server_info"]["server_protocol"]
                port = self.pl.api_account["server_info"]["port"]
                username = self.pl.api_account["user_info"]["username"]
                password = self.pl.api_account["user_info"]["password"]
                date = self.date_start.text()
                time = self.time_start.text().replace(":", "-")
                duration = self.txt_duration.text()
                url = f"{protocol}://{server}:{port}/streaming/timeshift.php?username={username}&password={password}&stream={stream}&start={date}:{time}&duration={duration}"
            self.txt_url.setText(url)

    def update_epg(self, stream):
        """Update the EPG for current channel and add elements in the list."""
        self.pl.update_epg(stream)
        self.cmb_epg.clear()
        if stream in self.pl.channels_epg:
            self.cmb_epg.addItem("...")
            for elem in reversed(sorted(self.pl.channels_epg[stream].keys())):
                self.cmb_epg.addItem(elem, self.pl.channels_epg[stream][elem])

    def select_epg(self):
        """When user selects a program in EPG, update the catchup settings."""
        if item := self.cmb_epg.currentData():
            self.date_start.setDate(QtCore.QDate.fromString(item["start_date"], QtCore.Qt.ISODate))
            self.time_start.setTime(QtCore.QTime.fromString(item["start_time"]))
            self.txt_duration.setText(str(item["duration"] + self.config_add_minutes))
            self.change_catchup_settings()

    def select_group_vod(self):
        """When a group is selected."""
        self.show_loader()
        self.list_channels_vod.setCurrentItem(None)
        self.list_channels_vod.clear()
        self.current_categ_vod = ""
        self.txt_url.setText("")
        self.picture_vod.clear()
        if self.list_categ_vod.currentItem():
            self.current_categ_vod = self.list_categ_vod.currentItem().text()
            # print(self.current_categ_2)
            self.update_channels_vod()
        self.hide_loader()

    def update_channels_vod(self):
        """Update the list "channels" with available / filtered elements."""
        fltr = self.txt_filter_channels_vod.text()
        self.list_channels_vod.setCurrentItem(None)
        self.list_channels_vod.clear()
        self.current_channels_vod = {}
        self.picture_vod.clear()
        self.txt_url.setText("")
        if self.current_categ_vod:
            for channel in self.pl.vod[self.current_categ_vod]["OTHERS"]:
                if fltr.lower() in channel.lower():
                    self.list_channels_vod.addItem(channel)
                    self.current_channels_vod[channel] = self.pl.vod[self.current_categ_vod]["OTHERS"][channel]
        else:
            # If no category is selected, display all available channels.
            for i in range(self.list_categ_vod.count()):
                categ_vod = self.list_categ_vod.item(i).text()
                for channel in self.pl.vod[categ_vod]["OTHERS"]:
                    if fltr.lower() in channel.lower():
                        self.list_channels_vod.addItem(channel)
                        self.current_channels_vod[channel] = self.pl.vod[categ_vod]["OTHERS"][channel]
        self.lbl_channels_vod.setText(f"Videos ({self.list_channels_vod.count()})")

    def select_channel_vod(self):
        """When a channel is selected."""
        self.show_loader()
        if self.list_channels_vod.currentItem():
            channel = self.list_channels_vod.currentItem().text()
            url = self.current_channels_vod[channel]
            self.txt_url.setText(url)

            url_image = self.pl.vod_details[url]["stream_icon"]
            image = QImage()
            image.loadFromData(requests.get(url_image).content)
            self.picture_vod.setPixmap(
                QPixmap(image).scaled(
                    self.picture_vod.width(),
                    self.picture_vod.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        self.hide_loader()

    def select_group_series(self):
        """When a group is selected."""
        self.show_loader()
        self.list_channels_series.setCurrentItem(None)
        self.list_channels_series.clear()
        self.current_categ_series = ""
        if self.list_categ_series.currentItem():
            self.current_categ_series = self.list_categ_series.currentItem().text()
            # print(self.current_categ_2)
            self.update_channels_series()
        self.hide_loader()

    def update_channels_series(self):
        """Update the list "channels" with available / filtered elements."""
        fltr = self.txt_filter_channels_series.text()
        self.list_channels_series.setCurrentItem(None)
        self.list_channels_series.clear()
        self.current_channels_series = {}
        self.txt_url.setText("")
        if self.current_categ_series:
            for channel in self.pl.series[self.current_categ_series]["OTHERS"]:
                if fltr.lower() in channel.lower():
                    self.list_channels_series.addItem(channel)
                    self.current_channels_series[channel] = self.pl.series[self.current_categ_series]["OTHERS"][
                        channel
                    ]
        else:
            # If no category is selected, display all available channels.
            for i in range(self.list_categ_series.count()):
                categ_series = self.list_categ_series.item(i).text()
                for channel in self.pl.series[categ_series]["OTHERS"]:
                    if fltr.lower() in channel.lower():
                        self.list_channels_series.addItem(channel)
                        self.current_channels_series[channel] = self.pl.series[categ_series]["OTHERS"][channel]
        self.list_episodes.setCurrentItem(None)
        self.list_episodes.clear()
        self.lbl_channels_series.setText(f"Videos ({self.list_channels_series.count()})")

    def select_channel_series(self):
        """When a channel is selected."""
        self.show_loader()
        self.txt_url.setText("")
        if not self.list_channels_series.currentItem():
            self.hide_loader()
            return
        channel = self.list_channels_series.currentItem().text()
        series_id = self.current_channels_series[channel]
        self.current_episodes = self.pl.get_series(series_id)
        self.list_episodes.setCurrentItem(None)
        self.list_episodes.clear()
        for e in self.current_episodes:
            self.list_episodes.addItem(e)
        self.hide_loader()

    def select_episode(self):
        """When an episode is selected."""
        self.show_loader()
        if self.list_episodes.currentItem():
            ep = self.list_episodes.currentItem().text()
            url = self.current_episodes[ep]
            self.txt_url.setText(url)
        self.hide_loader()

    def watch(self):
        """ "Launch player with correct parameters."""
        url = self.txt_url.text()
        if self.player_process:
            # Kill the previous process because we don't want more than 1 player
            with contextlib.suppress(Exception):
                process = psutil.Process(self.player_process.pid)
                for proc in process.children(recursive=True):
                    with contextlib.suppress(Exception):
                        proc.kill()
            self.player_process = None
        # Create a new process in a separated thread
        self.player_process = subprocess.Popen(
            [self.config_player, url.replace("&", "^&"), self.config_player_params],
            shell=True,
        )

    def show_loader(self, message: str = "LOADING..."):
        """Display the loader."""
        self.lbl_wait.setText(message)
        self.lbl_wait.show()
        self.lbl_wait.repaint()

    def hide_loader(self):
        """Hide the loader."""
        self.lbl_wait.hide()
        self.lbl_wait.repaint()

    def save_config(self):
        """Save the current parameters to a config file."""
        config = configparser.ConfigParser()
        config["PREFERENCES"] = {}
        config["PREFERENCES"]["remember_latest"] = str(self.config_remember)
        config["PREFERENCES"]["player"] = self.config_player
        config["PREFERENCES"]["player_params"] = self.config_player_params
        config["PREFERENCES"]["try_xtream_code"] = str(self.config_try_xtream_code)
        config["PREFERENCES"]["playlist_group_separator"] = self.config_sep_1
        config["PREFERENCES"]["playlist_categ_separator"] = self.config_sep_2
        config["PREFERENCES"]["catchup_add_minutes"] = str(self.config_add_minutes)

        config["XTREAM_CODE"] = {}
        config["XTREAM_CODE"]["username"] = self.latest_username
        config["XTREAM_CODE"]["password"] = self.latest_password
        config["XTREAM_CODE"]["server"] = self.latest_server

        config["LOCAL"] = {}
        config["LOCAL"]["filepath"] = self.latest_local
        config["REMOTE"] = {}
        config["REMOTE"]["filepath"] = self.latest_remote

        with open(self.config_file, "w", encoding="utf-8") as configfile:
            config.write(configfile)

    def url_changed(self):
        """When the URL is changed, enable / disable the "Watch" button."""
        if self.txt_url.text():
            self.btn_watch.setEnabled(True)
        else:
            self.btn_watch.setEnabled(False)

    def update_menu_status(self):
        if self.latest_server and self.latest_username and self.latest_password:
            self.menuXtream.setEnabled(True)
        else:
            self.menuXtream.setEnabled(False)
