from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from modules.quiz_exporter.word_renderer import ExamMeta, ExportConfig
from ui.views import quiz_builder_batch


class _DummySpin:
	def __init__(self, value: int) -> None:
		self._value = value

	def value(self) -> int:
		return self._value


class _DummyCheck:
	def __init__(self, checked: bool) -> None:
		self._checked = checked

	def isChecked(self) -> bool:
		return self._checked


class _DummyExportPanel:
	def validate_required_fields(self) -> str | None:
		return None

	def build_meta(self, *, duration_minutes: int) -> ExamMeta:
		return ExamMeta(exam_title="De Kiem Tra", duration_minutes=duration_minutes)

	def build_render_config(self) -> ExportConfig:
		return ExportConfig()


class _DummySelector:
	def build_snapshots(self, questions, shuffle_options: bool = True):
		_ = (questions, shuffle_options)
		return [
			{
				"type": "MC",
				"content": "Noi dung cau hoi",
				"point_value": 1.0,
				"options": [
					{"key": "A", "text": "Dap an A", "is_correct": True},
					{"key": "B", "text": "Dap an B", "is_correct": False},
				],
				"accepted_answers": [],
			}
		]


class _DummyDoc:
	def save(self, path: Path) -> None:
		Path(path).write_text("dummy", encoding="utf-8")


class _DummyRenderer:
	def render(self, *_args, **_kwargs):
		return _DummyDoc()


class _DummyView:
	def __init__(self) -> None:
		self._exam_count_spin = _DummySpin(2)
		self._count_spin = _DummySpin(1)
		self._duration_spin = _DummySpin(30)
		self._cb_no_repeat_between_exams = _DummyCheck(False)
		self._cb_shuffle_opts = _DummyCheck(True)
		self._export_panel = _DummyExportPanel()
		self._selector = _DummySelector()
		self._chapter_spins = {}
		self._type_spins = {}
		self._clo_spins = {}

	def _current_bank_id(self):
		return 1

	def _eligible_questions(self):
		return [SimpleNamespace(id=101), SimpleNamespace(id=102), SimpleNamespace(id=103)]

	def _quota_dict(self, _spins):
		return {}

	def _refresh_quota_warnings(self, _questions):
		return None


def test_run_batch_generation_creates_multiple_files(tmp_path, monkeypatch):
	view = _DummyView()
	generated_info_messages: list[str] = []

	monkeypatch.setattr(
		quiz_builder_batch.QFileDialog,
		"getExistingDirectory",
		lambda *_args, **_kwargs: str(tmp_path),
	)
	monkeypatch.setattr(
		quiz_builder_batch.QMessageBox,
		"warning",
		lambda *_args, **_kwargs: None,
	)
	monkeypatch.setattr(
		quiz_builder_batch.QMessageBox,
		"critical",
		lambda *_args, **_kwargs: None,
	)

	def _capture_information(_parent, _title, text, *args, **kwargs):
		_ = (args, kwargs)
		generated_info_messages.append(text)
		return None

	monkeypatch.setattr(
		quiz_builder_batch.QMessageBox,
		"information",
		_capture_information,
	)
	monkeypatch.setattr(
		quiz_builder_batch,
		"WordRenderer",
		_DummyRenderer,
	)
	monkeypatch.setattr(
		quiz_builder_batch,
		"build_inventory",
		lambda _questions: SimpleNamespace(),
	)
	monkeypatch.setattr(
		quiz_builder_batch,
		"validate_quota_plan",
		lambda _plan, _inv: SimpleNamespace(is_valid=True, errors=[]),
	)
	monkeypatch.setattr(
		quiz_builder_batch,
		"diagnose_quota_infeasibility",
		lambda *_args, **_kwargs: [],
	)

	call_count = {"n": 0}

	def _fake_allocate(_questions, _plan, excluded_question_ids=None):
		_ = excluded_question_ids
		call_count["n"] += 1
		return [SimpleNamespace(id=100 + call_count["n"])]

	monkeypatch.setattr(
		quiz_builder_batch,
		"allocate_questions_for_plan",
		_fake_allocate,
	)
	monkeypatch.setattr(quiz_builder_batch.os, "startfile", lambda *_args: None, raising=False)

	quiz_builder_batch.run_batch_generation(view)

	generated_files = list(tmp_path.rglob("*.docx"))
	assert len(generated_files) == 2
	assert any("Đã tạo 2 đề" in msg for msg in generated_info_messages)
