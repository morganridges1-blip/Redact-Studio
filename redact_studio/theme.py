"""Flat widget styles; native toolbar relief is deliberately removed."""

from .resources import asset


def stylesheet(theme):
    close_icon = asset('close.png').as_posix()
    dark = theme == 'dark'
    bg, panel, field, text, muted, line, hover = (
        ('#151a23', '#1d2430', '#252e3c', '#eef2f8', '#99a7bb', '#323e50', '#2b3749') if dark else
        ('#edf1f6', '#ffffff', '#f5f7fa', '#172437', '#637189', '#dce3ed', '#eaf0f8'))
    return f'''
        QWidget {{ background: {panel}; color: {text}; font-family: "Segoe UI", "DejaVu Sans"; font-size: 13px; }}
        QMainWindow, QDialog, QStackedWidget {{ background: {bg}; }}
        QLabel {{ background: transparent; }}
        QLabel#muted {{ color: {muted}; padding: 8px; }}
        QLabel#welcomeTitle {{ font-size: 28px; font-weight: 600; padding-top: 14px; }}
        QWidget#welcome {{ background: {bg}; }}
        QLabel#sectionTitle {{ color: {muted}; font-size: 11px; font-weight: 600; padding: 16px 12px 8px; }}
        QToolBar {{ background: {panel}; border: none; spacing: 4px; padding: 8px 12px; }}
        QToolBar::separator {{ width: 1px; background: {line}; margin: 8px; }}
        QToolButton {{ background: transparent; border: none; border-radius: 5px; padding: 8px 12px; }}
        QToolButton:hover {{ background: {hover}; }}
        QToolButton:pressed, QToolButton:checked {{ background: {field}; }}
        QToolButton:disabled {{ color: {muted}; }}
        QMenuBar {{ background: {panel}; border: none; padding: 2px 8px; }}
        QMenuBar::item {{ background: transparent; border: none; padding: 5px 9px; }}
        QMenuBar::item:selected, QMenu::item:selected {{ background: {hover}; }}
        QMenu {{ border: 1px solid {line}; padding: 6px; }}
        QMenu::item {{ padding: 7px 24px; }}
        QPushButton {{ background: {field}; border: 1px solid {line}; border-radius: 6px; padding: 8px 12px; }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:checked, QPushButton#primary {{ background: #2563eb; color: white; border: 1px solid #2563eb; }}
        QPushButton:disabled {{ color: {muted}; background: {field}; }}
        QLineEdit, QSpinBox, QComboBox {{ background: {field}; border: 1px solid {line}; border-radius: 5px; padding: 7px; }}
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: #4e85ee; }}
        QTabWidget::pane {{ border: none; }}
        QTabBar::tab {{ background: {panel}; color: {muted}; border: none; border-bottom: 2px solid transparent; padding: 10px 16px; }}
        QTabBar::tab:selected {{ color: {text}; border-bottom-color: #4e85ee; }}
        QTabBar::close-button {{ image: url("{close_icon}"); width: 12px; height: 12px; margin-left: 8px; }}
        QTabBar::close-button:hover {{ background: {hover}; border-radius: 3px; }}
        QSpinBox::up-button, QSpinBox::down-button {{ background: transparent; border: none; width: 16px; }}
        QTabBar::tab:hover {{ background: {hover}; }}
        QListWidget {{ background: {bg}; border: 1px solid {line}; border-radius: 5px; padding: 5px; outline: none; }}
        QListWidget::item {{ padding: 6px; border-radius: 4px; }}
        QListWidget::item:selected {{ background: {hover}; color: {text}; }}
        QScrollArea, QGraphicsView {{ border: none; }}
        QScrollBar:vertical {{ background: {bg}; width: 10px; margin: 0; }}
        QScrollBar:horizontal {{ background: {bg}; height: 10px; margin: 0; }}
        QScrollBar::handle {{ background: {line}; border-radius: 4px; min-height: 24px; min-width: 24px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: transparent; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
        QStatusBar {{ background: {panel}; color: {muted}; border-top: 1px solid {line}; padding: 5px 10px; }}
        QStatusBar::item {{ border: none; }}
        QMainWindow::separator {{ background: {bg}; width: 5px; height: 5px; }}
        QToolTip {{ background: {field}; color: {text}; border: 1px solid {line}; padding: 6px; }}
    '''
