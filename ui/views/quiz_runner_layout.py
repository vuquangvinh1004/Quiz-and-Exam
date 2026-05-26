from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ui.styles import apply_checkbox_style
from ui.widgets.bank_combo import BankCombo


def build_setup_panel(view) -> QWidget:
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(60, 60, 60, 60)
    layout.setSpacing(10)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    view._setup_title = QLabel("Làm bài kiểm tra")
    view._setup_title.setStyleSheet("font-size: 21px; font-weight: bold;")
    layout.addWidget(view._setup_title)

    view._setup_info = QLabel(
        "Chọn ngân hàng, chế độ, giới hạn thời gian và bộ lọc câu hỏi, "
        "sau đó nhấn <b>Bắt đầu làm bài</b>."
    )
    view._setup_info.setTextFormat(Qt.TextFormat.RichText)
    view._setup_info.setWordWrap(True)
    view._setup_info.setStyleSheet("font-size: 15px; color: #444; line-height: 1.6;")
    layout.addWidget(view._setup_info)

    setup_box = QWidget()
    setup_form = QFormLayout(setup_box)

    view._setup_bank_combo = BankCombo()
    setup_form.addRow("Ngân hàng *:", view._setup_bank_combo)

    view._setup_mode_combo = QComboBox()
    view._setup_mode_combo.addItem("🎯 Kiểm tra", userData="EXAM")
    view._setup_mode_combo.addItem("📝 Luyện tập", userData="PRACTICE")
    view._setup_mode_combo.addItem("📚 Học tập", userData="STUDY")
    setup_form.addRow("Chế độ *:", view._setup_mode_combo)

    view._setup_time_spin = QSpinBox()
    view._setup_time_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    view._setup_time_spin.setRange(1, 999)
    view._setup_time_spin.setValue(30)
    view._setup_time_spin.setSuffix(" phút")
    view._setup_time_spin.setMinimumWidth(120)
    setup_form.addRow("Thời gian:", view._setup_time_spin)

    view._setup_count_spin = QSpinBox()
    view._setup_count_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    view._setup_count_spin.setRange(1, 500)
    view._setup_count_spin.setValue(10)
    view._setup_count_spin.setMinimumWidth(120)
    setup_form.addRow("Số câu hỏi:", view._setup_count_spin)

    types_row = QHBoxLayout()
    view._setup_cb_mc = QCheckBox("MC")
    view._setup_cb_ma = QCheckBox("MA")
    view._setup_cb_blank = QCheckBox("Blank")
    view._setup_cb_sa = QCheckBox("SA")
    apply_checkbox_style(view._setup_cb_mc, view._setup_cb_ma, view._setup_cb_blank, view._setup_cb_sa)
    for cb in (view._setup_cb_mc, view._setup_cb_ma, view._setup_cb_blank, view._setup_cb_sa):
        cb.setChecked(True)
        types_row.addWidget(cb)
    types_row.addStretch()
    types_widget = QWidget()
    types_widget.setLayout(types_row)
    setup_form.addRow("Loại:", types_widget)

    diff_row = QHBoxLayout()
    view._setup_cb_easy = QCheckBox("Easy")
    view._setup_cb_medium = QCheckBox("Medium")
    view._setup_cb_hard = QCheckBox("Hard")
    apply_checkbox_style(view._setup_cb_easy, view._setup_cb_medium, view._setup_cb_hard)
    for cb in (view._setup_cb_easy, view._setup_cb_medium, view._setup_cb_hard):
        cb.setChecked(True)
        diff_row.addWidget(cb)
    diff_row.addStretch()
    diff_widget = QWidget()
    diff_widget.setLayout(diff_row)
    setup_form.addRow("Độ khó:", diff_widget)

    misc_row = QHBoxLayout()
    view._setup_shuffle_q = QCheckBox("Trộn thứ tự câu")
    view._setup_shuffle_q.setChecked(True)
    view._setup_shuffle_opts = QCheckBox("Trộn đáp án (MC/MA)")
    view._setup_shuffle_opts.setChecked(True)
    apply_checkbox_style(view._setup_shuffle_q, view._setup_shuffle_opts)
    misc_row.addWidget(view._setup_shuffle_q)
    misc_row.addWidget(view._setup_shuffle_opts)
    misc_row.addStretch()
    misc_widget = QWidget()
    misc_widget.setLayout(misc_row)
    setup_form.addRow("Tùy chọn:", misc_widget)

    view._setup_pool_btn = QPushButton("Chọn pool câu hỏi")
    view._setup_pool_summary = QLabel("Đang dùng: tất cả câu hỏi phù hợp bộ lọc")
    pool_row = QHBoxLayout()
    pool_row.addWidget(view._setup_pool_btn)
    pool_row.addWidget(view._setup_pool_summary)
    pool_row.addStretch()
    pool_widget = QWidget()
    pool_widget.setLayout(pool_row)
    setup_form.addRow("Pool câu hỏi:", pool_widget)

    view._setup_available_lbl = QLabel("Sẵn có: 0 câu")
    setup_form.addRow("Khả dụng:", view._setup_available_lbl)

    layout.addWidget(setup_box)

    layout.addStretch()

    view._setup_start_btn = QPushButton("▶  Bắt đầu làm bài")
    view._setup_start_btn.setFixedHeight(48)
    view._setup_start_btn.setEnabled(False)
    view._setup_start_btn.setStyleSheet(
        "QPushButton { background: #27ae60; color: white; font-size: 16px; "
        "font-weight: bold; border-radius: 6px; }"
        "QPushButton:hover { background: #219150; }"
        "QPushButton:disabled { background: #aaa; }"
    )
    view._setup_start_btn.clicked.connect(view._on_start)
    layout.addWidget(view._setup_start_btn)
    return panel


