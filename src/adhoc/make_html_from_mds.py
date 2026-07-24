"""
Adhoc-скрипт: сборка набора markdown-отчётов факторного анализа в один
статичный HTML-файл с боковым меню.

В папке ``mds_dir`` отбираются все файлы ``*.md``, в имени которых встречается
``date_token`` (например ``2026-04-30``). Содержимое каждого файла рендерится
в HTML (markdown -> html, GFM-таблицы), все отчёты упаковываются в единый
самодостаточный HTML с навигацией: клик по пункту меню (имя файла) показывает
в основной области отрендеренный текст соответствующего отчёта.

Запуск:
    source /Users/baltakov-df/venv/foo/bin/activate
    PYTHONPATH=... python -m adhoc.make_html_from_mds
или напрямую:
    python src/adhoc/make_html_from_mds.py
"""
from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import markdown


REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MDS_DIR = REPO_ROOT / "src" / "adhoc" / "mds"
DEFAULT_OUT = REPO_ROOT / "agent_stuff" / "results" / "tbgosb_results.html"

# Примечание о sane_lists: расширение НЕ используется намеренно. Оно требует
# пустую строку перед списком и не помогает (проблему отсутствия пустой строки
# решает препроцессинг _normalize_lists, а вложенность даёт tab_length=2).
MD_EXTENSIONS = ["tables", "fenced_code", "attr_list"]

# tab_length=2: в исходных .md вложенные пункты списков имеют отступ 2 пробела
# (а не 4). С дефолтным tab_length=4 такие подпункты схлопываются в плоский список
# верхнего уровня вместо вложенных <ul>. Поэтому явно выставляем 2.
MD_TAB_LENGTH = 2


def select_files(mds_dir: Path, date_token: str) -> list[Path]:
    """Вернуть отсортированный список ``*.md`` файлов, чьё имя содержит ``date_token``."""
    files = [p for p in mds_dir.glob("*.md") if date_token in p.name]
    files.sort(key=lambda p: p.name)
    return files


_ULIST_RE = re.compile(r"^[ \t]*([-*+])[ \t]+\S")
_OLIST_RE = re.compile(r"^[ \t]*\d{1,9}[.)][ \t]+\S")

_FENCE_MARKERS = ("```", "~~~")


def _is_list_item(line: str) -> bool:
    return bool(_ULIST_RE.match(line) or _OLIST_RE.match(line))


def normalize_lists(md_text: str) -> str:
    """Вставить пустую строку перед списком, если он идёт сразу после обычного
    текста (абзаца/заголовка/таблицы).

    Python-Markdown не позволяет списку прервать абзац: ``- item`` распознаётся
    как список только если перед ним есть пустая строка, иначе весь блок
    (включая ``-``) проваливается в предшествующий абзац и маркеры списков
    остаются literal-текстом. В исходных ``.md`` это правило местами нарушено
    (например ``chkdtb_bb__2026-04-30.md`` — «- item» сразу после строки без
    отступа). Функция приводит такие места к корректному виду:

    - не трогает уже разделённые пустой строкой блоки;
    - не ломает вложенность (между пунктами одного списка пустые строки не
      добавляются — проверяем, что предыдущая строка не сама пункт списка);
    - игнорирует содержимое fenced code-блоков.
    """
    out: list[str] = []
    in_fence = False
    fence_marker = ""
    for line in md_text.split("\n"):
        stripped = line.lstrip()
        if stripped[:3] in _FENCE_MARKERS:
            if not in_fence:
                in_fence = True
                fence_marker = stripped[:3]
            elif stripped.startswith(fence_marker):
                in_fence = False
        if (
            not in_fence
            and out
            and _is_list_item(line)
            and out[-1].strip() != ""
            and not _is_list_item(out[-1])
        ):
            out.append("")  # разделить абзац и список пустой строкой
        out.append(line)
    return "\n".join(out)


def render_md_to_html(md_text: str) -> str:
    """Сконвертировать markdown-текст в HTML-фрагмент."""
    md_text = normalize_lists(md_text)
    return markdown.markdown(
        md_text,
        extensions=MD_EXTENSIONS,
        output_format="html",
        tab_length=MD_TAB_LENGTH,
    )


def build_nav_item(index: int, file_name: str, size_bytes: int) -> str:
    """Один пункт бокового меню."""
    label = html.escape(file_name)
    size_kb = f"{size_bytes / 1024:4.1f} КБ"
    return (
        f'<a class="nav-item" href="#" data-target="panel-{index}">'
        f'<span class="nav-label">{label}</span>'
        f'<span class="nav-size">{html.escape(size_kb)}</span>'
        f"</a>"
    )


