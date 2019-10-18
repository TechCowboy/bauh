import logging
from threading import Thread
from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QToolBar, QVBoxLayout

from bauh.api.abstract.cache import MemoryCache
from bauh.api.http import HttpClient
from bauh.view.qt import qt_utils
from bauh.view.qt.components import new_spacer
from bauh.view.qt.view_model import PackageView


class ScreenshotsDialog(QDialog):

    MAX_HEIGHT = 600
    MAX_WIDTH = 800

    def __init__(self, pkg: PackageView, http_client: HttpClient, icon_cache: MemoryCache, i18n: dict, screenshots: List[QPixmap], logger: logging.Logger):
        super(ScreenshotsDialog, self).__init__()
        self.setWindowTitle(str(pkg))
        self.screenshots = screenshots
        self.logger = logger
        self.loaded_imgs = []
        self.download_threads = []
        self.resize(1280, 720)
        self.i18n = i18n
        self.http_client = http_client

        # THERE ARE CRASHES WITH SOME RARE ICONS ( like insomnia ). IT CAN BE A QT BUG. IN THE MEANTIME, ONLY THE TYPE ICON WILL BE RENDERED
        #
        # icon_data = icon_cache.get(pkg.model.icon_url)
        #
        # if icon_data and icon_data.get('icon'):
        #     self.setWindowIcon(icon_data.get('icon'))
        # else:
        #     self.setWindowIcon(QIcon(pkg.model.get_type_icon_path()))
        self.setWindowIcon(QIcon(pkg.model.get_type_icon_path()))
        self.setLayout(QVBoxLayout())

        self.img = QLabel()
        self.layout().addWidget(self.img)

        self.bottom_bar = QToolBar()

        self.bt_back = QPushButton(self.i18n['screenshots.bt_back.label'].capitalize())
        self.bt_back.clicked.connect(self.back)
        self.ref_bt_back = self.bottom_bar.addWidget(self.bt_back)
        self.bottom_bar.addWidget(new_spacer(50))

        self.img_label = QLabel()
        self.img_label.setStyleSheet('QLabel { font-weight: bold; text-align: center }')
        self.bottom_bar.addWidget(self.img_label)
        self.bottom_bar.addWidget(new_spacer(50))

        self.bt_next = QPushButton(self.i18n['screenshots.bt_next.label'].capitalize())
        self.bt_next.clicked.connect(self.next)
        self.ref_bt_next = self.bottom_bar.addWidget(self.bt_next)

        self.layout().addWidget(self.bottom_bar)

        self.img_idx = 0

        for idx, s in enumerate(self.screenshots):
            t = Thread(target=self._download_img, args=(idx, s))
            t.start()

        self._load_img()

    def _load_img(self):
        if len(self.loaded_imgs) > self.img_idx:
            img = self.loaded_imgs[self.img_idx]

            if isinstance(img, QPixmap):
                self.img_label.setText('')
                self.img.setPixmap(img)
            else:
                self.img_label.setText(img)
                self.img.setPixmap(QPixmap())
        else:
            self.img.setPixmap(QPixmap())
            self.img_label.setText('...{}...'.format(self.i18n['screenshots,download.running']))

        if len(self.screenshots) == 1:
            self.ref_bt_back.setVisible(False)
            self.ref_bt_next.setVisible(False)
        else:
            self.ref_bt_back.setEnabled(self.img_idx != 0)
            self.ref_bt_next.setEnabled(self.img_idx != len(self.screenshots) - 1)

        self.adjustSize()
        qt_utils.centralize(self)

    def _download_img(self, idx: int, url: str):
        self.logger.info('Downloading image [{}] from {}'.format(idx, url))
        res = self.http_client.get(url)

        if res:
            if not res.content:
                self.logger.warning('Image [{}] from {} has no content'.format(idx, url))
                self.loaded_imgs.append(self.i18n['screenshots.download.no_content'])
                self._load_img()
            else:
                self.logger.info('Image [{}] successfully downloaded'.format(idx))
                pixmap = QPixmap()
                pixmap.loadFromData(res.content)

                if pixmap.size().height() > self.MAX_HEIGHT or pixmap.size().width() > self.MAX_WIDTH:
                    pixmap = pixmap.scaled(self.MAX_WIDTH, self.MAX_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                self.loaded_imgs.append(pixmap)

                if self.img_idx == idx:
                    self._load_img()
        else:
            self.logger.info("Could not retrieve image [{}] from {}".format(idx, url))
            self.loaded_imgs.append(self.i18n['screenshots.download.no_response'])
            self._load_img()

    def back(self):
        self.img_idx -= 1
        self._load_img()

    def next(self):
        self.img_idx += 1
        self._load_img()


