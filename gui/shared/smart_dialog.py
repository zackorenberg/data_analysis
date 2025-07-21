from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QScrollArea, QWidget, QDesktopWidget, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QEvent

#event_types = {getattr(QEvent, name): name for name in vars(QEvent)}

# Note: Currently only supports out of screen bottom and right, no plan on changing that

class SmartDialog(QDialog):
    def __init__(self, parent=None, scrollbar_always_visible = False, enforce_horizontal_size = False):
        """

        :param scrollbar_always_visible: When true, vertical scrollbar is always visible
        :param enforce_horizontal_size: When true, out of screen to the right will also impose a resize
        """
        super().__init__(parent)
        self.__scrollbar_always_visible = scrollbar_always_visible
        self.__enforce_horizontal_size = enforce_horizontal_size

        self._scroll_area = QScrollArea(self)
        self._scroll_area.setWidgetResizable(True)
        # I am not sure this is needed:
        # self._scroll_area.setSizeAdjustPolicy(QScrollArea.AdjustToContents)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        if self.__scrollbar_always_visible:
            self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        # we want scroll bar option incase its moved off to the right
        # self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        if self.__enforce_horizontal_size:
            self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._content_widget = QWidget()
        self._scroll_area.setWidget(self._content_widget)
        self._scroll_area.setFrameStyle(self._scroll_area.NoFrame)
        self._content_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self._scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._outer_layout = QVBoxLayout(self)
        self._outer_layout.setContentsMargins(0,0,0,0)
        self._outer_layout.setSizeConstraint(QVBoxLayout.SetFixedSize) # Disable user scrollable
        self._outer_layout.addWidget(self._scroll_area)
        super().setLayout(self._outer_layout)

        self._user_layout = None

        # Watch for dynamic updates to content layout
        self._content_widget.installEventFilter(self)

    def setLayout(self, layout):
        """Override to allow user-defined layout inside scroll area."""
        self._user_layout = layout
        self._content_widget.setLayout(layout)
        # Adjust size when event loop is free
        QTimer.singleShot(0, self._adjustSizeAndPosition)

    def showEvent(self, event):
        super().showEvent(event)
        # Adjust size when event loop is free
        QTimer.singleShot(0, self._adjustSizeAndPosition)

    def resizeEvent(self, event):
        if not getattr(self, "_adjusting", False):
            self._adjustSizeAndPosition()
        super().resizeEvent(event)

    def moveEvent(self, event):
        self._adjustSizeAndPosition()
        super().moveEvent(event)

    def eventFilter(self, obj, event):
        # Children events, we only want to figure out if its a resize or layout change
        ret = super().eventFilter(obj, event)
        if obj == self._content_widget:
            if event.type() == QEvent.Resize:
                self._adjustSizeAndPosition()
            elif event.type() == QEvent.LayoutRequest:
                QTimer.singleShot(10, self._adjustSizeAndPosition)

        return ret


    def _adjustSizeAndPosition(self):
        if getattr(self, "_adjusting", False):
            return  # Prevent recursive calls
        self._adjusting = True

        try:
            screen = QDesktopWidget().availableGeometry(self)
            content_hint = self._content_widget.sizeHint()

            scrollbar_extent = self._scroll_area.verticalScrollBar().sizeHint()

            # Estimate frame overhead (title bar, borders, etc)
            frame_geom = self.frameGeometry()
            normal_geom = self.geometry()
            frame_overhead_width = frame_geom.width() - normal_geom.width()
            frame_overhead_height = frame_geom.height() - normal_geom.height()

            # Margin added to in debugging, not needed but functional
            margin = 0 #24

            # Determine available maximum space from current position
            max_width = screen.right() - self.x() - frame_overhead_width - margin
            max_height = screen.bottom() - self.y() - frame_overhead_height - margin

            # Start with content size
            scroll_width = content_hint.width()
            scroll_height = content_hint.height()

            # Add padding for scrollbar if it is or will be visible
            if scroll_height > max_height or self.__scrollbar_always_visible:
                scroll_width += scrollbar_extent.width()


            # Clamp scroll area size to available space
            scroll_width = min(scroll_width, max_width) if self.__enforce_horizontal_size else scroll_width
            scroll_height = min(scroll_height, max_height)

            current_scroll_size = self._scroll_area.size()
            if (current_scroll_size.width() != scroll_width or current_scroll_size.height() != scroll_height):
                self._scroll_area.setMinimumSize(scroll_width, scroll_height)
                self._scroll_area.setMaximumSize(max_width, max_height)



            # Final dialog size includes frame overhead
            desired_width = scroll_width #+ frame_overhead_width
            desired_height = scroll_height #+ frame_overhead_height

            # Clamp to screen size
            final_width = min(desired_width, screen.width() - margin) if self.__enforce_horizontal_size else desired_width
            final_height = min(desired_height, screen.height() - margin)


            #if (current_size.width() != final_width or
            #        current_size.height() != final_height):

            current_size = self.size()
            if abs(current_size.height() - final_height) > 1 or (self.__enforce_horizontal_size and abs(current_size.width() - final_width) > 1):
                self.resize(final_width, final_height)

                # Defer execution until event loop is free
                QTimer.singleShot(0, self._adjustSizeAndPosition)

        finally:
            self._adjusting = False