def build_panel(index: int, file_name: str, rendered_html: str) -> str:
    """Контейнер отрендеренного содержимого одного отчёта."""
    safe_name = html.escape(file_name)
    return (
        f'<article class="panel" id="panel-{index}">'
        f'<header class="panel-header"><h1>{safe_name}</h1></header>'
        f'<div class="panel-body markdown-body">{rendered_html}</div>'
        f"</article>"
    )


CSS = """
* { box-sizing: border-box; }
:root {
  --bg: #f5f6f8;
  --sidebar-bg: #1f2933;
  --sidebar-fg: #cbd5e1;
  --sidebar-fg-active: #ffffff;
  --sidebar-accent: #2563eb;
  --content-bg: #ffffff;
  --border: #e2e8f0;
  --text: #1e293b;
  --text-muted: #64748b;
}
html, body { height: 100%; margin: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: var(--text);
  background: var(--bg);
}
.layout { display: flex; min-height: 100vh; }

/* ---- Sidebar ---- */
.sidebar {
  width: 320px;
  flex: 0 0 320px;
  background: var(--sidebar-bg);
  color: var(--sidebar-fg);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
}
.sidebar-header {
  padding: 18px 20px 14px;
  border-bottom: 1px solid rgba(255,255,255,.08);
}
.sidebar-header h2 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}
.sidebar-header .meta {
  font-size: 12px;
  color: var(--text-muted);
}
.sidebar-search {
  padding: 10px 14px 6px;
}
.sidebar-search input {
  width: 100%;
  padding: 7px 10px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.06);
  color: #fff;
  font-size: 13px;
  outline: none;
}
.sidebar-search input::placeholder { color: #94a3b8; }
.sidebar-search input:focus { border-color: var(--sidebar-accent); }
.nav {
  overflow-y: auto;
  flex: 1 1 auto;
  padding: 4px 0 16px;
}
.nav-item {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 20px;
  color: var(--sidebar-fg);
  text-decoration: none;
  font-size: 13px;
  line-height: 1.35;
  border-left: 3px solid transparent;
  cursor: pointer;
}
.nav-item:hover { background: rgba(255,255,255,.05); color: #fff; }
.nav-item.active {
  background: rgba(37,99,235,.18);
  border-left-color: var(--sidebar-accent);
  color: var(--sidebar-fg-active);
  font-weight: 600;
}
.nav-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nav-size {
  font-size: 11px;
  color: #64748b;
  flex: 0 0 auto;
  font-variant-numeric: tabular-nums;
}
.nav-item.hidden { display: none; }
.nav-empty {
  padding: 16px 20px;
  font-size: 12px;
  color: #64748b;
  font-style: italic;
}

/* ---- Content ---- */
.content {
  flex: 1 1 auto;
  overflow-y: auto;
  height: 100vh;
  position: sticky;
  top: 0;
}
.panel { display: none; padding: 32px 40px 80px; max-width: 1200px; }
.panel.active { display: block; }
.panel-header {
  position: sticky;
  top: 0;
  background: var(--content-bg);
  margin: -32px -40px 24px;
  padding: 22px 40px 18px;
  border-bottom: 1px solid var(--border);
}
.panel-header h1 {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  color: var(--text);
  word-break: break-all;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

/* ---- Rendered markdown ---- */
.markdown-body { font-size: 15px; line-height: 1.7; color: var(--text); }
.markdown-body h1, .markdown-body h2, .markdown-body h3,
.markdown-body h4, .markdown-body h5, .markdown-body h6 {
  margin: 28px 0 12px;
  font-weight: 700;
  line-height: 1.3;
}
.markdown-body h2 { font-size: 22px; border-bottom: 2px solid var(--border); padding-bottom: 8px; }
.markdown-body h3 { font-size: 18px; color: #0f172a; }
.markdown-body p { margin: 12px 0; }
.markdown-body ul, .markdown-body ol { margin: 12px 0; padding-left: 24px; }
.markdown-body li { margin: 4px 0; }
.markdown-body strong { font-weight: 700; }
.markdown-body em { font-style: italic; }
.markdown-body code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 13px;
}
.markdown-body pre {
  background: #0f172a;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
}
.markdown-body pre code { background: transparent; padding: 0; color: inherit; }

/* Tables — основа отчётов, поэтому прорабатываем детально */
.markdown-body table {
  border-collapse: collapse;
  width: 100%;
  margin: 20px 0;
  font-size: 13.5px;
  box-shadow: 0 1px 3px rgba(15,23,42,.06);
  border-radius: 8px;
  overflow: hidden;
}
.markdown-body thead { background: #1e293b; }
.markdown-body thead th {
  color: #f8fafc;
  font-weight: 600;
  text-align: left;
  padding: 10px 12px;
  border: 1px solid #334155;
  white-space: nowrap;
}
.markdown-body tbody tr:nth-child(even) { background: #f8fafc; }
.markdown-body tbody tr:hover { background: #eff6ff; }
.markdown-body td {
  padding: 8px 12px;
  border: 1px solid var(--border);
  vertical-align: top;
}
.markdown-body td strong { white-space: nowrap; }
"""


