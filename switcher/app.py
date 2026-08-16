from __future__ import annotations

import signal
import sys
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    Property,
    QPoint,
    QPropertyAnimation,
    QProcess,
    QRect,
    QRectF,
    QSize,
    QTimer,
    Qt,
    QUrl,
    Signal,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import (
    QAction,
    QColor,
    QCursor,
    QDesktopServices,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QKeySequenceEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSystemTrayIcon,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .config import Config, Hotkeys, ModeColors, Profile
from .devices import (
    Device,
    list_inputs,
    list_monitors,
    list_outputs,
    set_default_audio,
    set_primary_monitor,
)
from .startup import set_autostart
from .hotkeys import HotkeyManager


def make_icon(glyph: str = "S") -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#3b82f6"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(3, 3, 58, 58, 15, 15)
    painter.setPen(QColor("white"))
    font = painter.font()
    font.setPixelSize(32)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, glyph)
    painter.end()
    return QIcon(pixmap)


def make_mode_icon(mode: str) -> QIcon:
    """Render professional SVG controls without relying on emoji fonts."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    asset_dir = Path(__file__).resolve().parent / "assets"
    if mode == "game":
        QSvgRenderer(str(asset_dir / "monitor.svg")).render(
            painter, QRectF(4, 4, 56, 56)
        )
    else:
        QSvgRenderer(str(asset_dir / "steering-wheel.svg")).render(
            painter, QRectF(4, 4, 56, 56)
        )
    painter.end()
    return QIcon(pixmap)


class SlidingHighlight(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._color = QColor("#1677D2")

    def get_color(self) -> QColor:
        return self._color

    def set_color(self, color: QColor) -> None:
        self._color = QColor(color)
        self.update()

    color = Property(QColor, get_color, set_color)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawRoundedRect(card, 10, 10)


class SlidingSwitcher(QFrame):
    """Two-position switch whose highlight slides between square buttons."""

    choose = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("switcherTrack")
        self.setFixedSize(260, 120)
        self._active = "game"

        self.highlight = SlidingHighlight(self)
        self.highlight.setObjectName("switcherHighlight")
        self.highlight.setGeometry(6, 6, 120, 108)

        self.game = QToolButton(self)
        self.racing = QToolButton(self)
        for button, mode, label, tooltip in (
            (self.game, "game", "Desktop", "Desktop setup"),
            (self.racing, "racing", "Sim racing", "Sim racing setup"),
        ):
            button.setObjectName("switcherChoice")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setIcon(make_mode_icon(mode))
            button.setIconSize(QSize(42, 42))
            button.setText(label)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            button.setToolTip(tooltip)
        self.game.setGeometry(6, 6, 120, 108)
        self.racing.setGeometry(134, 6, 120, 108)
        self.game.clicked.connect(lambda: self.select("game"))
        self.racing.clicked.connect(lambda: self.select("racing"))

        self.animation = QPropertyAnimation(self.highlight, b"geometry", self)
        self.animation.setDuration(220)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.color_animation = QPropertyAnimation(self.highlight, b"color", self)
        self.color_animation.setDuration(220)
        self.color_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.colors = {"game": QColor("#1677D2"), "racing": QColor("#E58A3A")}
        self._pending_choice: str | None = None
        self.animation.finished.connect(self._finish_selection)

    def _finish_selection(self) -> None:
        if self._pending_choice is not None:
            choice = self._pending_choice
            self._pending_choice = None
            self.choose.emit(choice)

    def select(self, name: str, *, emit: bool = True) -> None:
        target_x = 6 if name == "game" else 134
        self.animation.stop()
        self.color_animation.stop()
        self.animation.setStartValue(self.highlight.geometry())
        self.animation.setEndValue(QRect(target_x, 6, 120, 108))
        self.color_animation.setStartValue(self.highlight.get_color())
        self.color_animation.setEndValue(self.colors[name])
        self.animation.start()
        self.color_animation.start()
        self._active = name
        if emit:
            self._pending_choice = name

    def set_active(self, name: str) -> None:
        if name in ("game", "racing"):
            self.select(name, emit=False)

    def set_colors(self, game: str, racing: str) -> None:
        self.colors = {"game": QColor(game), "racing": QColor(racing)}
        self.highlight.set_color(self.colors[self._active])


class Flyout(QFrame):
    choose = Signal(str)
    settings_requested = Signal()

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setObjectName("flyout")
        self._backdrop = QPixmap()
        self._backdrop_padding = 28
        self._popup_animation = QParallelAnimationGroup(self)
        self._closing = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel("SetupSwitcher")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch(1)
        settings = QPushButton()
        settings.setObjectName("settingsButton")
        settings.setIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "settings.svg")))
        settings.setIconSize(QSize(17, 17))
        settings.setToolTip("Settings")
        settings.clicked.connect(self.settings_requested)
        header.addWidget(settings)
        layout.addLayout(header)

        self.switcher = SlidingSwitcher()
        self.switcher.choose.connect(self.choose)
        layout.addWidget(self.switcher, 0, Qt.AlignmentFlag.AlignHCenter)

        self.status = QLabel("Ready")
        self.status.setObjectName("status")
        self.status.hide()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if self.isVisible() and not self._closing:
            QTimer.singleShot(0, self.animate_close)

    def _capture_backdrop(self, screen) -> None:
        padding = self._backdrop_padding
        source = screen.grabWindow(
            0,
            self.x() - padding,
            self.y() - padding,
            self.width() + padding * 2,
            self.height() + padding * 2,
        )
        if source.isNull():
            self._backdrop = QPixmap()
            return
        scene = QGraphicsScene()
        scene.setSceneRect(QRectF(source.rect()))
        item = QGraphicsPixmapItem(source)
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(22)
        blur.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
        item.setGraphicsEffect(blur)
        scene.addItem(item)
        result = QPixmap(source.size())
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        scene.render(painter, QRectF(result.rect()), QRectF(source.rect()))
        painter.end()
        self._backdrop = result

    def paintEvent(self, event) -> None:
        # Qt stylesheets do not reliably paint a translucent top-level QFrame on
        # Windows 11, so draw the flyout surface explicitly.
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), 11, 11)
        painter.setClipPath(clip)
        if not self._backdrop.isNull():
            painter.drawPixmap(-self._backdrop_padding, -self._backdrop_padding, self._backdrop)
        painter.fillPath(clip, QColor(27, 28, 32, 205))
        painter.setClipping(False)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(255, 255, 255, 70))
        painter.drawRoundedRect(
            QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 11, 11
        )
        painter.end()

    def popup_at(self, point: QPoint) -> None:
        self.adjustSize()
        screen = QApplication.screenAt(point) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        margin = 16
        x = area.right() - self.width() - margin + 1
        y = area.bottom() - self.height() - margin + 1
        target = QPoint(x, y)
        start = QPoint(x, area.bottom() + 1)
        self.move(target)
        self._capture_backdrop(screen)
        self.setWindowOpacity(0.0)
        self._closing = False
        self.show()
        self.move(start)
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self._popup_animation.stop()
        self._popup_animation = QParallelAnimationGroup(self)
        position = QPropertyAnimation(self, b"pos", self._popup_animation)
        position.setDuration(280)
        position.setStartValue(start)
        position.setEndValue(target)
        position.setEasingCurve(QEasingCurve.Type.OutCubic)
        opacity = QPropertyAnimation(self, b"windowOpacity", self._popup_animation)
        opacity.setDuration(160)
        opacity.setStartValue(0.0)
        opacity.setEndValue(1.0)
        opacity.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._popup_animation.addAnimation(position)
        self._popup_animation.addAnimation(opacity)
        self._popup_animation.start()

    def animate_close(self) -> None:
        if not self.isVisible() or self._closing:
            return
        self._closing = True
        screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
        end = QPoint(self.x(), screen.availableGeometry().bottom() + 1)
        self._popup_animation.stop()
        self._popup_animation = QParallelAnimationGroup(self)
        position = QPropertyAnimation(self, b"pos", self._popup_animation)
        position.setDuration(230)
        position.setStartValue(self.pos())
        position.setEndValue(end)
        position.setEasingCurve(QEasingCurve.Type.InCubic)
        opacity = QPropertyAnimation(self, b"windowOpacity", self._popup_animation)
        opacity.setDuration(190)
        opacity.setStartValue(self.windowOpacity())
        opacity.setEndValue(0.0)
        opacity.setEasingCurve(QEasingCurve.Type.InCubic)
        self._popup_animation.addAnimation(position)
        self._popup_animation.addAnimation(opacity)

        def finish() -> None:
            self.hide()
            self.setWindowOpacity(1.0)
            self._closing = False

        self._popup_animation.finished.connect(finish)
        self._popup_animation.start()


class ProfileEditor(QWidget):
    def __init__(
        self,
        monitors: list[Device],
        outputs: list[Device],
        inputs: list[Device],
        color: str,
    ):
        super().__init__()
        form = QFormLayout(self)
        self.monitor = QComboBox()
        self.output = QComboBox()
        self.input = QComboBox()
        self._fill(self.monitor, monitors)
        self._fill(self.output, outputs)
        self._fill(self.input, inputs)
        form.addRow("Primary monitor", self.monitor)
        form.addRow("Speakers / headphones", self.output)
        form.addRow("Microphone", self.input)
        self.color = ColorButton(color)
        form.addRow("Mode color", self.color)

    @staticmethod
    def _fill(combo: QComboBox, devices: list[Device]) -> None:
        combo.addItem("— Select a device —", "")
        for device in devices:
            combo.addItem(device.name, device.id)

    def set_profile(self, profile: Profile) -> None:
        for combo, value in (
            (self.monitor, profile.monitor),
            (self.output, profile.output),
            (self.input, profile.input),
        ):
            index = combo.findData(value)
            if index < 0 and value:
                combo.addItem(f"Saved device ({value})", value)
                index = combo.count() - 1
            combo.setCurrentIndex(max(0, index))

    def profile(self) -> Profile:
        return Profile(
            monitor=self.monitor.currentData(),
            output=self.output.currentData(),
            input=self.input.currentData(),
        )


class ColorButton(QPushButton):
    def __init__(self, color: str) -> None:
        super().__init__()
        self._color = QColor(color)
        self.setMinimumHeight(32)
        self.clicked.connect(self.choose_color)
        self._refresh()

    def choose_color(self) -> None:
        selected = QColorDialog.getColor(self._color, self, "Choose mode color")
        if selected.isValid():
            self._color = selected
            self._refresh()

    def color_name(self) -> str:
        return self._color.name().upper()

    def _refresh(self) -> None:
        foreground = "#111111" if self._color.lightness() > 150 else "#FFFFFF"
        self.setText(self.color_name())
        self.setStyleSheet(
            f"background: {self.color_name()}; color: {foreground}; "
            "border: 1px solid rgba(255,255,255,45); border-radius: 6px;"
        )


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Switcher settings")
        self.setMinimumWidth(520)
        root = QVBoxLayout(self)
        explanation = QLabel(
            "Assign devices for both setups. Set Discord input and output to "
            "Default so it follows the Windows devices."
        )
        explanation.setWordWrap(True)
        root.addWidget(explanation)
        errors: list[str] = []
        try:
            monitors = list_monitors()
        except Exception as error:
            monitors = []
            errors.append(f"displays: {error}")
        try:
            outputs = list_outputs()
            inputs = list_inputs()
        except Exception as error:
            outputs, inputs = [], []
            errors.append(f"audio: {error}")
        if errors:
            warning = QLabel("Could not refresh " + "; ".join(errors))
            warning.setWordWrap(True)
            root.addWidget(warning)
        tabs = QTabWidget()
        self.tabs = tabs
        self.game = ProfileEditor(monitors, outputs, inputs, config.colors.game)
        self.racing = ProfileEditor(monitors, outputs, inputs, config.colors.racing)
        self.game.set_profile(config.game)
        self.racing.set_profile(config.racing)
        tabs.addTab(self.game, "PC")
        tabs.addTab(self.racing, "Sim racing")
        hotkeys_page = QWidget()
        hotkeys_form = QFormLayout(hotkeys_page)
        self.panel_hotkey = QKeySequenceEdit(QKeySequence(config.hotkeys.panel))
        self.panel_hotkey.setMaximumSequenceLength(1)
        hotkeys_form.addRow("Open panel at cursor", self.panel_hotkey)
        hint = QLabel("Supported keys: A-Z, 0-9 and F1-F24 with Ctrl, Alt, Shift or Win.")
        hint.setWordWrap(True)
        hotkeys_form.addRow(hint)
        tabs.addTab(hotkeys_page, "Hotkeys")
        root.addWidget(tabs)
        self.autostart = QCheckBox("Start with Windows")
        self.autostart.setChecked(config.autostart)
        root.addWidget(self.autostart)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        restart = buttons.addButton("Restart app", QDialogButtonBox.ButtonRole.ActionRole)
        restart.clicked.connect(lambda: self.done(2))
        github = buttons.addButton("", QDialogButtonBox.ButtonRole.HelpRole)
        github.setIcon(QIcon(str(Path(__file__).resolve().parent / "assets" / "github.svg")))
        github.setIconSize(QSize(18, 18))
        github.setFixedSize(30, 30)
        github.setToolTip("github.com/skvoch")
        github.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/skvoch"))
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)


class SwitcherApp:
    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.config = Config.load()
        if self.config.autostart:
            try:
                set_autostart(True)
            except OSError:
                pass
        self.flyout = Flyout()
        self.flyout.switcher.set_colors(self.config.colors.game, self.config.colors.racing)
        self.flyout.choose.connect(self.apply_profile)
        self.flyout.settings_requested.connect(self.show_settings)
        self.tray = QSystemTrayIcon(make_icon(), app)
        self.tray.setToolTip("Setup Switcher")
        menu = QMenu()
        settings_action = QAction("Settings", menu)
        settings_action.triggered.connect(self.show_settings)
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(app.quit)
        menu.addAction(settings_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()
        self.hotkeys = HotkeyManager(
            {
                "panel": self.toggle_flyout,
            }
        )
        app.installNativeEventFilter(self.hotkeys)
        app.aboutToQuit.connect(self.hotkeys.unregister_all)
        self.configure_hotkeys(show_warning=True)
        self.flyout.switcher.set_active(self.config.last_profile or "game")
        if not self.config.game.monitor or not self.config.racing.monitor:
            self.show_settings()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            # tray.geometry() is often empty or points at the overflow window on
            # Windows 11. The cursor is the reliable anchor for both locations.
            self.toggle_flyout()

    def toggle_flyout(self) -> None:
        if self.flyout.isVisible():
            self.flyout.animate_close()
        else:
            self.flyout.popup_at(QCursor.pos())

    def configure_hotkeys(self, *, show_warning: bool) -> None:
        failures = self.hotkeys.configure(
            {
                "panel": self.config.hotkeys.panel,
            }
        )
        if failures and show_warning:
            QMessageBox.warning(None, "Hotkeys", "\n".join(failures))

    def show_settings(self) -> None:
        self.flyout.animate_close()
        dialog = SettingsDialog(self.config)
        result = dialog.exec()
        if result == 2:
            self.restart_application()
            return
        if result != QDialog.DialogCode.Accepted:
            return
        self.config.game = dialog.game.profile()
        self.config.racing = dialog.racing.profile()
        self.config.hotkeys = Hotkeys(
            panel=dialog.panel_hotkey.keySequence().toString(QKeySequence.SequenceFormat.PortableText),
        )
        self.config.colors = ModeColors(
            game=dialog.game.color.color_name(),
            racing=dialog.racing.color.color_name(),
        )
        self.flyout.switcher.set_colors(self.config.colors.game, self.config.colors.racing)
        self.config.autostart = dialog.autostart.isChecked()
        self.config.save()
        self.configure_hotkeys(show_warning=True)
        try:
            set_autostart(self.config.autostart)
        except OSError as error:
            QMessageBox.warning(None, "Startup", str(error))

    def restart_application(self) -> None:
        self.hotkeys.unregister_all()
        self.tray.hide()
        if sys.platform == "win32" and getattr(self.app, "instance_mutex", None):
            import ctypes

            ctypes.windll.kernel32.CloseHandle(self.app.instance_mutex)
            self.app.instance_mutex = None
        launcher = str(Path(__file__).resolve().parent.parent / "run_switcher.py")
        if not QProcess.startDetached(sys.executable, [launcher]):
            QMessageBox.critical(None, "Restart", "Could not restart Switcher")
            return
        self.app.quit()

    def apply_profile(self, name: str) -> None:
        profile = getattr(self.config, name)
        if not profile.monitor or not profile.output or not profile.input:
            self.flyout.switcher.set_active(self.config.last_profile or "game")
            self.show_settings()
            return
        self.flyout.status.setText("Switching…")
        QApplication.processEvents()
        try:
            set_primary_monitor(profile.monitor)
            set_default_audio(profile.output)
            set_default_audio(profile.input)
        except Exception as error:
            self.flyout.switcher.set_active(self.config.last_profile or "game")
            self.flyout.status.setText("Error")
            QMessageBox.critical(None, "Could not switch setup", str(error))
            return
        label = "Desktop" if name == "game" else "Sim racing"
        self.config.last_profile = name
        self.config.save()
        self.flyout.switcher.set_active(name)
        self.flyout.status.setText(f"Active: {label}")
        self.flyout.animate_close()


STYLE = """
QWidget { font-family: 'Segoe UI'; font-size: 14px; }
QFrame#flyout { background: transparent; border: none; }
QLabel { color: #f5f5f5; }
QLabel#title { font-size: 16px; font-weight: 600; padding-bottom: 6px; }
QLabel#status { color: #b7b7b7; font-size: 12px; }
QFrame#switcherTrack { background: #292a2d; border: 1px solid rgba(255, 255, 255, 24); border-radius: 13px; }
QFrame#switcherHighlight { background: transparent; border: none; }
QToolButton#switcherChoice { color: #eeeeee; background: transparent; border: none; border-radius: 10px; font-size: 12px; font-weight: 500; padding-top: 8px; }
QToolButton#switcherChoice:hover { background: rgba(255, 255, 255, 14); }
QToolButton#switcherChoice:pressed { background: rgba(255, 255, 255, 25); }
QPushButton#settingsButton { color: white; background: transparent; border: none; border-radius: 6px; min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px; }
QPushButton#settingsButton:hover { background: #494949; }
QDialog { background: #202124; color: #f2f2f2; }
QDialog QLabel, QCheckBox { color: #e8e8e8; }
QTabWidget::pane {
    background: #292a2d;
    border: 1px solid #414246;
    border-radius: 8px;
    top: -1px;
}
QTabBar::tab {
    color: #a9aaad;
    background: transparent;
    border: none;
    padding: 8px 14px;
}
QTabBar::tab:selected {
    color: #ffffff;
    background: #35363a;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:hover:!selected { color: #ffffff; background: #2b2c2f; }
QComboBox, QKeySequenceEdit, QKeySequenceEdit QLineEdit {
    color: #f3f3f3;
    background: #333438;
    border: 1px solid #4a4b50;
    border-radius: 6px;
    min-height: 30px;
    padding: 0 9px;
    selection-background-color: #1677d2;
}
QComboBox:hover, QKeySequenceEdit:hover { border-color: #66686e; }
QComboBox:focus, QKeySequenceEdit:focus { border-color: #2589e8; }
QKeySequenceEdit QLineEdit { border: none; }
QComboBox::drop-down { border: none; width: 28px; }
QComboBox QAbstractItemView {
    color: #f3f3f3;
    background: #333438;
    border: 1px solid #4a4b50;
    selection-background-color: #1677d2;
}
QDialogButtonBox QPushButton {
    color: #ededed;
    background: #343539;
    border: 1px solid #4b4c51;
    border-radius: 6px;
    min-height: 30px;
    padding: 0 14px;
}
QDialogButtonBox QPushButton:hover { background: #404146; border-color: #62646a; }
QDialogButtonBox QPushButton:pressed { background: #2b2c30; }
"""


def capture_ui_screenshots(app: QApplication) -> None:
    """Render every user-facing state to the project's images directory."""
    output_dir = Path(__file__).resolve().parent.parent / "images"
    output_dir.mkdir(exist_ok=True)
    config = Config.load()

    flyout = Flyout()
    flyout.switcher.set_colors(config.colors.game, config.colors.racing)
    flyout.adjustSize()
    flyout.move(80, 80)

    settings = SettingsDialog(config)
    settings.adjustSize()
    settings.move(80, 80)

    captures = [
        (flyout, "panel-desktop.png", lambda: flyout.switcher.set_active("game")),
        (flyout, "panel-driving.png", lambda: flyout.switcher.set_active("racing")),
        (settings, "settings-pc.png", lambda: settings.tabs.setCurrentIndex(0)),
        (settings, "settings-driving.png", lambda: settings.tabs.setCurrentIndex(1)),
        (settings, "settings-hotkeys.png", lambda: settings.tabs.setCurrentIndex(2)),
    ]
    state = {"index": 0}

    def next_capture() -> None:
        index = state["index"]
        if index >= len(captures):
            flyout.close()
            settings.close()
            app.quit()
            return
        widget, filename, prepare = captures[index]
        if widget is flyout:
            settings.hide()
        else:
            flyout.hide()
        prepare()
        widget.show()
        widget.raise_()
        app.processEvents()

        def save() -> None:
            widget.grab().save(str(output_dir / filename), "PNG")
            state["index"] += 1
            QTimer.singleShot(80, next_capture)

        # Allow animations, layouts and native controls to finish painting.
        QTimer.singleShot(350, save)

    # Keep the windows and callbacks alive until the last image is written.
    app.ui_capture = (flyout, settings, captures, state, next_capture)
    QTimer.singleShot(0, next_capture)


def main() -> int:
    screenshot_mode = "--screenshots" in sys.argv
    if sys.platform == "win32":
        # Give Windows a stable identity instead of grouping us as python.exe.
        import ctypes
        from ctypes import wintypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Switcher.Desktop.AudioDisplay"
        )
        if not screenshot_mode:
            # A second copy would compete for the same global hotkeys and tray icon.
            ctypes.windll.kernel32.CreateMutexW.restype = wintypes.HANDLE
            instance_mutex = ctypes.windll.kernel32.CreateMutexW(
                None, False, "Local\\Switcher.Desktop.AudioDisplay.Instance"
            )
            if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                ctypes.windll.user32.MessageBoxW(
                    None,
                    "Switcher is already running. Check the system tray.",
                    "Switcher",
                    0x40,
                )
                return 0
    app = QApplication(sys.argv)
    if sys.platform == "win32" and not screenshot_mode:
        app.instance_mutex = instance_mutex
    app.setApplicationName("Switcher")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(STYLE)
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    # Let Python handle Ctrl+C while Qt owns the main event loop.
    signal_timer = QTimer(app)
    signal_timer.timeout.connect(lambda: None)
    signal_timer.start(200)
    if screenshot_mode:
        capture_ui_screenshots(app)
        return app.exec()
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Switcher", "The system tray is unavailable")
        return 1
    # Keep the Python controller alive for as long as QApplication is alive;
    # otherwise its bound tray callbacks may disappear after garbage collection.
    app.switcher_controller = SwitcherApp(app)
    return app.exec()
