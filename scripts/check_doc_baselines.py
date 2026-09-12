#!/usr/bin/env python3
"""守卫：文档里声称的数字必须与代码/规格的真实状态一致。

## 为什么存在

曾经出现过这类漂移：加完两条后端测试后忘记回改文档基线，README / HANDOFF / AGENTS.md
都还写着旧数字。**没有任何测试会抓这种错**，只能靠人记得——于是把它变成一个会自动失败的检查。

## 设计约束

- **零依赖**（仅标准库）：CI 里不需要 `pip install` / `npm ci`，跑一次约一两秒。
- **宁可吵闹地失败，也不猜**：遇到无法确定计数的构造（非字面量 parametrize、`it.each`、
  fixture 级参数化、测试类……）会报错退出，而不是给出一个假的「一致」。
- **文档措辞变了也要失败**：每条声称都用正则精确匹配，且要求**恰好命中一次**。
  否则改写文档会让检查静默失效——那比没有检查更危险。

用法：
    python scripts/check_doc_baselines.py
退出码：0 = 全部一致；1 = 有不一致或无法判定。
"""
from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Windows 控制台默认是 GBK，直接打印非 GBK 字符会抛 UnicodeEncodeError 而中断检查。
# 这个脚本要在任何 CI / 终端里都能跑完，所以兜一下。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent

# —— 文档中所有「声称的数字」。——
# 每条都必须**恰好命中一次**，否则视为文档被改写、检查失效。
@dataclass(frozen=True)
class Claim:
    path: str
    pattern: str
    subject: str  # 这条声称对应哪个真实计数


CLAIMS: tuple[Claim, ...] = (
    Claim("README.md", r"# 后端（(\d+) passed 为基线）", "pytest"),
    Claim("README.md", r"# 前端单元测试 \+ 生产构建（(\d+) passed 为基线）", "vitest"),
    Claim("README.md", r"# 真实浏览器端到端（(\d+) passed 为基线", "playwright"),
    Claim("README.md", r"pytest（(\d+) 项：", "pytest"),
    Claim("docs/HANDOFF.md", r"# 后端（(\d+) passed 为基线）", "pytest"),
    Claim(
        "docs/HANDOFF.md",
        r"# 前端单元测试 \+ 生产构建（(\d+) passed \+ 构建成功为基线）",
        "vitest",
    ),
    Claim("docs/HANDOFF.md", r"# 真实浏览器端到端（(\d+) passed 为基线", "playwright"),
    Claim("AGENTS.md", r"# 全量（基线 (\d+) passed）", "pytest"),
    Claim("AGENTS.md", r"# vitest run（基线 (\d+) passed）", "vitest"),
)

HANDOFF = "docs/HANDOFF.md"


# ——————————————————————————————————————————————
# 真实计数
# ——————————————————————————————————————————————
def _parametrize_argvalues(dec: ast.expr) -> list | None:
    """取出 `@pytest.mark.parametrize("a,b", [...])` 的第二参；无法静态求值则返回 None。"""
    if not isinstance(dec, ast.Call):
        return None
    func = dec.func
    is_mark = (
        isinstance(func, ast.Attribute)
        and func.attr == "parametrize"
        or isinstance(func, ast.Name)
        and func.id == "parametrize"
    )
    if not is_mark:
        return None
    if len(dec.args) < 2:
        return None
    try:
        value = ast.literal_eval(dec.args[1])
    except (ValueError, SyntaxError):
        return None
    return list(value) if isinstance(value, (list, tuple)) else None


