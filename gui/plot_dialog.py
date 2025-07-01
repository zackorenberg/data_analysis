from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QFormLayout,
                             QTextEdit, QColorDialog, QLayout, QMessageBox, QGroupBox, QWidget)
from PyQt5.QtCore import pyqtSignal, QSize, Qt
from PyQt5.QtGui import QColor, QPainter, QPen


class ColorButton(QPushButton):
    """A button that displays a color and opens a color dialog on click."""

    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(40, 24))
        self._color = color
        self.setToolTip("Click to choose color.\nRight-click to clear.")
        self.update_style()

    def set_color(self, color):
        self._color = color
        self.update()
        self.update_style()

    def get_color(self):
        return self._color

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        rect = self.rect().adjusted(4, 4, -4, -4)
        if self._color:
            painter.setBrush(self._color)
            painter.setPen(QPen(QColor('black'), 1))
            painter.drawRect(rect)
        else:
            painter.setBrush(QColor('white'))
            painter.setPen(QPen(QColor('black'), 1))
            painter.drawRect(rect)
            # Draw red diagonal line to indicate no color
            pen = QPen(QColor('red'), 2)
            painter.setPen(pen)
            painter.drawLine(rect.topLeft(), rect.bottomRight())

    def update_style(self):
        if self._color:
            self.setStyleSheet(f"background-color: {self._color.name()}; border: 1px solid #888;")
        else:
            self.setStyleSheet("background-color: white; border: 1px solid #888;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # this makes it so that the color chosen is inherited by the color selector, which is undesirable
            #color = QColorDialog.getColor(self.get_color() or QColor(0, 0, 0), self, "Choose Color")
            color = QColorDialog.getColor(self.get_color() or QColor(0, 0, 0), self.parent(), "Choose Color")
            if color.isValid():
                self.set_color(color)
        elif event.button() == Qt.RightButton:
            self.set_color(None)
        super().mousePressEvent(event)


class _SharedPlotOptionsWidget(QWidget):
    """A reusable widget containing all common plot options (filtering, masking, styling)."""

    def __init__(self, current_params=None, parent=None):
        super().__init__(parent)
        self.current_params = current_params or {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Filtering Group ---
        filtering_group = QGroupBox("Filtering and Masking")
        form = QFormLayout()

        self.minx_edit = QLineEdit(str(self.current_params.get('minx', '')))
        self.minx_edit.setPlaceholderText("Optional")
        form.addRow("Min X:", self.minx_edit)

        self.maxx_edit = QLineEdit(str(self.current_params.get('maxx', '')))
        self.maxx_edit.setPlaceholderText("Optional")
        form.addRow("Max X:", self.maxx_edit)

        self.miny_edit = QLineEdit(str(self.current_params.get('miny', '')))
        self.miny_edit.setPlaceholderText("Optional")
        form.addRow("Min Y:", self.miny_edit)

        self.maxy_edit = QLineEdit(str(self.current_params.get('maxy', '')))
        self.maxy_edit.setPlaceholderText("Optional")
        form.addRow("Max Y:", self.maxy_edit)

        filtering_group.setLayout(form)
        layout.addWidget(filtering_group)

        # --- Custom Mask Group ---
        mask_group = QGroupBox("Custom Mask Expressions")
        self.mask_expr_layout = QVBoxLayout()
        mask_label = QLabel("e.g., abs(x) <= 10 or y > 0")
        self.mask_expr_layout.addWidget(mask_label)

        self.mask_expr_edits = []
        mask_exprs = self.current_params.get('mask_exprs', [])
        if isinstance(mask_exprs, str): mask_exprs = [mask_exprs]

        if mask_exprs:
            for expr in mask_exprs:
                self._add_mask_expr_field(expr)
        else:
            self._add_mask_expr_field()  # Add one empty field to start

        mask_btns_layout = QHBoxLayout()
        add_mask_btn = QPushButton("+")
        remove_mask_btn = QPushButton("–")
        add_mask_btn.clicked.connect(lambda: self._add_mask_expr_field())
        remove_mask_btn.clicked.connect(self._remove_mask_expr_field)
        mask_btns_layout.addStretch()
        mask_btns_layout.addWidget(add_mask_btn)
        mask_btns_layout.addWidget(remove_mask_btn)
        self.mask_expr_layout.addLayout(mask_btns_layout)

        mask_group.setLayout(self.mask_expr_layout)
        layout.addWidget(mask_group)

        # --- Styling Group ---
        styling_group = QGroupBox("Styling")
        style_form_layout = QFormLayout()

        self.axis_combo = QComboBox()
        self.axis_combo.addItems(['Primary', 'Secondary Y', 'Secondary X', 'Secondary X and Y'])
        if 'axis' in self.current_params:
            idx = self.axis_combo.findText(self.current_params['axis'])
            if idx >= 0: self.axis_combo.setCurrentIndex(idx)
        style_form_layout.addRow("Axis:", self.axis_combo)

        self.legend_edit = QLineEdit(self.current_params.get('legend', ''))
        self.legend_edit.setPlaceholderText("Legend label")
        style_form_layout.addRow("Legend:", self.legend_edit)

        self.linestyle_combo = QComboBox()
        self.linestyle_combo.addItems(['-', '--', '-.', ':', 'None'])
        if 'linestyle' in self.current_params:
            idx = self.linestyle_combo.findText(self.current_params['linestyle'])
            if idx >= 0: self.linestyle_combo.setCurrentIndex(idx)
        style_form_layout.addRow("Line style:", self.linestyle_combo)

        self.marker_combo = QComboBox()
        self.marker_combo.addItems(['', 'o', 's', '^', 'v', '<', '>', 'd', 'p', '*', '+', 'x'])
        if 'marker' in self.current_params:
            idx = self.marker_combo.findText(self.current_params['marker'])
            if idx >= 0: self.marker_combo.setCurrentIndex(idx)
        style_form_layout.addRow("Marker:", self.marker_combo)

        initial_color = QColor(self.current_params['color']) if 'color' in self.current_params else None
        self.color_btn = ColorButton(initial_color)
        style_form_layout.addRow("Color:", self.color_btn)

        styling_group.setLayout(style_form_layout)
        layout.addWidget(styling_group)

    def _add_mask_expr_field(self, value=""):
        edit = QLineEdit(value)
        edit.setPlaceholderText("e.g. y > 0")
        self.mask_expr_layout.insertWidget(self.mask_expr_layout.count() - 1, edit)
        self.mask_expr_edits.append(edit)

    def _remove_mask_expr_field(self):
        if len(self.mask_expr_edits) > 1:
            edit = self.mask_expr_edits.pop()
            self.mask_expr_layout.removeWidget(edit)
            edit.deleteLater()

    def get_params(self):
        """Collects and returns all parameters from this shared widget."""
        params = {}
        if self.minx_edit.text().strip(): params['minx'] = self.minx_edit.text().strip()
        if self.maxx_edit.text().strip(): params['maxx'] = self.maxx_edit.text().strip()
        if self.miny_edit.text().strip(): params['miny'] = self.miny_edit.text().strip()
        if self.maxy_edit.text().strip(): params['maxy'] = self.maxy_edit.text().strip()

        mask_exprs = [edit.text().strip() for edit in self.mask_expr_edits if edit.text().strip()]
        if mask_exprs: params['mask_exprs'] = mask_exprs

        if self.legend_edit.text().strip(): params['legend'] = self.legend_edit.text().strip()
        if self.linestyle_combo.currentText() != 'None': params['linestyle'] = self.linestyle_combo.currentText()
        if self.marker_combo.currentText(): params['marker'] = self.marker_combo.currentText()
        if self.color_btn.get_color(): params['color'] = self.color_btn.get_color().name()

        return params


class PlotParamDialog(QDialog):
    """Dialog for simple X vs Y plotting with optional calculations."""
    paramsSelected = pyqtSignal(dict)

    def __init__(self, columns, current_params=None, comments=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot Parameters")
        self.setMinimumWidth(450)
        self.columns = columns
        self.current_params = current_params or {}
        self.comments = comments or []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        if self.comments:
            comment_box = QTextEdit()
            comment_box.setReadOnly(True)
            comment_box.setMaximumHeight(100)
            comment_box.setPlainText('\n'.join(self.comments))
            main_layout.addWidget(comment_box)

        # --- Data Source Group ---
        source_group = QGroupBox("Data Source")
        form = QFormLayout()
        self.x_combo = QComboBox()
        self.x_combo.addItems(self.columns)
        if 'x' in self.current_params:
            idx = self.x_combo.findText(self.current_params['x'])
            if idx >= 0: self.x_combo.setCurrentIndex(idx)
        form.addRow("X column:", self.x_combo)

        self.y_combo = QComboBox()
        self.y_combo.addItems(self.columns)
        if 'y' in self.current_params:
            idx = self.y_combo.findText(self.current_params['y'])
            if idx >= 0: self.y_combo.setCurrentIndex(idx)
        form.addRow("Y column:", self.y_combo)

        self.calc_x_edit = QLineEdit(str(self.current_params.get('calc_x', '')))
        self.calc_x_edit.setPlaceholderText("e.g. x / 100 (optional)")
        form.addRow("X calculation:", self.calc_x_edit)

        self.calc_y_edit = QLineEdit(str(self.current_params.get('calc_y', '')))
        self.calc_y_edit.setPlaceholderText("e.g. y / 100 (optional)")
        form.addRow("Y calculation:", self.calc_y_edit)
        source_group.setLayout(form)
        main_layout.addWidget(source_group)

        # --- Shared Options ---
        self.shared_options = _SharedPlotOptionsWidget(self.current_params)
        main_layout.addWidget(self.shared_options)

        # --- OK/Cancel Buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton("Plot")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

        main_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(main_layout)

    def accept(self):
        params = {
            'x': self.x_combo.currentText(),
            'y': self.y_combo.currentText(),
        }
        if self.calc_x_edit.text().strip(): params['calc_x'] = self.calc_x_edit.text().strip()
        if self.calc_y_edit.text().strip(): params['calc_y'] = self.calc_y_edit.text().strip()

        shared_params = self.shared_options.get_params()
        params.update(shared_params)

        if 'legend' not in params:
            params['legend'] = f"{params['y']} vs {params['x']}"

        self.paramsSelected.emit(params)
        super().accept()


class CalcPlotParamDialog(QDialog):
    """A dialog for plotting mathematical expressions of multiple columns."""
    paramsSelected = pyqtSignal(dict)

    def __init__(self, columns, parent=None, current_params=None, comments=None):
        super().__init__(parent)
        self.setWindowTitle("Plot with Math Expressions")
        self.setMinimumWidth(450)
        self.columns = columns
        self.variable_rows = []
        self.current_params = current_params or {}
        self.comments = comments or []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        if self.comments:
            comment_text = '\n'.join(self.comments)
            comment_box = QTextEdit()
            comment_box.setReadOnly(True)
            comment_box.setMaximumHeight(100)
            comment_box.setPlainText(comment_text)
            main_layout.addWidget(comment_box)

        # --- Variable Definitions Section ---
        variables_group = QGroupBox("Define Variables")
        self.variables_layout = QVBoxLayout()
        var_btn_layout = QHBoxLayout()
        var_btn_layout.addStretch()
        add_var_btn = QPushButton("Add Variable")
        add_var_btn.clicked.connect(self.add_variable_row)
        var_btn_layout.addWidget(add_var_btn)
        self.variables_layout.addLayout(var_btn_layout)
        variables_group.setLayout(self.variables_layout)
        main_layout.addWidget(variables_group)

        definitions = self.current_params.get('definitions', {})
        if definitions:
            for var_name, col_name in definitions.items():
                self._add_variable_row_with_data(var_name, col_name)
        else:
            self.add_variable_row()
            self.add_variable_row()

        # --- Expressions Section ---
        expressions_group = QGroupBox("Define Axes Expressions")
        form_layout = QFormLayout()
        self.x_expr_edit = QLineEdit(self.current_params.get('x_expression', ''))
        self.x_expr_edit.setPlaceholderText("e.g., b")
        self.y_expr_edit = QLineEdit(self.current_params.get('y_expression', ''))
        self.y_expr_edit.setPlaceholderText("e.g., v / i")
        form_layout.addRow("X-Axis Expression:", self.x_expr_edit)
        form_layout.addRow("Y-Axis Expression:", self.y_expr_edit)
        expressions_group.setLayout(form_layout)
        main_layout.addWidget(expressions_group)

        # --- Shared Options ---
        self.shared_options = _SharedPlotOptionsWidget(self.current_params)
        main_layout.addWidget(self.shared_options)

        # --- OK/Cancel Buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton("Plot")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

        main_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(main_layout)

    def add_variable_row(self):
        self._add_variable_row_with_data("", "")

    def _add_variable_row_with_data(self, var_name, col_name):
        row_layout = QHBoxLayout()
        var_name_edit = QLineEdit(var_name)
        var_name_edit.setPlaceholderText("Var Name")
        var_name_edit.setFixedWidth(80)
        column_combo = QComboBox()
        column_combo.addItems(self.columns)
        if col_name in self.columns:
            idx = column_combo.findText(col_name)
            if idx >= 0: column_combo.setCurrentIndex(idx)
        remove_btn = QPushButton("–")
        remove_btn.setFixedWidth(30)
        row_layout.addWidget(var_name_edit)
        row_layout.addWidget(QLabel("="))
        row_layout.addWidget(column_combo)
        row_layout.addWidget(remove_btn)
        self.variables_layout.insertLayout(len(self.variable_rows), row_layout)
        row_widgets = (row_layout, var_name_edit, column_combo)
        self.variable_rows.append(row_widgets)
        remove_btn.clicked.connect(lambda: self.remove_variable_row(row_widgets))

    def remove_variable_row(self, row_widgets_to_remove):
        if len(self.variable_rows) <= 1:
            QMessageBox.warning(self, "Cannot Remove", "At least one variable definition is required.")
            return
        self.variable_rows.remove(row_widgets_to_remove)
        row_layout, _, _ = row_widgets_to_remove
        while row_layout.count():
            item = row_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.variables_layout.removeItem(row_layout)

    def accept(self):
        definitions = {}
        for _, var_name_edit, column_combo in self.variable_rows:
            var_name = var_name_edit.text().strip()
            column_name = column_combo.currentText()
            if var_name and column_name:
                if not var_name.isidentifier():
                    QMessageBox.warning(self, "Invalid Variable", f"'{var_name}' is not a valid Python identifier.")
                    return
                definitions[var_name] = column_name
        if not definitions:
            QMessageBox.warning(self, "No Variables", "Please define at least one variable.")
            return

        x_expr = self.x_expr_edit.text().strip()
        y_expr = self.y_expr_edit.text().strip()
        if not x_expr or not y_expr:
            QMessageBox.warning(self, "Missing Expression", "Please provide expressions for both axes.")
            return

        params = {
            'plot_type': 'multi_column',
            'definitions': definitions,
            'x_expression': x_expr,
            'y_expression': y_expr,
        }

        shared_params = self.shared_options.get_params()
        params.update(shared_params)

        if 'legend' not in params:
            params['legend'] = f"{y_expr} vs {x_expr}"

        self.paramsSelected.emit(params)
        super().accept()
