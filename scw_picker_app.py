"""
Streamlit で scw_picker のHTMLをそのまま埋め込むラッパー。
依存: streamlit, requests など不要。`streamlit run scw_picker_app.py` で実行。
"""

import streamlit as st
from pathlib import Path

# scw_picker.py に埋め込まれている HTML を読み込む
HTML_PATH = Path(__file__).with_name("scw_picker.py")

# scw_picker.py から HTML 文字列を取り出す簡易パーサ
def load_html():
    text = HTML_PATH.read_text(encoding="utf-8")
    marker = 'HTML = """'
    start = text.find(marker)
    if start == -1:
        st.error("scw_picker.py から HTML を見つけられませんでした。")
        st.stop()
    start += len(marker)
    end = text.find('"""', start)
    if end == -1:
        st.error("scw_picker.py の HTML 終端が見つかりませんでした。")
        st.stop()
    return text[start:end]


def main():
    st.set_page_config(page_title="座標ピッカー", layout="wide")
    html = load_html()
    # 高さが足りない場合は height を増やす
    st.components.v1.html(html, height=1200, scrolling=True)


if __name__ == "__main__":
    main()
