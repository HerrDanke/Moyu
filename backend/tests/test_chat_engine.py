from __future__ import annotations

import pytest

from app.services.chat_engine import parse_intent


@pytest.mark.parametrize(
    "text,kind",
    [
        ("下一章", "next"),
        ("下章", "next"),
        ("继续", "next"),
        # 「继续读」属于 next，不属于 resume —— 这是新增 resume 意图时必须守住的边界
        ("继续读", "next"),
        ("再来", "next"),
        ("上一章", "prev"),
        ("返回", "prev"),
        ("继续本章", "resume"),
        ("续读本章", "resume"),
        ("接着读", "resume"),
        ("第 20 章", "goto"),
        ("跳到 5", "goto"),
        ("到第3章", "goto"),
        ("书单", "list_books"),
        ("有哪些书", "list_books"),
        ("读《凡人修仙传》", "switch_book"),
        ("换书 凡人", "switch_book"),
        ("搜 韩立", "search"),
        ("有韩立吗", "search"),
        ("帮助", "help"),
        ("你能干嘛", "help"),
        ("今天天气不错", "fallback"),
        ("", "fallback"),
    ],
)
def test_parse_intent(text, kind):
    assert parse_intent(text).kind == kind


def test_goto_extracts_number():
    assert parse_intent("第 128 章").number == 128


def test_input_truncation_is_safe():
    # 超长畸形输入不崩溃、不超时（正则线性）
    weird = "第" + "9" * 5000 + "章"
    intent = parse_intent(weird, max_chars=500)
    assert intent.kind in {
        "goto",
        "fallback",
        "search",
        "switch_book",
        "next",
        "prev",
        "resume",
        "help",
        "list_books",
    }