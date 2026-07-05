from app.shared.video.director import select_style


def test_selects_precision_light_for_algorithmic_topics() -> None:
    decision = select_style("二分查找算法与数组指针移动", ["代码执行", "时间复杂度"])

    assert decision.id == "precision_light"


def test_selects_systems_dark_for_system_topics() -> None:
    decision = select_style("操作系统进程调度", ["状态转换", "CPU", "就绪队列"])

    assert decision.id == "systems_dark"


def test_selects_editorial_classroom_for_concept_topics() -> None:
    decision = select_style("面向对象基本概念", ["定义", "常见误区", "复习总结"])

    assert decision.id == "editorial_classroom"


def test_explicit_style_hint_wins() -> None:
    decision = select_style(
        "操作系统进程调度",
        ["CPU"],
        style_hint="editorial_classroom",
    )

    assert decision.id == "editorial_classroom"