def build_running_panel(view) -> QWidget:
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    header = QWidget()
    header.setObjectName("runner_header")
    header.setFixedHeight(52)
    header.setStyleSheet("#runner_header { background: #2c3e50; color: white; }")
    header_hl = QHBoxLayout(header)
    header_hl.setContentsMargins(16, 0, 16, 0)

    view._header_title = QLabel("Bài kiểm tra")
    view._header_title.setStyleSheet("color: white; font-size: 15px; font-weight: bold;")
    header_hl.addWidget(view._header_title, stretch=1)

    view._timer_label = QLabel("⏱ --:--")
    view._timer_label.setStyleSheet("color: #f1c40f; font-size: 15px; font-weight: bold;")
    header_hl.addWidget(view._timer_label)

    view._progress_label = QLabel("Câu 0 / 0")
    view._progress_label.setStyleSheet("color: #ecf0f1; font-size: 14px; padding-left: 16px;")
    header_hl.addWidget(view._progress_label)
    layout.addWidget(header)

    view._submitter_bar = QWidget()
    view._submitter_bar.setStyleSheet("background: #ecf0f1; padding: 2px 16px;")
    sb_hl = QHBoxLayout(view._submitter_bar)
    sb_hl.setContentsMargins(16, 4, 16, 4)
    view._submitter_info_label = QLabel()
    view._submitter_info_label.setStyleSheet("font-size: 13px; color: #555;")
    sb_hl.addWidget(view._submitter_info_label)
    sb_hl.addStretch()
    layout.addWidget(view._submitter_bar)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    view._question_area = QWidget()
    q_layout = QVBoxLayout(view._question_area)
    q_layout.setContentsMargins(32, 24, 32, 16)
    q_layout.setSpacing(10)

    view._question_num = QLabel()
    view._question_num.setStyleSheet("color: #888; font-size: 13px;")
    q_layout.addWidget(view._question_num)

    view._question_label = QLabel()
    view._question_label.setWordWrap(True)
    view._question_label.setTextFormat(Qt.TextFormat.RichText)
    view._question_label.setStyleSheet("font-size: 16px; line-height: 1.5;")
    q_layout.addWidget(view._question_label)

    view._hint_label = QLabel()
    view._hint_label.setWordWrap(True)
    view._hint_label.setStyleSheet(
        "font-size: 14px; color: #8e44ad; padding: 8px; "
        "background: #f5eef8; border-radius: 4px;"
    )
    view._hint_label.hide()
    q_layout.addWidget(view._hint_label)

    view._answer_renderer.attach(q_layout)

    view._feedback_label = QLabel()
    view._feedback_label.setWordWrap(True)
    view._feedback_label.setStyleSheet("font-size: 14px; padding: 8px; border-radius: 4px;")
    view._feedback_label.hide()
    q_layout.addWidget(view._feedback_label)

    view._confirm_btn = QPushButton("✓  Xác nhận câu này")
    view._confirm_btn.setFixedHeight(36)
    view._confirm_btn.setStyleSheet(
        "QPushButton { background: #27ae60; color: white; "
        "border-radius: 4px; font-weight: bold; padding: 0 16px; }"
        "QPushButton:hover { background: #219150; }"
        "QPushButton:disabled { background: #aaa; }"
    )
    view._confirm_btn.clicked.connect(view._on_confirm_study)
    view._confirm_btn.hide()
    q_layout.addWidget(view._confirm_btn)

    q_layout.addStretch()
    scroll.setWidget(view._question_area)
    layout.addWidget(scroll, stretch=1)

    nav_bar = QWidget()
    nav_bar.setStyleSheet("background: #f8f9fa; border-top: 1px solid #dee2e6;")
    nav_hl = QHBoxLayout(nav_bar)
    nav_hl.setContentsMargins(16, 8, 16, 8)

    view._prev_btn = QPushButton("← Câu trước")
    view._prev_btn.clicked.connect(view._on_prev)
    nav_hl.addWidget(view._prev_btn)

    nav_hl.addStretch()

    view._submit_btn = QPushButton("Nộp bài")
    view._submit_btn.setFixedHeight(40)
    view._submit_btn.setStyleSheet(
        "QPushButton { background: #e74c3c; color: white; font-weight: bold; "
        "border-radius: 4px; padding: 0 20px; }"
        "QPushButton:hover { background: #c0392b; }"
    )
    view._submit_btn.clicked.connect(view._on_submit_clicked)
    nav_hl.addWidget(view._submit_btn)

    view._next_btn = QPushButton("Câu tiếp →")
    view._next_btn.clicked.connect(view._on_next)
    nav_hl.addWidget(view._next_btn)

    layout.addWidget(nav_bar)
    return panel


def build_done_panel(view) -> QWidget:
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(60, 80, 60, 60)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    view._done_label = QLabel("✓ Đã hoàn thành bài.")
    view._done_label.setStyleSheet("font-size: 19px; font-weight: bold;")
    layout.addWidget(view._done_label)

    view._done_summary = QLabel()
    view._done_summary.setWordWrap(True)
    view._done_summary.setTextFormat(Qt.TextFormat.RichText)
    view._done_summary.setStyleSheet("font-size: 15px; color: #444;")
    layout.addWidget(view._done_summary)

    restart_btn = QPushButton("Tạo bài kiểm tra mới")
    restart_btn.setFixedHeight(40)
    restart_btn.clicked.connect(view._reset_to_setup)
    layout.addWidget(restart_btn)
    layout.addStretch()
    return panel