def count_pytest_tests() -> tuple[int | None, list[str]]:
    """静态统计 backend/tests 的用例数（含展开字面量 parametrize）。"""
    tests_dir = ROOT / "backend" / "tests"
    total = 0
    problems: list[str] = []

    for path in sorted(tests_dir.glob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            problems.append(f"{path.name}: 语法错误 {exc}")
            continue

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                # 只处理模块级函数；类里的用例需要换一套口径，交给人来改这个脚本
                if any(
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name.startswith("test_")
                    for item in node.body
                ):
                    problems.append(
                        f"{path.name}:{node.lineno} 出现测试类 {node.name}，本脚本只支持模块级用例"
                    )
                continue

            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue

            cases = 1
            for dec in node.decorator_list:
                if _is_parametrize_decorator(dec):
                    values = _parametrize_argvalues(dec)
                    if values is None:
                        problems.append(
                            f"{path.name}:{node.lineno} {node.name} 的 parametrize 无法静态展开"
                            f"（非字面量？），请改成字面量或更新本脚本"
                        )
                        continue
                    cases = len(values)
                if _declares_fixture_params(dec):
                    problems.append(
                        f"{path.name}:{node.lineno} 检测到 fixture 级 params，用例数无法静态确定"
                    )
            total += cases

    return (None if problems else total), problems


def _is_parametrize_decorator(dec: ast.expr) -> bool:
    if not isinstance(dec, ast.Call):
        return False
    func = dec.func
    return (isinstance(func, ast.Attribute) and func.attr == "parametrize") or (
        isinstance(func, ast.Name) and func.id == "parametrize"
    )


def _declares_fixture_params(dec: ast.expr) -> bool:
    if not isinstance(dec, ast.Call):
        return False
    func = dec.func
    is_fixture = (isinstance(func, ast.Attribute) and func.attr == "fixture") or (
        isinstance(func, ast.Name) and func.id == "fixture"
    )
    return is_fixture and any(kw.arg == "params" for kw in dec.keywords)


def count_vitest_tests() -> tuple[int | None, list[str]]:
    src = ROOT / "frontend" / "src"
    problems: list[str] = []
    total = 0

    for path in sorted(src.rglob("*.test.ts")) + sorted(src.rglob("*.test.tsx")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"\b(it|test|describe)\.each\s*\(", text):
            problems.append(f"{path.name}: 使用了 .each 参数化，用例数无法静态确定")
        total += len(re.findall(r"^\s*(?:it|test)\s*\(", text, re.MULTILINE))

    return (None if problems else total), problems


def count_playwright_tests() -> tuple[int | None, list[str]]:
    """统计 e2e 用例；排除 `_` 前缀文件（与 playwright.config.ts 的 testIgnore 一致）。"""
    e2e = ROOT / "frontend" / "e2e"
    problems: list[str] = []
    total = 0

    for path in sorted(e2e.glob("*.spec.ts")):
        if path.name.startswith("_"):
            continue  # 一次性工具/诊断脚本，不参与回归
        text = path.read_text(encoding="utf-8")
        if re.search(r"\btest\.(each|skip|fixme|fail)\s*\(", text):
            problems.append(f"{path.name}: 出现 test.each/skip/fixme/fail，用例数无法静态确定")
        total += len(re.findall(r"^\s*test\s*\(", text, re.MULTILINE))

    return (None if problems else total), problems


def _section(text: str, heading: str) -> str:
    """取出 `## heading` 到下一个同级标题之间的内容。"""
    start = text.index(heading)
    rest = text[start + len(heading) :]
    nxt = rest.find("\n## ")
    return rest if nxt == -1 else rest[:nxt]


def count_handoff_conventions() -> int:
    text = (ROOT / HANDOFF).read_text(encoding="utf-8")
    body = _section(text, "## 不可破坏的约定")
    return len(re.findall(r"^\d+\. ", body, re.MULTILINE))


def count_spec_capabilities() -> int:
    specs = ROOT / "openspec" / "specs"
    return sum(1 for d in specs.iterdir() if d.is_dir() and (d / "spec.md").is_file())


def find_spec_placeholders() -> list[str]:
    hits: list[str] = []
    for spec in sorted((ROOT / "openspec" / "specs").glob("*/spec.md")):
        for lineno, line in enumerate(spec.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"TBD|待定|TODO|FIXME", line):
                hits.append(f"openspec/specs/{spec.parent.name}/spec.md:{lineno} {line.strip()}")
    return hits


# ——————————————————————————————————————————————
# 校验
# ——————————————————————————————————————————————
@dataclass
class Result:
    ok: bool
    label: str
    detail: str


def check_claims(actual: dict[str, int | None], problems: list[str]) -> list[Result]:
    results: list[Result] = []
    for claim in CLAIMS:
        path = ROOT / claim.path
        text = path.read_text(encoding="utf-8")
        found = re.findall(claim.pattern, text)
        want = actual.get(claim.subject)

        if len(found) != 1:
            results.append(
                Result(
                    False,
                    f"{claim.path} · {claim.subject}",
                    f"正则命中 {len(found)} 次（要求恰好 1 次）：{claim.pattern!r}"
                    " —— 文档措辞被改过，检查已失效，请同步更新脚本里的正则",
                )
            )
            continue
        if want is None:
            results.append(
                Result(False, f"{claim.path} · {claim.subject}", "真实计数无法确定（见上方问题）")
            )
            continue
        if int(found[0]) != want:
            results.append(
                Result(
                    False,
                    f"{claim.path} · {claim.subject}",
                    f"文档写 {found[0]}，实际是 {want}",
                )
            )
            continue
        results.append(Result(True, f"{claim.path} · {claim.subject}", f"{want}"))
    return results


def main() -> int:
    actual: dict[str, int | None] = {}
    problems: list[str] = []

    pytest_n, p = count_pytest_tests()
    actual["pytest"] = pytest_n
    problems += p

    vitest_n, p = count_vitest_tests()
    actual["vitest"] = vitest_n
    problems += p

    pw_n, p = count_playwright_tests()
    actual["playwright"] = pw_n
    problems += p

    print("真实计数：")
    for name in ("pytest", "vitest", "playwright"):
        value = actual[name]
        print(f"  {name:<11} {value if value is not None else '无法确定'}")

    conventions = count_handoff_conventions()
    capabilities = count_spec_capabilities()
    placeholders = find_spec_placeholders()
    print(f"  HANDOFF 约定 {conventions} 条 / specs 能力 {capabilities} 个")
    print()

    results = check_claims(actual, problems)

    # 结构性一致性
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    m = re.findall(r"完整 (\d+) 条见", agents)
    if len(m) != 1:
        results.append(
            Result(False, "AGENTS.md · 约定条数引用", f"找不到唯一的「完整 N 条见」（命中 {len(m)} 次）")
        )
    elif int(m[0]) != conventions:
        results.append(
            Result(
                False,
                "AGENTS.md · 约定条数引用",
                f"写「完整 {m[0]} 条」，HANDOFF 实际有 {conventions} 条",
            )
        )
    else:
        results.append(Result(True, "AGENTS.md · 约定条数引用", f"{conventions} 条"))

    handoff = (ROOT / HANDOFF).read_text(encoding="utf-8")
    m = re.findall(r"openspec/specs/`（(\d+) 个能力", handoff)
    if len(m) != 1:
        results.append(
            Result(False, "HANDOFF · 能力数量", f"找不到唯一的「N 个能力」（命中 {len(m)} 次）")
        )
    elif int(m[0]) != capabilities:
        results.append(
            Result(False, "HANDOFF · 能力数量", f"写 {m[0]} 个，实际 {capabilities} 个目录")
        )
    else:
        results.append(Result(True, "HANDOFF · 能力数量", f"{capabilities} 个"))

    if placeholders:
        for hit in placeholders:
            results.append(Result(False, "specs 占位符", hit))
    else:
        results.append(Result(True, "specs 占位符", "无 TBD/待定/TODO"))

    print("检查结果：")
    failed = 0
    for r in results:
        mark = "OK  " if r.ok else "FAIL"
        if not r.ok:
            failed += 1
        print(f"  [{mark}] {r.label}")
        if not r.ok:
            print(f"         -> {r.detail}")

    if problems:
        print()
        print("无法判定的问题（守卫拒绝给出结论）：")
        for item in problems:
            print(f"  ! {item}")

    print()
    if failed == 0 and not problems:
        print(f"全部一致（{len(results)} 项检查通过）。")
        return 0
    print(f"发现 {failed + len(problems)} 个问题 —— 文档与代码不一致，或守卫无法判定。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
