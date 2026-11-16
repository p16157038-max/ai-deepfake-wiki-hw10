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


def icon(name, class_name=""):
    """Original code-native pictograms, never platform logos or case photos."""
    paths = {
        "voice": '<path d="M8 32h5m4-12v24m7-34v44m8-34v24m8-29v34m8-23v12m8-6h3"/>',
        "face": '<rect x="10" y="7" width="44" height="50" rx="12"/><circle cx="32" cy="26" r="9"/><path d="M18 49c1-14 27-14 28 0M10 17H5m49 0h5M10 47H5m49 0h5"/>',
        "chat": '<path d="M10 11h44v32H29L17 54V43h-7z"/><path d="M19 22h26M19 31h17"/>',
        "identity": '<rect x="5" y="13" width="54" height="38" rx="7"/><circle cx="21" cy="27" r="7"/><path d="M11 43c1-12 19-12 20 0m8-17h12m-12 9h8"/>',
        "question": '<circle cx="32" cy="32" r="24"/><path d="M24 24c0-11 18-11 18 0 0 8-10 6-10 15m0 7v1"/>',
        "alert": '<path d="M32 7 59 53H5zM32 23v14m0 8v1"/>',
        "document": '<path d="M14 5h27l10 10v44H14zM41 5v12h10M23 27h20M23 36h20M23 45h12"/>',
        "video": '<rect x="5" y="12" width="42" height="40" rx="8"/><path d="m47 26 12-9v30l-12-9M24 24l12 8-12 8z"/>',
        "shield": '<path d="m32 5 23 9v17c0 15-23 28-23 28S9 46 9 31V14z"/><path d="m21 31 8 8 16-17"/>',
        "search": '<circle cx="27" cy="27" r="18"/><path d="m41 41 16 16M20 27h14m-7-7v14"/>',
        "label": '<path d="M8 10h28l21 21-26 26L8 34z"/><circle cx="23" cy="25" r="4"/>',
        "lock": '<rect x="11" y="27" width="42" height="31" rx="7"/><path d="M20 27V16c0-17 24-17 24 0v11M32 39v8"/>',
        "stop": '<path d="m23 5 18 0 18 18v18L41 59H23L5 41V23z"/><path d="M21 32h22"/>',
        "exit": '<path d="M29 8H10v48h19M22 32h35m-12-11 12 11-12 11"/>',
        "archive": '<path d="M8 16h48v41H8zM5 7h54v12H5zM24 29h16"/>',
        "phone": '<path d="M16 7 7 16c0 20 21 41 41 41l9-9-13-13-9 6c-8-3-12-7-15-15l6-6z"/>',
        "check": '<circle cx="32" cy="32" r="25"/><path d="m19 32 9 9 18-21"/>',
        "link": '<path d="m25 20 7-7c17-17 32 0 17 15l-7 7M22 29l-7 7C0 51 16 67 31 52l7-7M23 41l18-18"/>',
    }
    return f'<svg class="pictogram {esc(class_name)}" viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths.get(name, paths["check"])}</svg>'


