from __future__ import annotations

from modules.quiz_runner.timer_controller import QuizTimerController


def test_timer_controller_emits_tick_and_time_up() -> None:
    controller = QuizTimerController()
    ticks: list[int] = []
    time_up_calls = 0

    controller.tick.connect(lambda remaining: ticks.append(remaining))

    def _mark_time_up() -> None:
        nonlocal time_up_calls
        time_up_calls += 1

    controller.time_up.connect(_mark_time_up)

    controller.start(2)
    controller._on_tick()
    controller._on_tick()

    assert ticks == [1, 0]
    assert time_up_calls == 1
    assert controller.elapsed_seconds == 2
    assert controller.is_active() is False


def test_timer_controller_stop() -> None:
    controller = QuizTimerController()
    controller.start(5)
    controller.stop()
    assert controller.is_active() is False
