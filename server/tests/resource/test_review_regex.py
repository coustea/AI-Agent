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
