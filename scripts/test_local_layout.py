#!/usr/bin/env python3
"""local/index.html 이 데모와 같은 2열 레이아웃(aside.side + main.main)을 쓰는지 검증."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL_HTML = (ROOT / "local" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "css" / "style.css").read_text(encoding="utf-8")


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = {"tag": "#document", "id": None, "class": [], "children": []}
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        node = {
            "tag": tag,
            "id": d.get("id"),
            "class": (d.get("class") or "").split(),
            "children": [],
        }
        self.stack[-1]["children"].append(node)
        if tag not in {"br", "img", "input", "meta", "link", "hr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                break


def find(node, pred, acc=None):
    if acc is None:
        acc = []
    if pred(node):
        acc.append(node)
    for c in node.get("children") or []:
        find(c, pred, acc)
    return acc


def parent_of(root, target):
    stack = [(root, None)]
    while stack:
        node, parent = stack.pop()
        if node is target:
            return parent
        for c in node.get("children") or []:
            stack.append((c, node))
    return None


def ancestor_has(root, node, pred):
    p = parent_of(root, node)
    while p is not None:
        if pred(p):
            return True
        p = parent_of(root, p)
    return False


def test_side_and_main_exist():
    tree = TreeBuilder()
    tree.feed(LOCAL_HTML)
    sides = find(tree.root, lambda n: n["tag"] == "aside" and "side" in n["class"])
    mains = find(tree.root, lambda n: n["tag"] == "main" and "main" in n["class"])
    assert sides, "local/index.html 에 <aside class='side'> 가 있어야 한다"
    assert mains, "local/index.html 에 <main class='main'> 가 있어야 한다"


def test_views_and_topbar_live_inside_main():
    tree = TreeBuilder()
    tree.feed(LOCAL_HTML)
    for vid in ("view-dashboard", "view-pm", "view-dev", "view-infra", "view-qa", "view-ops"):
        nodes = find(tree.root, lambda n, i=vid: n.get("id") == i)
        assert nodes, f"#{vid} 가 없다"
        assert ancestor_has(
            tree.root, nodes[0], lambda n: n["tag"] == "main" and "main" in n["class"]
        ), f"#{vid} 는 <main class='main'> 안에 있어야 한다"
    topbars = find(tree.root, lambda n: "topbar" in n["class"])
    assert topbars, ".topbar 가 없다"
    assert ancestor_has(
        tree.root, topbars[0], lambda n: n["tag"] == "main" and "main" in n["class"]
    ), ".topbar 는 <main class='main'> 안에 있어야 한다"


def test_nav_buttons_live_inside_side():
    tree = TreeBuilder()
    tree.feed(LOCAL_HTML)
    navs = find(tree.root, lambda n: "navbtn" in n["class"])
    assert len(navs) >= 8, f"사이드바 navbtn 이 부족하다: {len(navs)}"
    for n in navs:
        assert ancestor_has(
            tree.root, n, lambda x: x["tag"] == "aside" and "side" in x["class"]
        ), "navbtn 은 <aside class='side'> 안에 있어야 한다"


def test_no_flex_layout_override():
    compact = "".join(LOCAL_HTML.split())
    assert "body.team-hub{display:flex" not in compact, (
        "body.team-hub display:flex 오버라이드는 2열 그리드를 깨뜨린다"
    )


def test_css_media_query_closes_cleanly():
    assert "||}" not in CSS, "css/style.css 미디어쿼리 닫힘이 '||}' 로 깨져 있다"


if __name__ == "__main__":
    tests = [
        test_side_and_main_exist,
        test_views_and_topbar_live_inside_main,
        test_nav_buttons_live_inside_side,
        test_no_flex_layout_override,
        test_css_media_query_closes_cleanly,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    if failed:
        raise SystemExit(failed)
    print("all ok")
