from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QFormLayout, QTextEdit, QColorDialog, QLayout, QMessageBox, QGroupBox)
from PyQt5.QtCore import pyqtSignal, QSize, Qt
from PyQt5.QtGui import QColor, QPainter, QPen

class ColorButton(QPushButton):
    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(40, 24))
        self._color = color
        self.setToolTip("Choose Color")
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
            # Draw red diagonal line
            pen = QPen(QColor('red'), 2)
            painter.setPen(pen)
            painter.drawLine(rect.topLeft(), rect.bottomRight())

    def update_style(self):
        if self._color:
            self.setStyleSheet(f"background-color: {self._color.name()}; border: 1px solid #888;")
        else:
            self.setStyleSheet("background-color: white; border: 1px solid #888;")

class PlotParamDialog(QDialog):
    paramsSelected = pyqtSignal(dict)

    def __init__(self, columns, current_params=None, comments=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot Parameters")
        self.setMinimumWidth(300)
        self.columns = columns
        self.current_params = current_params or {}
        self.comments = comments or []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        # Show comments at the top
        if self.comments:
            comment_text = '\n'.join(self.comments)
            comment_box = QTextEdit()
            comment_box.setReadOnly(True)
            comment_box.setPlainText(comment_text)
            comment_box.setMaximumHeight(100)
            layout.addWidget(comment_box)
        form = QFormLayout()
        self.x_combo = QComboBox()
        self.x_combo.addItems(self.columns)
        if 'x' in self.current_params:
            idx = self.columns.index(self.current_params['x'])
            self.x_combo.setCurrentIndex(idx)
        form.addRow("X column:", self.x_combo)
        self.y_combo = QComboBox()
        self.y_combo.addItems(self.columns)
        if 'y' in self.current_params:
            idx = self.columns.index(self.current_params['y'])
            self.y_combo.setCurrentIndex(idx)
        form.addRow("Y column:", self.y_combo)
        # Calculation field for x
        self.calc_x_edit = QLineEdit()
        self.calc_x_edit.setPlaceholderText("e.g. x / 100")
        if 'calc_x' in self.current_params:
            self.calc_x_edit.setText(str(self.current_params['calc_x']))
        form.addRow("X calculation:", self.calc_x_edit)
        # Calculation field for y
        self.calc_edit = QLineEdit()
        self.calc_edit.setPlaceholderText("e.g. y / 100")
        if 'calc_y' in self.current_params:
            self.calc_edit.setText(str(self.current_params['calc_y']))
        form.addRow("Y calculation:", self.calc_edit)
        # Min/Max for x and y
        self.minx_edit = QLineEdit()
        self.minx_edit.setPlaceholderText("Optional")
        if 'minx' in self.current_params:
            self.minx_edit.setText(str(self.current_params['minx']))
        form.addRow("Min X:", self.minx_edit)
        self.maxx_edit = QLineEdit()
        self.maxx_edit.setPlaceholderText("Optional")
        if 'maxx' in self.current_params:
            self.maxx_edit.setText(str(self.current_params['maxx']))
        form.addRow("Max X:", self.maxx_edit)
        self.miny_edit = QLineEdit()
        self.miny_edit.setPlaceholderText("Optional")
        if 'miny' in self.current_params:
            self.miny_edit.setText(str(self.current_params['miny']))
        form.addRow("Min Y:", self.miny_edit)
        self.maxy_edit = QLineEdit()
        self.maxy_edit.setPlaceholderText("Optional")
        if 'maxy' in self.current_params:
            self.maxy_edit.setText(str(self.current_params['maxy']))
        form.addRow("Max Y:", self.maxy_edit)
        # Arbitrary mask expressions
        self.mask_expr_edits = []
        self.mask_expr_layout = QVBoxLayout()
        mask_label = QLabel("Custom mask expressions (e.g. abs(x) <= 10):")
        self.mask_expr_layout.addWidget(mask_label)
        # Restore mask_exprs if present
        mask_exprs = self.current_params.get('mask_exprs', [])
        if isinstance(mask_exprs, str):
            mask_exprs = [mask_exprs]
        if mask_exprs:
            for expr in mask_exprs:
                self.add_mask_expr_field(expr)
        else:
            self.add_mask_expr_field()
        mask_btns = QHBoxLayout()
        add_mask_btn = QPushButton("+")
        remove_mask_btn = QPushButton("–")
        add_mask_btn.clicked.connect(self.add_mask_expr_field)
        remove_mask_btn.clicked.connect(self.remove_mask_expr_field)
        mask_btns.addWidget(add_mask_btn)
        mask_btns.addWidget(remove_mask_btn)
        self.mask_expr_layout.addLayout(mask_btns)
        layout.addLayout(form)
        layout.addLayout(self.mask_expr_layout)
        # Legend label
        self.legend_edit = QLineEdit()
        self.legend_edit.setPlaceholderText("Legend label")
        if 'legend' in self.current_params:
            self.legend_edit.setText(self.current_params['legend'])
        form.addRow("Legend:", self.legend_edit)
        # Linestyle
        self.linestyle_combo = QComboBox()
        self.linestyle_combo.addItems(['-', '--', '-.', ':', 'None'])
        if 'linestyle' in self.current_params:
            idx = self.linestyle_combo.findText(self.current_params['linestyle'])
            if idx >= 0:
                self.linestyle_combo.setCurrentIndex(idx)
        form.addRow("Line style:", self.linestyle_combo)
        # Marker style
        self.marker_combo = QComboBox()
        marker_options = [
            '', 'o', 's', '^', 'v', '<', '>', 'd', 'D', 'p', '*', 'h', 'H', '+', 'x', 'X', '.', ',', '|', '_'
        ]
        self.marker_combo.addItems(marker_options)
        if 'marker' in self.current_params:
            idx = self.marker_combo.findText(self.current_params['marker'])
            if idx >= 0:
                self.marker_combo.setCurrentIndex(idx)
        form.addRow("Marker:", self.marker_combo)
        # Color picker
        self.color = None
        if 'color' in self.current_params:
            self.color = QColor(self.current_params['color'])
        self.color_btn = ColorButton(self.color)
        self.color_btn.clicked.connect(self.choose_color)
        form.addRow("Color:", self.color_btn)
        layout.addLayout(form)
        btns = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        cancel_btn = QPushButton("Cancel")
        apply_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(apply_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)
        layout.setSizeConstraint(QLayout.SetFixedSize)
        self.setLayout(layout)

    def choose_color(self):
        color = QColorDialog.getColor(self.color or QColor(0, 0, 0), self, "Choose Color")
        if color.isValid():
            self.color = color
        else:
            self.color = None
        self.color_btn.set_color(self.color)

    def add_mask_expr_field(self, value=""):
        edit = QLineEdit()
        edit.setPlaceholderText("e.g. abs(x) <= 10")
        if value:
            edit.setText(value)
        self.mask_expr_edits.append(edit)
        self.mask_expr_layout.insertWidget(len(self.mask_expr_edits), edit)

    def remove_mask_expr_field(self):
        if self.mask_expr_edits:
            edit = self.mask_expr_edits.pop()
            self.mask_expr_layout.removeWidget(edit)
            edit.deleteLater()

    def accept(self):
        params = {
            'x': self.x_combo.currentText(),
            'y': self.y_combo.currentText(),
        }
        calc_x_val = self.calc_x_edit.text().strip()
        if calc_x_val:
            params['calc_x'] = calc_x_val
        calc_val = self.calc_edit.text().strip()
        if calc_val:
            params['calc_y'] = calc_val
        minx_val = self.minx_edit.text().strip()
        maxx_val = self.maxx_edit.text().strip()
        miny_val = self.miny_edit.text().strip()
        maxy_val = self.maxy_edit.text().strip()
        if minx_val:
            params['minx'] = minx_val
        if maxx_val:
            params['maxx'] = maxx_val
        if miny_val:
            params['miny'] = miny_val
        if maxy_val:
            params['maxy'] = maxy_val
        mask_exprs = [edit.text().strip() for edit in self.mask_expr_edits if edit.text().strip()]
        if mask_exprs:
            params['mask_exprs'] = mask_exprs
        legend = self.legend_edit.text().strip()
        if legend:
            params['legend'] = legend
        else:
            params['legend'] = f"{self.x_combo.currentText()} vs {self.y_combo.currentText()}"
        linestyle = self.linestyle_combo.currentText()
        if linestyle:
            params['linestyle'] = linestyle
        marker = self.marker_combo.currentText()
        if marker:
            params['marker'] = marker
        if self.color:
            color = self.color.name()
            if color:
                params['color'] = color
        self.paramsSelected.emit(params)
        super().accept()


#### Calc plot param dialog

class CalcPlotParamDialog(QDialog):
    """A dialog for plotting mathematical expressions of multiple columns."""
    paramsSelected = pyqtSignal(dict)

    def __init__(self, columns, parent=None, current_params=None, comments=None):  # Added current_params and comments
        super().__init__(parent)
        self.setWindowTitle("Plot with Math Expressions")
        self.setMinimumWidth(450)
        self.columns = columns
        self.variable_rows = []
        self.current_params = current_params or {}  # Store current parameters
        self.comments = comments or []  # Store comments
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Comments Section (NEW) ---
        if self.comments:
            comment_text = '\n'.join(self.comments)
            comment_box = QTextEdit()
            comment_box.setReadOnly(True)
            comment_box.setPlainText(comment_text)
            comment_box.setMaximumHeight(100)
            main_layout.addWidget(comment_box)

        # --- Variable Definitions Section ---
        variables_group = QGroupBox("1. Define Variables")
        self.variables_layout = QVBoxLayout()

        # Layout for the + and - buttons
        var_btn_layout = QHBoxLayout()
        var_btn_layout.addStretch()
        add_var_btn = QPushButton("Add Variable")
        add_var_btn.clicked.connect(self.add_variable_row)
        var_btn_layout.addWidget(add_var_btn)

        self.variables_layout.addLayout(var_btn_layout)
        variables_group.setLayout(self.variables_layout)
        main_layout.addWidget(variables_group)

        # Add initial rows for convenience or pre-populate from current_params
        definitions = self.current_params.get('definitions', {})
        if definitions:
            for var_name, col_name in definitions.items():
                self._add_variable_row_with_data(var_name, col_name)
        else:
            self.add_variable_row()  # Add at least one empty row
            self.add_variable_row()  # Add a second empty row for convenience

        # --- Expressions Section ---
        expressions_group = QGroupBox("2. Define Axes Expressions")
        form_layout = QFormLayout()
        self.x_expr_edit = QLineEdit()
        self.x_expr_edit.setPlaceholderText("e.g., b")
        self.x_expr_edit.setText(self.current_params.get('x_expression', ''))  # Pre-populate
        self.y_expr_edit = QLineEdit()
        self.y_expr_edit.setPlaceholderText("e.g., v / i")
        self.y_expr_edit.setText(self.current_params.get('y_expression', ''))  # Pre-populate
        form_layout.addRow("X-Axis Expression:", self.x_expr_edit)
        form_layout.addRow("Y-Axis Expression:", self.y_expr_edit)
        expressions_group.setLayout(form_layout)
        main_layout.addWidget(expressions_group)

        # --- Styling Section ---
        styling_group = QGroupBox("3. Style Plot")
        style_form_layout = QFormLayout()
        self.legend_edit = QLineEdit()
        self.legend_edit.setPlaceholderText("Legend label")
        self.legend_edit.setText(self.current_params.get('legend', ''))  # Pre-populate
        style_form_layout.addRow("Legend:", self.legend_edit)

        self.linestyle_combo = QComboBox()
        self.linestyle_combo.addItems(['-', '--', '-.', ':', 'None'])
        # Pre-populate
        if 'linestyle' in self.current_params:
            idx = self.linestyle_combo.findText(self.current_params['linestyle'])
            if idx >= 0:
                self.linestyle_combo.setCurrentIndex(idx)
        style_form_layout.addRow("Line style:", self.linestyle_combo)

        self.marker_combo = QComboBox()
        marker_options = ['', 'o', 's', '^', 'v', '<', '>', 'd', 'p', '*', '+', 'x']
        self.marker_combo.addItems(marker_options)
        # Pre-populate
        if 'marker' in self.current_params:
            idx = self.marker_combo.findText(self.current_params['marker'])
            if idx >= 0:
                self.marker_combo.setCurrentIndex(idx)
        style_form_layout.addRow("Marker:", self.marker_combo)

        # Pre-populate color
        initial_color = None
        if 'color' in self.current_params:
            initial_color = QColor(self.current_params['color'])
        self.color_btn = ColorButton(initial_color)  # Pass initial color to ColorButton
        self.color_btn.clicked.connect(self.choose_color)
        style_form_layout.addRow("Color:", self.color_btn)
        styling_group.setLayout(style_form_layout)
        main_layout.addWidget(styling_group)

        # TODO: add all other plotting options found in plot_dialog.py. Maybe by merging them

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

    def add_variable_row(self):
        """Adds a new empty row for defining a variable."""
        self._add_variable_row_with_data("", "")  # Call helper with empty data

    def _add_variable_row_with_data(self, var_name, col_name):
        """Adds a new row for defining a variable, pre-populating with data."""
        row_layout = QHBoxLayout()

        var_name_edit = QLineEdit()
        var_name_edit.setPlaceholderText("Var Name")
        var_name_edit.setFixedWidth(80)
        var_name_edit.setText(var_name)  # Set initial value

        equals_label = QLabel("=")

        column_combo = QComboBox()
        column_combo.addItems(self.columns)
        # Set initial value
        if col_name in self.columns:
            idx = column_combo.findText(col_name)
            if idx >= 0:
                column_combo.setCurrentIndex(idx)

        remove_btn = QPushButton("–")
        remove_btn.setFixedWidth(30)

        row_layout.addWidget(var_name_edit)
        row_layout.addWidget(equals_label)
        row_layout.addWidget(column_combo)
        row_layout.addWidget(remove_btn)

        # Insert the new row before the button layout
        # The index needs to be dynamic to insert above the "Add Variable" button
        self.variables_layout.insertLayout(len(self.variable_rows), row_layout)

        row_widgets = (row_layout, var_name_edit, column_combo)
        self.variable_rows.append(row_widgets)

        # The lambda captures the specific row_widgets tuple to be removed
        remove_btn.clicked.connect(lambda: self.remove_variable_row(row_widgets))
        return row_widgets  # Return for potential external use (e.g., by _init_ui)

    def remove_variable_row(self, row_widgets_to_remove):
        """Removes a specific variable definition row from the layout and our list."""
        if len(self.variable_rows) <= 1:
            QMessageBox.warning(self, "Cannot Remove", "At least one variable definition is required.")
            return

        # Find and remove from list
        self.variable_rows.remove(row_widgets_to_remove)

        # Unpack to get the layout
        row_layout, _, _ = row_widgets_to_remove

        # Remove all widgets from the layout and delete them
        while row_layout.count():
            item = row_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Remove the layout itself
        self.variables_layout.removeItem(row_layout)

    def choose_color(self):
        # Use the color from the button as the initial color for the dialog
        color = QColorDialog.getColor(self.color_btn.get_color() or QColor(0, 0, 0), self, "Choose Color")
        if color.isValid():
            self.color_btn.set_color(color)
        else:
            self.color_btn.set_color(None)  # Allow clearing the color

    def accept(self):
        """Collects all parameters and emits the signal."""
        definitions = {}
        for _, var_name_edit, column_combo in self.variable_rows:
            var_name = var_name_edit.text().strip()
            column_name = column_combo.currentText()
            if var_name and column_name:  # Only add if both are provided
                if not var_name.isidentifier():
                    QMessageBox.warning(self, "Invalid Variable",
                                        f"'{var_name}' is not a valid variable name. Please use letters, numbers, and underscores.")
                    return
                definitions[var_name] = column_name

        if not definitions:
            QMessageBox.warning(self, "No Variables", "Please define at least one variable.")
            return

        x_expr = self.x_expr_edit.text().strip()
        y_expr = self.y_expr_edit.text().strip()

        if not x_expr or not y_expr:
            QMessageBox.warning(self, "Missing Expression", "Please provide expressions for both the X and Y axes.")
            return

        xparam, yparam = x_expr, y_expr
        for var_name, column_name in definitions.items():
            xparam = xparam.replace(var_name, column_name)
            yparam = yparam.replace(var_name, column_name)

        params = {
            'plot_type': 'multi_column',  # Special key to identify this plot type
            'definitions': definitions,
            'x_expression': x_expr,
            'y_expression': y_expr,
            'x': xparam,
            'y': yparam,
        }

        # Add styling parameters only if they have values
        if self.legend_edit.text().strip():
            params['legend'] = self.legend_edit.text().strip()
        else:
            params['legend'] = f"{xparam} vs {yparam}"
        if self.linestyle_combo.currentText() and self.linestyle_combo.currentText() != 'None':  # 'None' is a valid option for no line
            params['linestyle'] = self.linestyle_combo.currentText()
        if self.marker_combo.currentText():  # Empty string is a valid option for no marker
            params['marker'] = self.marker_combo.currentText()
        if self.color_btn.get_color():
            params['color'] = self.color_btn.get_color().name()

        self.paramsSelected.emit(params)
        super().accept()
