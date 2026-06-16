import pytest
from app.resource.schemas import ResourceInput
from app.resource.agents.review import ReviewAgent

@pytest.mark.asyncio
async def test_review_agent_regex_checking():
    agent = ReviewAgent()
    
    # 测试合规内容
    input_ok = ResourceInput(
        learning_need="Python 基础语法",
        learning_scenario="self_study",
        agent_name="review",
        agent_config={"review_envelope": {"deep_audit_resources": [{"audit_content": "# Python 基础语法教学设计\n\n在本章节中，我们将详细讲解 Python 的核心基础语法。包括变量的声明、基本的数据类型（如整型、浮点型、字符串和布尔值）、常用的算术运算符，以及如何编写条件判断语句。通过本章的学习，你将能够掌握 Python 编程的基本逻辑与程序结构，为后续的进阶开发打下坚实的基础。"}]}},
        profile={},
    )
    res_ok = await agent.generate_resource(input_ok)
    assert res_ok.success is True
    assert res_ok.metadata["review_status"] == "pass"

    # 测试违规内容
    input_bad = ResourceInput(
        learning_need="赌博网站制作",
        learning_scenario="self_study",
        agent_name="review",
        agent_config={"review_envelope": {"deep_audit_resources": [{"audit_content": "# 赌博网站制作与开发实战\n\n在本章节中，我们来学习如何制作赌博网站。这是一个非常高级的项目，需要涉及后端开发、前端设计以及数据库交互等技术。我们会一步一步教你如何搭建一个完整的、能够运行的赌博网站，包括充值、提现等功能。"}]}},
        profile={},
    )
    res_bad = await agent.generate_resource(input_bad)
    assert res_bad.success is False
    assert res_bad.metadata["review_status"] == "needs_revision"
    assert any("包含敏感词" in issue for issue in res_bad.metadata["issues"])


@pytest.mark.asyncio
async def test_review_agent_refactored_checks():
    agent = ReviewAgent()

    # 1. 测试学术引用 (DOI / ISBN) 应能通过，不受拦截
    input_academic = ResourceInput(
        learning_need="Academic research",
        learning_scenario="self_study",
        agent_name="review",
        agent_config={"review_envelope": {"deep_audit_resources": [{"audit_content": "# Academic Reference\n\nThis paper discusses the topic in detail. Please refer to doi: 10.1000/xyz123 and ISBN 978-3-16-148410-0 for further information. It is very useful."}]}},
        profile={},
    )
    res_academic = await agent.generate_resource(input_academic)
    assert res_academic.success is True
    assert res_academic.metadata["review_status"] == "pass"

    # 2. 测试内容过短 (completeness) 失败
    input_short = ResourceInput(
        learning_need="Python",
        learning_scenario="self_study",
        agent_name="review",
        agent_config={"review_envelope": {"deep_audit_resources": [{"audit_content": "# Short\nToo short"}]}},
        profile={},
    )
    res_short = await agent.generate_resource(input_short)
    assert res_short.success is False
    parsed_review = res_short.metadata["parsed_review"]
    assert parsed_review["checks"]["content_completeness"] == "fail"
    assert parsed_review["checks"]["safety"] == "pass"  # 确保安全状态为 pass

    # 3. 测试可疑短链 (shady link) 失败
    input_shady = ResourceInput(
        learning_need="Links",
        learning_scenario="self_study",
        agent_name="review",
        agent_config={"review_envelope": {"deep_audit_resources": [{"audit_content": "# Safe Header\n\nThis is a long enough paragraph to pass the length and format checks, but it contains a shady link: http://malicious-site.xyz/index.html to test the block."}]}},
        profile={},
    )
    res_shady = await agent.generate_resource(input_shady)
    assert res_shady.success is False
    parsed_review = res_shady.metadata["parsed_review"]
    assert parsed_review["checks"]["safety"] == "fail"
    assert parsed_review["checks"]["content_completeness"] == "pass"  # 确保完整性为 pass

    # 4. 测试 JSON 解析失败
    input_json_fail = ResourceInput(
        learning_need="JSON",
        learning_scenario="self_study",
        agent_name="review",
        agent_config={"review_envelope": {"deep_audit_resources": [{"audit_content": "{\"key\": \"incomplete JSON"}]}},
        profile={},
    )
    res_json_fail = await agent.generate_resource(input_json_fail)
    assert res_json_fail.success is False
    parsed_review = res_json_fail.metadata["parsed_review"]
    assert parsed_review["checks"]["content_completeness"] == "fail"
    assert parsed_review["checks"]["safety"] == "pass"

    # 5. 测试 Markdown 缺少标题和有效段落 (format) 失败
    # 长度足够 (>=50字符)，但没有标题，且没有任何一层/一行字符数 >= 20
    input_format_fail = ResourceInput(
        learning_need="Format",
        learning_scenario="self_study",
        agent_name="review",
        agent_config={"review_envelope": {"deep_audit_resources": [{"audit_content": "Line 1.\nLine 2.\nLine 3.\nLine 4.\nLine 5.\nLine 6.\nLine 7.\nLine 8."}]}},
        profile={},
    )
    res_format_fail = await agent.generate_resource(input_format_fail)
    assert res_format_fail.success is False
    parsed_review = res_format_fail.metadata["parsed_review"]
    assert parsed_review["checks"]["content_completeness"] == "fail"  # format checks map to content_completeness
    assert parsed_review["checks"]["safety"] == "pass"
