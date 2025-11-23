"""
Streamlit で scw_picker の HTML を埋め込むラッパー。
使い方: streamlit run scw_picker_app.py
"""

from pathlib import Path
import importlib
import streamlit as st


def extract_html_from_py(py_path: Path) -> str | None:
  text = py_path.read_text(encoding="utf-8")
  marker = 'HTML = """'
  start = text.find(marker)
  if start == -1:
    return None
  start += len(marker)
  end = text.find('"""', start)
  if end == -1:
    return None
  return text[start:end]


def load_html() -> str:
  # 1) モジュールから直接取得（同梱されている場合）
  try:
    picker = importlib.import_module("scw_picker")
    if hasattr(picker, "HTML"):
      return picker.HTML  # type: ignore[attr-defined]
  except Exception:
    pass

  # 2) ファイルから取得（同ディレクトリを優先）
  candidates = [
    Path(__file__).with_name("scw_picker.py"),
    Path(__file__).with_name("scw_picker.html"),
    Path(__file__).parent / "scw_picker.py",
    Path(__file__).parent / "scw_picker.html",
  ]
  for p in candidates:
    if not p.exists():
      continue
    if p.suffix == ".py":
      html = extract_html_from_py(p)
      if html:
        return html
    else:
      return p.read_text(encoding="utf-8")

  st.error("scw_picker の HTML を見つけられませんでした。同じフォルダに scw_picker.py か scw_picker.html を置いてください。")
  st.stop()


def main():
  st.set_page_config(page_title="座標ピッカー", layout="wide")
  html = load_html()
  st.components.v1.html(html, height=2000, scrolling=True)


if __name__ == "__main__":
  main()