def scene(kind):
    """Conceptual editorial diagrams; they do not depict real people or evidence."""
    if kind == "cover":
        content = '''<path class="scene-grid" d="M30 60h440M30 130h440M30 200h440M30 270h440M100 25v300M180 25v300M260 25v300M340 25v300M420 25v300"/>
<rect class="scene-float" x="12" y="85" width="169" height="120" rx="17"/><text class="scene-label" x="32" y="117">聲音</text><path class="scene-wave" d="M34 154h10m8-14v28m11-41v54m11-36v18m11-51v80m11-57v34m11-25v16m11-35v54m11-31v8m11-4h12"/>
<path class="scene-connector" d="M181 145h41m-11-8 11 8-11 8"/><rect class="scene-phone" x="232" y="21" width="207" height="318" rx="30"/><rect class="scene-screen" x="245" y="34" width="181" height="291" rx="20"/><path class="scene-notch" d="M289 34h92v15h-92z"/><circle class="scene-avatar" cx="336" cy="122" r="37"/><circle class="scene-avatar-line" cx="336" cy="110" r="12"/><path class="scene-avatar-line" d="M314 143c0-25 44-25 44 0"/><text class="scene-label" x="280" y="192">身分</text><rect class="scene-row" x="268" y="210" width="135" height="11" rx="5"/><rect class="scene-row" x="268" y="233" width="94" height="11" rx="5"/><rect class="scene-call" x="276" y="270" width="120" height="33" rx="16"/><path class="scene-call-mark" d="M305 281h63"/>
<circle class="scene-question-bg" cx="431" cy="91" r="36"/><path class="scene-question" d="M420 81c0-17 25-17 25 0 0 11-13 8-13 20m0 9v2"/><path class="scene-bracket" d="M34 239v46h114M466 207v75h-12"/>'''
        viewbox = "0 0 500 360"
    elif kind == "document":
        content = '''<rect class="scene-folder" x="22" y="64" width="338" height="228" rx="18"/><path class="scene-folder-tab" d="M22 89V57q0-16 16-16h101l22 23h183q16 0 16 16v9"/><path class="scene-paper" d="M102 20h155l49 49v188H102z"/><path class="scene-fold" d="M257 20v49h49"/><path class="scene-document-lines" d="M129 97h116m-116 22h150m-150 22h150m-150 22h114m-114 22h134"/><rect class="scene-highlight" x="122" y="210" width="164" height="23" rx="4"/><path class="scene-envelope" d="M35 200h157v103H35zM35 200l78 64 79-64"/><circle class="scene-evidence-dot" cx="323" cy="259" r="31"/><path class="scene-evidence-check" d="m309 259 10 10 20-23"/>'''
        viewbox = "0 0 400 330"
    elif kind == "video":
        content = '''<rect class="scene-folder" x="18" y="25" width="354" height="229" rx="16"/><rect class="scene-video-screen" x="35" y="43" width="320" height="176" rx="8"/><circle class="scene-video-avatar" cx="112" cy="111" r="29"/><path class="scene-video-avatar-line" d="M76 175c0-47 73-47 73 0"/><circle class="scene-video-avatar" cx="278" cy="111" r="29"/><path class="scene-video-avatar-line" d="M242 175c0-47 73-47 73 0"/><circle class="scene-play-bg" cx="195" cy="128" r="31"/><path class="scene-play" d="m187 113 25 15-25 15z"/><path class="scene-record-line" d="M40 236h134m24 0h42"/><circle class="scene-record-dot" cx="347" cy="236" r="5"/><path class="scene-connector" d="M196 255v30h37"/><path class="scene-message" d="M239 253h130v51h-83l-26 18v-18h-21z"/><path class="scene-message-lines" d="M255 270h98m-98 17h71"/>'''
        viewbox = "0 0 400 330"
    else:
        content = '''<circle class="scene-orbit" cx="222" cy="174" r="139"/><circle class="scene-orbit" cx="222" cy="174" r="108"/><path class="scene-shield" d="m222 49 93 37v73c0 66-93 123-93 123s-93-57-93-123V86z"/><path class="scene-big-check" d="m174 164 34 34 68-78"/><rect class="scene-chip" x="19" y="105" width="120" height="49" rx="10"/><path class="scene-chip-line" d="M39 130h78"/><rect class="scene-chip" x="302" y="223" width="120" height="49" rx="10"/><path class="scene-chip-line" d="M322 248h78"/><circle class="scene-coral-dot" cx="337" cy="75" r="15"/>'''
        viewbox = "0 0 445 340"
    return f'<svg class="scene-svg" viewBox="{viewbox}" aria-hidden="true">{content}</svg>'


def visual_module(kind, extra=""):
    return f'<figure class="visual-module {esc(extra)}">{scene(kind)}<figcaption class="visual-caption">概念示意</figcaption></figure>'


ITEM_ICONS = {
    "s02": ["face", "question", "check"], "s03": ["voice", "video", "chat"],
    "s04": ["identity", "alert", "search"], "s05": ["document", "search", "archive"],
    "s06": ["archive", "video", "chat"], "s08": ["search", "question", "phone"],
    "s09": ["label", "face", "search"], "s10": ["chat", "lock", "identity"],
    "s11": ["stop", "exit", "search", "archive"], "s13": ["phone", "lock", "archive"],
    "s14": ["identity", "question", "check"],
}


def platform_preview(index):
    tag = '<rect class="preview-ai-tag" x="79" y="27" width="39" height="20" rx="5"/><text class="preview-ai-text" x="88" y="41">AI</text>' if index == 0 else ""
    if index == 2:
        return f'<div class="platform-preview preview-search">{icon("search")}</div>'
    return f'<div class="platform-preview"><svg viewBox="0 0 200 103" aria-hidden="true"><rect class="preview-surface" x="3" y="3" width="194" height="97" rx="9"/><rect class="preview-video" x="16" y="15" width="114" height="72" rx="6"/><circle class="preview-avatar" cx="72" cy="43" r="12"/><path class="preview-person" d="M49 78c0-30 46-30 46 0"/><path class="preview-lines" d="M144 27h36m-36 14h26m-26 25h36m-36 14h20"/>{tag}</svg></div>'


