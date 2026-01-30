from typing import List, Tuple

from aqt.qt import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    Qt,
    QVBoxLayout,
    QWidget,
)


class KeyFieldsDialog(QDialog):
    """Dialog for selecting primary and additional key fields for notecards."""

    def __init__(
        self,
        available_fields: List[str],
        primary_key: str = "",
        additional_keys: List[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.available_fields = available_fields
        self.additional_key_widgets = []
        self.field_id_counter = 0  # Counter for unique field IDs
        self.field_widgets = {}  # Maps field_id to (combo, layout, remove_button)
        self.primary_key = primary_key
        self.additional_keys = additional_keys or []

        self.setWindowTitle("Select Key Fields")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        self.setup_ui()
        self.load_existing_keys()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout()

        # Primary key field selection
        primary_layout = QHBoxLayout()
        primary_label = QLabel("Primary Key Field:")
        self.primary_combo = QComboBox()
        self.primary_combo.addItems(self.available_fields)
        primary_layout.addWidget(primary_label)
        primary_layout.addWidget(self.primary_combo)
        layout.addLayout(primary_layout)

        # Additional key fields section
        additional_label = QLabel("Additional Key Fields (optional):")
        layout.addWidget(additional_label)

        # Scroll area for additional fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.additional_widget = QWidget()
        self.additional_layout = QVBoxLayout(self.additional_widget)
        scroll.setWidget(self.additional_widget)
        layout.addWidget(scroll)

        # Add/Remove buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("+ Add Field")
        self.add_button.clicked.connect(self.add_additional_field)
        button_layout.addWidget(self.add_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Dialog buttons
        dialog_button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        dialog_button_layout.addStretch()
        dialog_button_layout.addWidget(self.ok_button)
        dialog_button_layout.addWidget(self.cancel_button)
        layout.addLayout(dialog_button_layout)

        self.setLayout(layout)

    def add_additional_field(self):
        """Add a new additional key field dropdown."""
        field_layout = QHBoxLayout()

        combo = QComboBox()
        combo.addItems(self.available_fields)

        remove_button = QPushButton("-")
        remove_button.setMaximumWidth(30)

        # Generate unique field ID
        field_id = self.field_id_counter
        self.field_id_counter += 1

        # Store references
        self.additional_layout.addLayout(field_layout)
        field_layout.addWidget(combo)
        field_layout.addWidget(remove_button)
        self.field_widgets[field_id] = (combo, field_layout, remove_button)
        self.additional_key_widgets.append(field_id)

        # Connect the remove button with the field ID
        remove_button.clicked.connect(
            lambda checked=False, fid=field_id: self.remove_additional_field(fid)
        )

    def remove_additional_field(self, field_id):
        """Remove an additional key field dropdown by field ID."""
        if field_id in self.field_widgets:
            combo, layout, remove_button = self.field_widgets[field_id]

            # Remove widgets from layout
            layout.removeWidget(combo)
            layout.removeWidget(remove_button)

            # Delete widgets
            combo.deleteLater()
            remove_button.deleteLater()

            # Remove layout from parent layout
            self.additional_layout.removeItem(layout)

            # Delete layout
            layout.deleteLater()

            # Remove from tracking
            del self.field_widgets[field_id]
            self.additional_key_widgets.remove(field_id)

    def load_existing_keys(self):
        """Load existing key selections."""
        # Set primary key
        if hasattr(self, "primary_key") and self.primary_key:
            index = self.primary_combo.findText(self.primary_key)
            if index >= 0:
                self.primary_combo.setCurrentIndex(index)

        # Load additional keys
        for key in self.additional_keys:
            self.add_additional_field()
            if self.additional_key_widgets:
                field_id = self.additional_key_widgets[-1]
                if field_id in self.field_widgets:
                    combo, layout, remove_button = self.field_widgets[field_id]
                    index = combo.findText(key)
                    if index >= 0:
                        combo.setCurrentIndex(index)

    def get_selected_fields(self) -> Tuple[str, List[str]]:
        """Get the selected primary and additional key fields.

        Returns:
            Tuple[str, List[str]]: (primary_key, additional_keys)
        """
        primary_key = self.primary_combo.currentText()
        additional_keys = []

        for field_id in self.additional_key_widgets:
            if field_id in self.field_widgets:
                combo, layout, remove_button = self.field_widgets[field_id]
                field = combo.currentText()
                if field and field not in additional_keys and field != primary_key:
                    additional_keys.append(field)

        return primary_key, additional_keys