JS = r"""
(function () {
  const items = Array.from(document.querySelectorAll('.nav-item'));
  const panels = Array.from(document.querySelectorAll('.panel'));
  const headerLabel = document.getElementById('current-file');
  const search = document.getElementById('nav-search');
  const emptyNote = document.getElementById('nav-empty');

  function showPanel(index) {
    panels.forEach((p, i) => p.classList.toggle('active', i === index));
    items.forEach((it, i) => {
      it.classList.toggle('active', i === index);
      if (i === index && it.dataset.target) {
        const panel = document.getElementById(it.dataset.target);
        const header = panel ? panel.querySelector('.panel-header h1') : null;
        if (headerLabel && header) headerLabel.textContent = header.textContent;
      }
    });
    // прокрутка активного пункта в зону видимости
    const active = items[index];
    if (active) active.scrollIntoView({ block: 'nearest' });
  }

  items.forEach((it, i) => {
    it.addEventListener('click', function (e) {
      e.preventDefault();
      showPanel(i);
    });
  });

  // поиск по имени файла
  if (search) {
    search.addEventListener('input', function () {
      const q = this.value.trim().toLowerCase();
      let visible = 0;
      items.forEach((it) => {
        const text = it.querySelector('.nav-label').textContent.toLowerCase();
        const match = !q || text.indexOf(q) !== -1;
        it.classList.toggle('hidden', !match);
        if (match) visible++;
      });
      if (emptyNote) emptyNote.style.display = visible === 0 ? 'block' : 'none';
    });
  }

  // показать первый отчёт по умолчанию
  showPanel(0);
})();
"""


def build_html(files: list[Path], date_token: str) -> str:
    nav_items: list[str] = []
    panels: list[str] = []
    total_bytes = 0

    for i, path in enumerate(files):
        raw = path.read_text(encoding="utf-8")
        size = len(raw.encode("utf-8"))
        total_bytes += size
        rendered = render_md_to_html(raw)
        nav_items.append(build_nav_item(i, path.name, size))
        panels.append(build_panel(i, path.name, rendered))

    nav_html = "\n".join(nav_items)
    panels_html = "\n".join(panels)
    count = len(files)
    total_kb = f"{total_bytes / 1024:.1f}"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Факторный анализ — отчёты за {html.escape(date_token)}</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <div class="sidebar-header">
      <h2>Факторный анализ</h2>
      <div class="meta">Отчётов: {count} · Дата: {html.escape(date_token)} · {total_kb} КБ</div>
    </div>
    <div class="sidebar-search">
      <input id="nav-search" type="text" placeholder="Поиск по имени файла…" autocomplete="off">
    </div>
    <nav class="nav">
{nav_html}
      <div id="nav-empty" class="nav-empty" style="display:none">Ничего не найдено</div>
    </nav>
  </aside>

  <main class="content">
    <div class="panel-header" style="position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid var(--border);padding:14px 40px;font-size:13px;color:var(--text-muted);">
      Текущий отчёт: <span id="current-file" style="color:var(--text);font-weight:600;font-family:ui-monospace,monospace;"></span>
    </div>
{panels_html}
  </main>
</div>

<script>
{JS}
</script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Сборка markdown-отчётов в единый HTML.")
    p.add_argument("--mds-dir", type=Path, default=DEFAULT_MDS_DIR,
                   help=f"Папка с .md файлами (по умолчанию: {DEFAULT_MDS_DIR})")
    p.add_argument("--date", default="2026-04-30",
                   help="Дата-токен для отбора файлов (по умолчанию: 2026-04-30)")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT,
                   help=f"Куда сохранить HTML (по умолчанию: {DEFAULT_OUT})")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    files = select_files(args.mds_dir, args.date)
    if not files:
        raise SystemExit(f"В папке {args.mds_dir} не найдено .md файлов с '{args.date}' в имени")

    out_html = build_html(files, args.date)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(out_html, encoding="utf-8")

    size_kb = args.out.stat().st_size / 1024
    print(f"✓ Обработано файлов: {len(files)}")
    print(f"✓ HTML сохранён: {args.out} ({size_kb:.1f} КБ)")


if __name__ == "__main__":
    main()