def render_items(slide):
    items = slide.get("items", [])
    if not items:
        return ""
    ordered = slide.get("type") in {"flow", "steps"}
    tag = "ol" if ordered else "div"
    child = "li" if ordered else "section"
    pieces = [f'<{tag} class="items">']
    for index, item in enumerate(items):
        title = f'<h3 class="item-title">{esc(item["title"])}</h3>' if item.get("title") else ""
        text = f'<p class="item-text">{esc(item["text"])}</p>' if item.get("text") else ""
        names = ITEM_ICONS.get(slide["id"], [])
        symbol = f'<span class="item-icon">{icon(names[index])}</span>' if index < len(names) else ""
        preview = platform_preview(index) if slide["id"] == "s09" else ""
        pieces.append(f'<{child} class="item">{preview}{symbol}<div class="item-copy">{title}{text}</div></{child}>')
    pieces.append(f"</{tag}>")
    return "".join(pieces)


def render_chat(slide):
    messages = []
    for message in slide.get("chat", []):
        sender = message.get("sender", "")
        messages.append(f'<div class="chat-message" role="listitem" data-sender="{esc(sender)}"><span class="chat-sender">{esc(sender)}</span><p class="chat-text">{esc(message.get("text", ""))}</p></div>')
    return '<div class="chat" role="list" aria-label="教學情境">' + "".join(messages) + "</div>"


def phone_conversation(slide):
    voice = slide["id"] == "s07"
    symbol = icon("voice" if voice else "lock")
    return ('<div class="phone-stage"><div class="phone-frame"><div class="phone-top"><span class="phone-sensor"></span><span class="phone-signal" aria-hidden="true">▂ ▄ ▆</span></div>'
            f'<div class="phone-identity">{icon("identity")}<span>教學模擬</span></div>{render_chat(slide)}'
            f'<div class="phone-bottom" aria-hidden="true">{symbol}<span class="phone-dot"></span><span class="phone-dot"></span><span class="phone-dot"></span></div>'
            '</div><p class="phone-caption">教學模擬・非真實聊天室</p></div>')


def render_content(slide):
    sid = slide["id"]
    items = render_items(slide)
    bullets = '<ul class="slide-bullets">' + "".join(f'<li>{esc(text)}</li>' for text in slide.get("bullets", [])) + '</ul>' if slide.get("bullets") else ""
    if sid == "s01":
        body = f'<div class="cover-copy">{bullets}{items}</div>{visual_module("cover", "cover-visual")}'
        layout = "cover"
    elif sid in {"s05", "s06"}:
        body = f'{visual_module("document" if sid == "s05" else "video")}{bullets}{items}'
        layout = "case"
    elif slide.get("quiz"):
        body = f'{phone_conversation(slide)}{render_quiz(slide)}'
        layout = "quiz"
    elif sid == "s14":
        body = f'<div class="closing-copy">{bullets}{items}</div>{visual_module("shield")}'
        layout = "closing"
    else:
        layout = {"s02": "learning", "s03": "media", "s04": "chain", "s08": "comparison", "s09": "comparison", "s10": "platform", "s11": "action", "s13": "support"}.get(sid, "standard")
        body = f'{bullets}{items}<span class="diagram-caption">概念示意</span>'
    return f'<div class="content-layout {layout}-layout" data-layout="{layout}">{body}</div>'


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
    links.append(f'<a href="evidence.html#slide={esc(slide["id"])}" class="trace-link">本頁證據</a>')
    return '<footer class="source-footer"><span class="source-label">Wiki 出處</span><div class="source-links">' + "".join(links) + "</div></footer>"


def render_slide(slide, number, total, catalog):
    sid = slide["id"]
    kind = slide.get("type", "concept")
    heading = "h1" if number == 1 else "h2"
    lead = f'<p class="slide-lead">{esc(slide["lead"])}</p>' if slide.get("lead") else ""
    note = f'<details class="teacher-notes"><summary>教學備註</summary><p>{esc(slide["note"])}</p></details>' if slide.get("note") else ""
    hidden = "" if number == 1 else ' hidden aria-hidden="true"'
    return (
        f'<section class="slide" id="{esc(sid)}" data-type="{esc(kind)}" data-slide="{number}" '
        f'aria-labelledby="{esc(sid)}-title"{hidden}><div class="slide-inner">'
        f'<header class="slide-header"><div class="eyebrow"><span>AI 識讀練習</span><span class="slide-number">{number:02} / {total:02}</span></div>'
        f'<{heading} class="slide-title" id="{esc(sid)}-title" tabindex="-1">{esc(slide["title"])}</{heading}>{lead}</header>'
        f'<div class="slide-body">{render_content(slide)}</div>'
        f'<div class="slide-meta">{note}{render_citations(slide, catalog)}</div></div></section>'
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
<body class="deck-page"><a class="skip-link" href="#slides">跳到簡報內容</a><div class="deck-shell"><header class="deck-topbar"><a class="brand" href="#{esc(slides[0]['id'])}">AI 識讀課<span>先停一下，再查證</span></a><nav class="utility-links" aria-label="學習資源"><a href="wiki.html">知識 Wiki</a><a href="workflow.html">製作流程</a><a href="evidence.html">驗收證據</a><button type="button" data-deck-print>列印</button></nav></header>
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
