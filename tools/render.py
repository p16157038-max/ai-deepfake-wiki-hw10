"""Deterministically render approved teaching text as a self-contained HTML deck.

No model calls, source retrieval, or content generation occur here. Importing this
module never renders anything. The Wiki and at least one saved query must already
exist before render_deck(root) can write deck.html.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import quote


SLIDE_TYPES = {
    "cover", "goals", "concept", "flow", "case", "quiz", "comparison", "steps", "closing"
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def string(value, context: str, *, required=False) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f"{context} must be {'a nonempty' if required else 'a'} string")
    return value


def string_list(value, context: str):
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{context} must be a list of strings")
    return value


def wiki_path(value: str) -> str:
    value = string(value, "citation.wiki", required=True)
    path = PurePosixPath(value)
    if "\\" in value or path.is_absolute() or ".." in path.parts or path.suffix.lower() != ".md":
        raise ValueError(f"Citation must be a relative Markdown path inside wiki/: {value}")
    if any(mark in value for mark in ("?", "#", ":")):
        raise ValueError(f"Citation path cannot contain a query, fragment, or scheme: {value}")
    return path.as_posix()


def load_catalog(root: Path):
    path = root / "wiki/catalog.json"
    if not path.exists():
        return {}
    data = read_json(path)
    pages = data.get("pages", []) if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError("wiki/catalog.json must contain a pages list")
    return {str(page["path"]): page for page in pages if isinstance(page, dict) and page.get("path")}


def content_gate(root: Path):
    for name in ("wiki/index.md", "wiki/log.md"):
        path = root / name
        if not path.is_file() or not path.read_text(encoding="utf-8-sig").strip():
            raise ValueError(f"Complete the real Wiki before rendering: missing or empty {name}")
    query_files = sorted((root / "queries").glob("*.json"))
    actual_query = False
    for path in query_files:
        data = read_json(path)
        if isinstance(data, dict) and data.get("question") and data.get("pages") and data.get("answer"):
            actual_query = True
            break
    if not actual_query:
        raise ValueError("Save at least one actual Wiki query JSON with question, pages, and answer before rendering")


def validate_slides(root: Path, slides, catalog):
    if not isinstance(slides, list) or len(slides) != 14:
        raise ValueError("The approved deck must contain exactly 14 slides")
    seen = set()
    quiz_count = 0
    for number, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            raise ValueError(f"Slide {number} must be an object")
        sid = string(slide.get("id"), f"Slide {number} id", required=True)
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", sid) or sid in seen:
            raise ValueError(f"Slide IDs must be unique safe HTML identifiers: {sid}")
        seen.add(sid)
        if slide.get("type", "concept") not in SLIDE_TYPES:
            raise ValueError(f"Unsupported slide type on {sid}")
        string(slide.get("title"), f"{sid}.title", required=True)
        string(slide.get("lead"), f"{sid}.lead")
        string(slide.get("note"), f"{sid}.note")
        string_list(slide.get("bullets"), f"{sid}.bullets")
        for field in ("items", "chat"):
            value = slide.get(field, [])
            if not isinstance(value, list):
                raise ValueError(f"{sid}.{field} must be a list")
            for item in value:
                if not isinstance(item, dict):
                    raise ValueError(f"Each {sid}.{field} item must be an object")
                for key in (("title", "text") if field == "items" else ("sender", "text")):
                    string(item.get(key), f"{sid}.{field}.{key}")
        citations = slide.get("citations")
        if not isinstance(citations, list) or not citations:
            raise ValueError(f"Every slide needs an approved Wiki citation: {sid}")
        for citation in citations:
            if not isinstance(citation, dict):
                raise ValueError(f"{sid}.citations must contain objects")
            relative = wiki_path(citation.get("wiki"))
            target = (root / "wiki" / relative).resolve()
            if not target.is_relative_to((root / "wiki").resolve()) or not target.is_file():
                raise ValueError(f"Missing Wiki citation target on {sid}: {relative}")
            claims = string_list(citation.get("claims"), f"{sid}.citation.claims")
            if not claims:
                raise ValueError(f"Citations must identify approved claim IDs on {sid}")
            source_text = target.read_text(encoding="utf-8-sig")
            page = catalog.get(relative)
            known = {str(claim.get("id")) for claim in page.get("claims", []) if isinstance(claim, dict)} if page else set()
            for claim in claims:
                if claim not in source_text and claim not in known:
                    raise ValueError(f"Claim {claim} does not exist in cited Wiki page {relative}")
            string(citation.get("label"), f"{sid}.citation.label")
        if slide.get("quiz") is not None:
            quiz_count += 1
            quiz = slide["quiz"]
            if not isinstance(quiz, dict):
                raise ValueError(f"{sid}.quiz must be an object")
            string(quiz.get("question"), f"{sid}.quiz.question", required=True)
            options = quiz.get("options")
            if not isinstance(options, list) or len(options) < 2:
                raise ValueError(f"{sid}.quiz needs at least two options")
            for option in options:
                if not isinstance(option, dict) or type(option.get("correct")) is not bool:
                    raise ValueError(f"{sid}.quiz options need a boolean correct field")
                string(option.get("text"), f"{sid}.quiz.option.text", required=True)
                string(option.get("feedback"), f"{sid}.quiz.option.feedback")
            if not any(option["correct"] for option in options):
                raise ValueError(f"{sid}.quiz needs at least one correct option")
    if quiz_count < 2:
        raise ValueError("The approved lesson must contain at least two interactive quizzes")


def render_items(slide):
    items = slide.get("items", [])
    if not items:
        return ""
    ordered = slide.get("type") in {"flow", "steps"}
    tag = "ol" if ordered else "div"
    child = "li" if ordered else "section"
    pieces = [f'<{tag} class="items">']
    for item in items:
        title = f'<h3 class="item-title">{esc(item["title"])}</h3>' if item.get("title") else ""
        text = f'<p class="item-text">{esc(item["text"])}</p>' if item.get("text") else ""
        pieces.append(f'<{child} class="item">{title}{text}</{child}>')
    pieces.append(f"</{tag}>")
    return "".join(pieces)


def render_quiz(slide):
    quiz = slide.get("quiz")
    if not quiz:
        return ""
    sid = slide["id"]
    options = []
    for index, option in enumerate(quiz["options"]):
        options.append(
            f'<li class="quiz-option"><button type="button" class="quiz-choice" data-quiz-option="{index}" '
            f'data-correct="{str(option["correct"]).lower()}" data-feedback="{esc(option.get("feedback", ""))}" '
            f'aria-pressed="false" aria-describedby="{esc(sid)}-feedback">'
            f'<span class="option-letter" aria-hidden="true">{chr(65 + index)}</span>'
            f'<span>{esc(option["text"])}</span></button></li>'
        )
    return (
        f'<div class="quiz" data-quiz="{esc(sid)}"><fieldset><legend>{esc(quiz["question"])}</legend>'
        f'<ol class="quiz-options">{"".join(options)}</ol></fieldset>'
        f'<div class="quiz-feedback" id="{esc(sid)}-feedback" role="status" aria-live="polite" hidden></div>'
        '<button type="button" class="quiz-reset" data-quiz-reset>重新作答</button></div>'
    )


def render_citations(slide, catalog):
    links = []
    for citation in slide["citations"]:
        path = wiki_path(citation["wiki"])
        label = citation.get("label") or catalog.get(path, {}).get("title") or path
        links.append(
            f'<a href="wiki.html#page={quote(path, safe="")}" data-wiki="{esc(path)}" '
            f'data-claims="{esc(" ".join(citation["claims"]))}">{esc(label)}</a>'
        )
    return '<footer class="source-footer"><span class="source-label">Wiki 出處</span><div class="source-links">' + "".join(links) + "</div></footer>"


def render_slide(slide, number, total, catalog):
    sid = slide["id"]
    kind = slide.get("type", "concept")
    heading = "h1" if number == 1 else "h2"
    lead = f'<p class="slide-lead">{esc(slide["lead"])}</p>' if slide.get("lead") else ""
    bullets = '<ul class="slide-bullets">' + "".join(f"<li>{esc(text)}</li>" for text in slide.get("bullets", [])) + "</ul>" if slide.get("bullets") else ""
    chat = ""
    if slide.get("chat"):
        messages = []
        for message in slide["chat"]:
            sender = message.get("sender", "")
            messages.append(f'<div class="chat-message" role="listitem" data-sender="{esc(sender)}"><span class="chat-sender">{esc(sender)}</span><p class="chat-text">{esc(message.get("text", ""))}</p></div>')
        chat = '<div class="chat" role="list" aria-label="教學情境">' + "".join(messages) + "</div>"
    note = f'<details class="teacher-notes"><summary>教學備註</summary><p>{esc(slide["note"])}</p></details>' if slide.get("note") else ""
    hidden = "" if number == 1 else ' hidden aria-hidden="true"'
    return (
        f'<section class="slide" id="{esc(sid)}" data-type="{esc(kind)}" data-slide="{number}" '
        f'aria-labelledby="{esc(sid)}-title"{hidden}><div class="slide-inner">'
        f'<header class="slide-header"><div class="eyebrow"><span>AI 識讀練習</span><span class="slide-number">{number:02} / {total:02}</span></div>'
        f'<{heading} class="slide-title" id="{esc(sid)}-title" tabindex="-1">{esc(slide["title"])}</{heading}>{lead}</header>'
        f'<div class="slide-body">{bullets}{render_items(slide)}{chat}{render_quiz(slide)}</div>'
        f'{note}{render_citations(slide, catalog)}</div></section>'
    )


def render_deck(root) -> Path:
    """Render approved text only; return the resulting deck.html path."""
    root = Path(root).resolve()
    content_gate(root)
    data = read_json(root / "teaching/deck.json")
    slides = data.get("slides") if isinstance(data, dict) else data
    catalog = load_catalog(root)
    validate_slides(root, slides, catalog)
    css = (root / "assets/deck.css").read_text(encoding="utf-8-sig")
    js = (root / "assets/deck.js").read_text(encoding="utf-8-sig")
    if "</style" in css.lower() or "</script" in js.lower():
        raise ValueError("Inline assets cannot contain closing style/script tags")
    title = slides[0]["title"]
    body = "\n".join(render_slide(slide, number, len(slides), catalog) for number, slide in enumerate(slides, 1))
    output = f'''<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="generator" content="HW10 deterministic approved-text renderer"><title>{esc(title)}</title><style>{css}</style></head>
<body class="deck-page"><a class="skip-link" href="#slides">跳到簡報內容</a><div class="deck-shell"><header class="deck-topbar"><a class="brand" href="#{esc(slides[0]['id'])}">AI 識讀課<span>先停一下，再查證</span></a><nav class="utility-links" aria-label="學習資源"><a href="wiki.html">知識 Wiki</a><a href="workflow.html">製作流程</a><button type="button" data-deck-print>列印</button></nav></header>
<main class="slides" id="slides" tabindex="-1" aria-label="教學簡報">{body}</main>
<nav class="deck-controls" aria-label="投影片導覽"><button class="nav-button" type="button" data-deck-prev aria-label="上一頁">← 上一頁</button><div class="deck-progress"><span class="page-count" data-page-count>1 / {len(slides)}</span><div class="progress-track" role="progressbar" aria-label="簡報進度" aria-valuemin="1" aria-valuemax="{len(slides)}" aria-valuenow="1"><span class="progress-fill" style="width:{100 / len(slides):.6f}%"></span></div><span class="keyboard-hint">鍵盤 ← → 換頁</span></div><button class="nav-button" type="button" data-deck-next aria-label="下一頁">下一頁 →</button></nav></div>
<p class="sr-only deck-status" role="status" aria-live="polite" aria-atomic="true" data-deck-status></p><noscript><style>.slide[hidden]{{display:block!important}}.deck-controls{{display:none}}</style><p class="noscript-note">JavaScript 未啟用，以下顯示全部投影片；互動題與換頁功能需啟用 JavaScript。</p></noscript><script>{js}</script></body></html>'''
    target = root / "deck.html"
    target.write_text(output, encoding="utf-8", newline="\n")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = render_deck(args.root)
    print(f"Rendered approved text only: {result}")


if __name__ == "__main__":
    main()
