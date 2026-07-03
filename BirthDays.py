import sys
import os
import sqlite3
import csv
import subprocess
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QStackedWidget, QPushButton, QLabel, QComboBox, QTableWidget, 
    QTableWidgetItem, QLineEdit, QFormLayout, QFileDialog, QMessageBox,
    QHeaderView, QGraphicsDropShadowEffect, QTextEdit, QDialog, QDialogButtonBox
)
from PyQt6.QtGui import QFont, QColor

DB_NAME = "Birthday_Recorder.db"

class DatabaseManager:
    """Manages the SQLite database operations with structural schema updates."""
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.create_table()
        self.update_schema_if_needed()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS birthdays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                day INTEGER NOT NULL,
                month TEXT NOT NULL,
                year INTEGER,
                country TEXT,
                state TEXT,
                district TEXT,
                remarks TEXT,
                relation TEXT,
                phone TEXT
            )
        ''')
        self.conn.commit()

    def update_schema_if_needed(self):
        """Ensures existing databases gracefully adapt to the new phone number field constraint."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(birthdays)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'phone' not in columns:
            cursor.execute("ALTER TABLE birthdays ADD COLUMN phone TEXT")
            self.conn.commit()

    def insert_birthday(self, data):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO birthdays (name, day, month, year, country, state, district, remarks, relation, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', data)
        self.conn.commit()

    def update_birthday(self, row_id, data):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE birthdays 
            SET name=?, day=?, month=?, year=?, country=?, state=?, district=?, remarks=?, relation=?, phone=?
            WHERE id=?
        ''', data + (row_id,))
        self.conn.commit()

    def delete_birthday(self, row_id):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM birthdays WHERE id=?', (row_id,))
        self.conn.commit()

    def get_birthdays_by_month(self, month_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT name, district, remarks, day, month, year, country, state, relation, phone 
            FROM birthdays 
            WHERE LOWER(month) = LOWER(?)
            ORDER BY CAST(day AS INTEGER) ASC
        ''', (month_name,))
        return cursor.fetchall()

    def get_all_ordered_by_name(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id, name, day, month, year, country, state, district, remarks, relation, phone FROM birthdays ORDER BY name COLLATE NOCASE ASC')
        return cursor.fetchall()

    def import_from_csv(self, file_path):
        cursor = self.conn.cursor()
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 10:
                    cursor.execute('''
                        INSERT INTO birthdays (name, day, month, year, country, state, district, remarks, relation, phone)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', row[:10])
        self.conn.commit()

    def export_to_csv(self, file_path):
        cursor = self.conn.cursor()
        cursor.execute('SELECT name, day, month, year, country, state, district, remarks, relation, phone FROM birthdays')
        rows = cursor.fetchall()
        with open(file_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Day', 'Month', 'Year', 'Country', 'State', 'District', 'Remarks', 'Relation', 'Phone'])
            writer.writerows(rows)


class EditRecordDialog(QDialog):
    """Modal dialog housing structured fields to modify records safely."""
    def __init__(self, parent, current_data, months_list):
        super().__init__(parent)
        self.setWindowTitle("Modify Registry Record")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog { background-color: #121212; border: 1px solid #2C2C2C; }
            QLabel { color: #B0B0B0; font-size: 13px; }
            QLineEdit, QComboBox { background-color: #1C1C1C; border: 1px solid #333333; color: #FFFFFF; padding: 6px; border-radius: 4px; }
            QComboBox QAbstractItemView { background-color: #FFFFFF; color: #000000; }
        """)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.inputs = {
            "name": QLineEdit(str(current_data[1])),
            "day": QLineEdit(str(current_data[2])),
            "month": QComboBox(),
            "year": QLineEdit(str(current_data[4]) if current_data[4] else ""),
            "country": QLineEdit(str(current_data[5])),
            "state": QLineEdit(str(current_data[6])),
            "district": QLineEdit(str(current_data[7])),
            "remarks": QLineEdit(str(current_data[8])),
            "relation": QLineEdit(str(current_data[9])),
            "phone": QLineEdit(str(current_data[10]) if len(current_data) > 10 and current_data[10] else "")
        }
        
        self.inputs["month"].addItems(months_list)
        idx = self.inputs["month"].findText(str(current_data[3]))
        if idx >= 0:
            self.inputs["month"].setCurrentIndex(idx)
            
        form_layout.addRow("Name *", self.inputs["name"])
        form_layout.addRow("Day *", self.inputs["day"])
        form_layout.addRow("Month *", self.inputs["month"])
        form_layout.addRow("Year", self.inputs["year"])
        form_layout.addRow("Country", self.inputs["country"])
        form_layout.addRow("State", self.inputs["state"])
        form_layout.addRow("District", self.inputs["district"])
        form_layout.addRow("Remarks", self.inputs["remarks"])
        form_layout.addRow("Relation", self.inputs["relation"])
        form_layout.addRow("Phone Number", self.inputs["phone"])
        
        layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_form_values(self):
        return (
            self.inputs["name"].text().strip(),
            self.inputs["day"].text().strip(),
            self.inputs["month"].currentText(),
            self.inputs["year"].text().strip(),
            self.inputs["country"].text().strip(),
            self.inputs["state"].text().strip(),
            self.inputs["district"].text().strip(),
            self.inputs["remarks"].text().strip(),
            self.inputs["relation"].text().strip(),
            self.inputs["phone"].text().strip()
        )


class BirthdayApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Birthday Reminder")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.showFullScreen()

        self.setStyleSheet("""
            QMainWindow { background-color: #0A0A0A; }
            QWidget { color: #FFFFFF; font-family: 'Segoe UI', Arial, sans-serif; }
            QLineEdit, QComboBox { background-color: #161616; border: 1px solid #2C2C2C; border-radius: 5px; padding: 8px; color: #FFFFFF; font-size: 14px; }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #555555; background-color: #1D1D1D; }
            QPushButton { background-color: #1E1E1E; border: 1px solid #333333; border-radius: 5px; padding: 8px 16px; font-size: 14px; font-weight: 500; }
            QPushButton:hover { background-color: #2A2A2A; border-color: #444444; }
            QPushButton:pressed { background-color: #141414; }
            QTableWidget { background-color: #0F0F0F; border: 1px solid #222222; gridline-color: #1F1F1F; border-radius: 6px; }
            QHeaderView::section { background-color: #161616; color: #888888; padding: 8px; border: none; font-weight: bold; font-size: 12px; }
            QTableWidget::item { padding: 10px; border-bottom: 1px solid #181818; }
        """)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        title_bar = QWidget()
        title_bar.setFixedHeight(50)
        title_bar.setStyleSheet("background-color: #0A0A0A; border-bottom: 1px solid #141414;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 0, 15, 0)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(8)
        
        close_btn = QPushButton()
        close_btn.setFixedSize(14, 14)
        close_btn.setStyleSheet("background-color: #FF5F56; border: none; border-radius: 7px;")
        close_btn.clicked.connect(self.close)
        
        minimize_btn = QPushButton()
        minimize_btn.setFixedSize(14, 14)
        minimize_btn.setStyleSheet("background-color: #FFBD2E; border: none; border-radius: 7px;")
        minimize_btn.clicked.connect(self.showMinimized)

        control_layout.addWidget(close_btn)
        control_layout.addWidget(minimize_btn)
        title_layout.addLayout(control_layout)

        title_label = QLabel("Birthday Reminder")
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #888888; margin-left: 15px;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        workspace_layout = QHBoxLayout()
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background-color: #0D0D0D; border-right: 1px solid #141414;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 30, 15, 15)
        sidebar_layout.setSpacing(12)

        nav_title = QLabel("NAVIGATION")
        nav_title.setStyleSheet("color: #444444; font-size: 11px; font-weight: bold; letter-spacing: 1px; margin-bottom: 5px;")
        sidebar_layout.addWidget(nav_title)

        self.btn_page1 = QPushButton("Monthly Tracker")
        self.btn_page2 = QPushButton("New Entry")
        self.btn_page3 = QPushButton("Database Archive")
        self.btn_page4 = QPushButton("About & License")

        for btn in [self.btn_page1, self.btn_page2, self.btn_page3, self.btn_page4]:
            btn.setFixedHeight(42)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { text-align: left; padding-left: 15px; background-color: transparent; border: none; border-radius: 6px; color: #A0A0A0; font-size: 14px; }
                QPushButton:hover { background-color: #161616; color: #FFFFFF; }
                QPushButton:checked { background-color: #202020; color: #FFFFFF; font-weight: bold; }
            """)
            btn.setCheckable(True)
            sidebar_layout.addWidget(btn)

        self.btn_page1.setChecked(True)
        sidebar_layout.addStretch()

        self.btn_page1.clicked.connect(lambda: self.switch_page(0))
        self.btn_page2.clicked.connect(lambda: self.switch_page(1))
        self.btn_page3.clicked.connect(lambda: self.switch_page(2))
        self.btn_page4.clicked.connect(lambda: self.switch_page(3))

        self.pages_container = QStackedWidget()
        self.setup_page1()
        self.setup_page2()
        self.setup_page3()
        self.setup_page4()

        workspace_layout.addWidget(sidebar)
        workspace_layout.addWidget(self.pages_container)

        main_layout.addWidget(title_bar)
        main_layout.addLayout(workspace_layout)
        self.setCentralWidget(central_widget)

    def switch_page(self, index):
        self.btn_page1.setChecked(index == 0)
        self.btn_page2.setChecked(index == 1)
        self.btn_page3.setChecked(index == 2)
        self.btn_page4.setChecked(index == 3)
        self.pages_container.setCurrentIndex(index)
        
        if index == 0:
            self.refresh_page1_data()
        elif index == 2:
            self.refresh_page3_data()

    # --- PAGE 1: MONTHLY TRACKER ---
    def setup_page1(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        self.page1_title = QLabel("Birthdays of This Month")
        self.page1_title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        
        self.month_dropdown = QComboBox()
        self.month_dropdown.setStyleSheet("""
            QComboBox QAbstractItemView {
                background-color: #FFFFFF; color: #000000; selection-background-color: #E0E0E0; selection-color: #000000; border: 1px solid #CCCCCC;
            }
        """)
        self.month_dropdown.addItems(self.months)
        self.month_dropdown.setFixedWidth(160)
        current_month_idx = sys.modules['PyQt6'].QtCore.QDate.currentDate().month() - 1
        self.month_dropdown.setCurrentIndex(current_month_idx)
        self.month_dropdown.currentIndexChanged.connect(self.refresh_page1_data)

        header_layout.addWidget(self.page1_title)
        header_layout.addStretch()
        header_layout.addWidget(self.month_dropdown)
        layout.addLayout(header_layout)

        self.table_month = QTableWidget()
        self.table_month.setColumnCount(7)
        self.table_month.setHorizontalHeaderLabels([
            "Name of Person", "Day", "Phone Number", "Year", "Place (District)", "Remarks", "Quick View"
        ])
        self.table_month.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_month.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.table_month)
        self.pages_container.addWidget(page)
        self.refresh_page1_data()

    def refresh_page1_data(self):
        selected_month = self.month_dropdown.currentText()
        self.page1_title.setText(f"Birthdays of {selected_month}")
        
        records = self.db.get_birthdays_by_month(selected_month)
        self.table_month.setRowCount(len(records))
        
        for i, row in enumerate(records):
            name, district, remarks, day, month, year, country, state, relation, phone = row
            
            self.table_month.setItem(i, 0, QTableWidgetItem(str(name)))
            self.table_month.setItem(i, 1, QTableWidgetItem(str(day)))
            self.table_month.setItem(i, 2, QTableWidgetItem(str(phone) if phone else "N/A"))
            self.table_month.setItem(i, 3, QTableWidgetItem(str(year) if year else ""))
            self.table_month.setItem(i, 4, QTableWidgetItem(str(district)))
            self.table_month.setItem(i, 5, QTableWidgetItem(str(remarks)))
            
            notepad_btn = QPushButton("Open in Notepad")
            notepad_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            notepad_btn.setStyleSheet("""
                QPushButton { background-color: #161616; border: 1px solid #2A2A2A; color: #A0A0A0; font-size: 11px; padding: 4px; }
                QPushButton:hover { background-color: #FFFFFF; color: #000000; font-weight: bold; }
            """)
            
            data_map = {
                "Name of Person": name,
                "Day": day,
                "Month": month,
                "Year": year if year else 'N/A',
                "Phone Number": phone if phone else 'N/A',
                "Country": country,
                "State": state,
                "District": district,
                "Remarks": remarks,
                "Relation to Me": relation
            }
            
            notepad_btn.clicked.connect(lambda checked, d=data_map: self.generate_notepad_profile(d))
            self.table_month.setCellWidget(i, 6, notepad_btn)

    def generate_notepad_profile(self, data):
        lines = []
        for label, val in data.items():
            lines.append(f"{label}: {val}")
        
        content = "\n".join(lines)
        file_name = f"Profile_{str(data['Name of Person']).replace(' ', '_')}.txt"
        
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(content)
            
            if sys.platform == "win32":
                os.startfile(file_name)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "TextEdit", file_name])
            else:
                subprocess.Popen(["xdg-open", file_name])
        except Exception as err:
            QMessageBox.critical(self, "System Process Error", f"Could not create text profile asset stream: {str(err)}")


    # --- PAGE 2: DATA ENTRY PAGE ---
    def setup_page2(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        title = QLabel("Add New Birthday Profile")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        form_scroll = QWidget()
        form_layout = QFormLayout(form_scroll)
        form_layout.setSpacing(15)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.inputs = {
            "name": QLineEdit(),
            "day": QLineEdit(),
            "month": QComboBox(),
            "year": QLineEdit(),
            "country": QLineEdit(),
            "state": QLineEdit(),
            "district": QLineEdit(),
            "remarks": QLineEdit(),
            "relation": QLineEdit(),
            "phone": QLineEdit()
        }

        self.inputs["month"].setStyleSheet("""
            QComboBox QAbstractItemView { background-color: #FFFFFF; color: #000000; selection-background-color: #E0E0E0; selection-color: #000000; }
        """)
        self.inputs["month"].addItems(self.months)

        self.inputs["name"].setPlaceholderText("e.g., John Doe")
        self.inputs["day"].setPlaceholderText("e.g., 14")
        self.inputs["year"].setPlaceholderText("e.g., 1995 (Optional)")
        self.inputs["country"].setPlaceholderText("e.g., India")
        self.inputs["state"].setPlaceholderText("e.g., Kerala")
        self.inputs["district"].setPlaceholderText("e.g., Thrissur")
        self.inputs["remarks"].setPlaceholderText("e.g., Loves filter coffee and classical books")
        self.inputs["relation"].setPlaceholderText("e.g., College Friend")
        self.inputs["phone"].setPlaceholderText("e.g., +91 9876543210 (Optional)")

        labels = [
            ("Name of Person *", "name"),
            ("Birth Day (DD) *", "day"),
            ("Birth Month *", "month"),
            ("Birth Year", "year"),
            ("Phone Number", "phone"),
            ("Country", "country"),
            ("State", "state"),
            ("District", "district"),
            ("Special Remarks", "remarks"),
            ("Relation to Me", "relation")
        ]

        for label_text, key in labels:
            label_obj = QLabel(label_text)
            label_obj.setStyleSheet("font-size: 14px; color: #B0B0B0; font-weight: 500;")
            form_layout.addRow(label_obj, self.inputs[key])

        layout.addWidget(form_scroll)

        btn_layout = QHBoxLayout()
        submit_btn = QPushButton("Save Entry Data")
        submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        submit_btn.setMinimumSize(180, 45)
        submit_btn.setStyleSheet("""
            QPushButton { background-color: #FFFFFF; color: #000000; font-weight: bold; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: #E0E0E0; }
            QPushButton:pressed { background-color: #CCCCCC; }
        """)
        submit_btn.clicked.connect(self.save_entry)
        
        btn_layout.addStretch()
        btn_layout.addWidget(submit_btn)
        layout.addLayout(btn_layout)
        
        self.pages_container.addWidget(page)

    def save_entry(self):
        name = self.inputs["name"].text().strip()
        day_str = self.inputs["day"].text().strip()
        month = self.inputs["month"].currentText()
        year_str = self.inputs["year"].text().strip()
        country = self.inputs["country"].text().strip()
        state = self.inputs["state"].text().strip()
        district = self.inputs["district"].text().strip()
        remarks = self.inputs["remarks"].text().strip()
        relation = self.inputs["relation"].text().strip()
        phone = self.inputs["phone"].text().strip()

        if not name or not day_str:
            QMessageBox.warning(self, "Validation Error", "Name and Day field parameters are structural requirements.")
            return

        try:
            day = int(day_str)
            if not (1 <= day <= 31):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Day must resolve to an absolute calendar day integer value (1-31).")
            return

        year = None
        if year_str:
            try:
                year = int(year_str)
            except ValueError:
                QMessageBox.warning(self, "Validation Error", "Year must resolve to a valid calendar year representation.")
                return

        data_pack = (name, day, month, year, country, state, district, remarks, relation, phone)
        self.db.insert_birthday(data_pack)
        
        QMessageBox.information(self, "Success", "Record written successfully into the persistent log storage layer.")
        
        for key, field in self.inputs.items():
            if isinstance(field, QLineEdit):
                field.clear()
        self.inputs["month"].setCurrentIndex(0)


    # --- PAGE 3: DATABASE ARCHIVE LISTING PAGE ---
    def setup_page3(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        title = QLabel("System Archive Index")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()

        import_btn = QPushButton("Import CSV Data")
        export_btn = QPushButton("Export Archive File")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        import_btn.clicked.connect(self.import_database)
        export_btn.clicked.connect(self.export_database)

        header_layout.addWidget(import_btn)
        header_layout.addWidget(export_btn)
        layout.addLayout(header_layout)

        self.table_all = QTableWidget()
        self.table_all.setColumnCount(12)
        self.table_all.setHorizontalHeaderLabels([
            "Name", "Day", "Month", "Year", "Country", "State", "District", "Remarks", "Relation", "Phone", "Edit", "Delete"
        ])
        self.table_all.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_all.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.table_all)
        self.pages_container.addWidget(page)
        self.refresh_page3_data()

    def refresh_page3_data(self):
        records = self.db.get_all_ordered_by_name()
        self.table_all.setRowCount(len(records))
        
        for idx, row in enumerate(records):
            for col_idx in range(1, 11):
                val = row[col_idx]
                item_str = "" if val is None else str(val)
                self.table_all.setItem(idx, col_idx - 1, QTableWidgetItem(item_str))
            
            edit_btn = QPushButton("Edit")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.setStyleSheet("""
                QPushButton { background-color: #161616; border: 1px solid #333333; color: #5B9BD5; padding: 2px; font-size: 11px; }
                QPushButton:hover { background-color: #5B9BD5; color: #000000; font-weight: bold; }
            """)
            edit_btn.clicked.connect(lambda checked, r=row: self.edit_record_action(r))
            self.table_all.setCellWidget(idx, 10, edit_btn)

            delete_btn = QPushButton("Delete")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setStyleSheet("""
                QPushButton { background-color: #161616; border: 1px solid #333333; color: #FF5F56; padding: 2px; font-size: 11px; }
                QPushButton:hover { background-color: #FF5F56; color: #FFFFFF; font-weight: bold; }
            """)
            delete_btn.clicked.connect(lambda checked, row_id=row[0], name=row[1]: self.delete_record_action(row_id, name))
            self.table_all.setCellWidget(idx, 11, delete_btn)

    def edit_record_action(self, row_data):
        dialog = EditRecordDialog(self, row_data, self.months)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_form_values()
            
            if not values[0] or not values[1]:
                QMessageBox.warning(self, "Validation Error", "Name and Day fields remain structural requirements.")
                return
            try:
                day = int(values[1])
                if not (1 <= day <= 31): raise ValueError
            except ValueError:
                QMessageBox.warning(self, "Validation Error", "Day integer parameter must track between 1-31.")
                return
                
            year = None
            if values[3]:
                try: year = int(values[3])
                except ValueError:
                    QMessageBox.warning(self, "Validation Error", "Year expression format invalid.")
                    return

            processed_pack = (values[0], day, values[2], year, values[4], values[5], values[6], values[7], values[8], values[9])
            self.db.update_birthday(row_data[0], processed_pack)
            self.refresh_page3_data()

    def delete_record_action(self, row_id, name):
        confirm = QMessageBox.question(
            self, "Verify Intent", 
            f"Are you completely sure you want to drop the profile tracking record belonging to: {name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.db.delete_birthday(row_id)
            self.refresh_page3_data()

    def import_database(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Source Ledger Update Packet", "", "CSV Storage Sheets (*.csv)")
        if file_path:
            try:
                self.db.import_from_csv(file_path)
                QMessageBox.information(self, "Success", "External data packet merged into default registry structures successfully.")
                self.refresh_page3_data()
            except Exception as err:
                QMessageBox.critical(self, "System Execution Error", f"Data stream structural parser error context: {str(err)}")

    def export_database(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Target Export Ledger Workspace", "Birthday_Export.csv", "CSV Storage Sheets (*.csv)")
        if file_path:
            try:
                self.db.export_to_csv(file_path)
                QMessageBox.information(self, "Success", f"System Registry ledger written to storage destination target address location:\n{file_path}")
            except Exception as err:
                QMessageBox.critical(self, "System Execution Error", f"File System operation failure exception trace: {str(err)}")


    # --- PAGE 4: LEGAL LICENSE & DEVELOPER REGISTRY ---
    def setup_page4(self):
        """Builds a detailed open-source legal license framework protecting the creator from liabilities."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        title = QLabel("Legal Architecture & License")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        layout.addWidget(title)

        credit_card = QWidget()
        credit_card.setStyleSheet("background-color: #111111; border: 1px solid #222222; border-radius: 8px; padding: 20px;")
        card_layout = QVBoxLayout(credit_card)

        creator_label = QLabel("Author & Creator: Ayrish Jose")
        creator_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        creator_label.setStyleSheet("color: #FFFFFF; border: none;")
        
        purpose_label = QLabel("Purpose: Open Source Non-Commercial Educational Software Sandbox")
        purpose_label.setFont(QFont("Segoe UI", 12))
        purpose_label.setStyleSheet("color: #888888; border: none; padding-top: 4px;")

        contact_label = QLabel("Official Contact Registry: https://in.linkedin.com/in/ayrish-jose-881041199")
        contact_label.setFont(QFont("Segoe UI", 12))
        contact_label.setStyleSheet("color: #5B9BD5; border: none; padding-top: 4px;")

        card_layout.addWidget(creator_label)
        card_layout.addWidget(purpose_label)
        card_layout.addWidget(contact_label)
        layout.addWidget(credit_card)

        license_title = QLabel("Detailed Open-Source Disclaimer Agreement")
        license_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        license_title.setStyleSheet("color: #AAAAAA; margin-top: 10px;")
        layout.addWidget(license_title)

        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setStyleSheet("""
            QTextEdit {
                background-color: #0F0F0F;
                border: 1px solid #222222;
                border-radius: 6px;
                color: #A0A0A0;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                line-height: 1.5;
                padding: 15px;
            }
        """)
        
        comprehensive_license = (
            "DETAILED EDUCATIONAL OPEN-SOURCE LICENSE\n"
            "Copyright (c) 2026, Ayrish Jose. All Rights Reserved.\n"
            "--------------------------------------------------------------------------------\n\n"
            "1. GRANT OF LICENSE\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software application sandbox and associated documentation files, to "
            "use, modify, and distribute the program without restriction, subject explicitly "
            "to the terms, conditions, and strict liability disclaimers outlined below.\n\n"
            "2. LOCAL STORAGE ARCHITECTURE & DATA PRIVACY\n"
            "This software is designed as a standalone system layout. All database assets, registries, "
            "and sensitive personal profiles logged within this environment are kept and handled "
            "locally inside the application file framework via a local SQLite file database named "
            "['Birthday_Recorder.db']. No operational streams, data records, or backend assets are "
            "transmitted to external hosting cloud spaces or third-party servers by the author.\n\n"
            "3. ABSOLUTE WAIVER OF WARRANTY AND GUARANTEE\n"
            "THE SOFTWARE IS PROVIDED 'AS IS' AND 'WITH ALL FAULTS', WITHOUT WARRANTY OR GUARANTEE "
            "OF ANY KIND, EXPRESSED OR IMPLIED. THE AUTHOR DISCLAIMS ALL WARRANTIES, INCLUDING "
            "BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, SECURITY, PERFORMANCE, STABILITY, "
            "ACCURACY, AND FITNESS FOR A PARTICULAR PURPOSE.\n\n"
            "4. NO RECOURSE & ZERO TECHNICAL SUPPORT STATUS\n"
            "UNDER NO CIRCUMSTANCES SHALL THE CREATOR (AYRISH JOSE) PROVIDE FUNCTIONAL MAINTENANCE, "
            "TECHNICAL ASSISTANCE, SERVER FIXES, UPGRADES, BUG REFACTORING, OR CUSTOMER SUPPORT "
            "OF ANY KIND TO USERS OR DISTRIBUTORS. SYSTEM INTEGRITY AND CODE OPERATION REMAIN THE "
            "SOLE RESPONSIBILITY OF THE RUNNING PARTY.\n\n"
            "5. INDEMNIFICATION & COMPLETE PROTECTIVE LIABILITY SHIELD\n"
            "IN NO EVENT SHALL THE AUTHOR, CREATOR, OR COPYRIGHT HOLDER (AYRISH JOSE) BE LIABLE FOR "
            "ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, PUNITIVE, OR CONSEQUENTIAL "
            "DAMAGES, LOSSES, OR THREATS (INCLUDING, BUT NOT LIMITED TO, DATA CORRUPTION, SYSTEM "
            "FAILURES, UNAUTHORIZED DATA EXPOSURE, SECURITY INTENSITIES, OS CONFLICTS, OR HOSTILE "
            "USER TAMPERING) ARISING IN ANY WAY OUT OF THE USE, OPERATION, REPRODUCTION, OR "
            "MISUSE OF THIS SOFTWARE BY ANY OTHER USERS, EVEN IF ADVISED OF THE POSSIBILITY OF "
            "SUCH DAMAGE.\n\n"
            "BY RUNNING, HOSTING, OR RETAINING THIS SCRIPT ENGINE, YOU ACKNOWLEDGE AND EXPRESSLY "
            "AGREE TO INDEMNIFY AND HOLD HARMLESS THE AUTHOR FROM ALL THREATS, ACTIONS, CLAIMS, "
            "OR LIABILITIES GENERATED BY COMPONENT DEPLOYMENTS OR RUNTIME MISUSE."
        )
        license_text.setText(comprehensive_license)
        layout.addWidget(license_text)

        self.pages_container.addWidget(page)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BirthdayApp()
    window.show()
    sys.exit(app.exec())