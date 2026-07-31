"""tts.ruby (台本 LLM インラインルビ + 自動読み辞書 I/O) のユニットテスト.

Sprint T56 Ticket (Issue #52)。
"""
from __future__ import annotations

from pathlib import Path

from karyu_tech_news.tts.ruby import (
    append_auto_readings,
    extract_ruby,
    load_auto_readings,
)

# ---------- extract_ruby: 正常系 ----------


def test_extract_ruby_single_pair() -> None:
    cleaned, mapping = extract_ruby("[[零一万物|レイイチバンブツ]] が新モデルを発表しました。")
    assert cleaned == "零一万物 が新モデルを発表しました。"
    assert mapping == {"零一万物": "レイイチバンブツ"}


def test_extract_ruby_multiple_pairs() -> None:
    text = "[[GPU|ジーピーユー]] を使い [[灵晟|リンション]] が発表しました。"
    cleaned, mapping = extract_ruby(text)
    assert cleaned == "GPU を使い 灵晟 が発表しました。"
    assert mapping == {"GPU": "ジーピーユー", "灵晟": "リンション"}


def test_extract_ruby_japanese_surface() -> None:
    """カナ表記の表記側にも対応する (日本語混じり固有名詞)."""
    cleaned, mapping = extract_ruby("[[アリペイHK|アリペイエイチケー]] が拡大しています。")
    assert cleaned == "アリペイHK が拡大しています。"
    assert mapping == {"アリペイHK": "アリペイエイチケー"}


def test_extract_ruby_chinese_surface() -> None:
    cleaned, mapping = extract_ruby("[[千里科技|チエンリカギ]] の新工場です。")
    assert cleaned == "千里科技 の新工場です。"
    assert mapping == {"千里科技": "チエンリカギ"}


def test_extract_ruby_no_match_returns_original() -> None:
    text = "ルビの無い普通の本文です。"
    cleaned, mapping = extract_ruby(text)
    assert cleaned == text
    assert mapping == {}


def test_extract_ruby_strips_surrounding_whitespace() -> None:
    cleaned, mapping = extract_ruby("[[ 零一万物 | レイイチバンブツ ]] が発表。")
    assert cleaned == "零一万物 が発表。"
    assert mapping == {"零一万物": "レイイチバンブツ"}


# ---------- extract_ruby: malformed は素通し (fail-open) ----------


def test_extract_ruby_empty_reading_passes_through() -> None:
    text = "[[零一万物|]] が発表しました。"
    cleaned, mapping = extract_ruby(text)
    assert cleaned == text
    assert mapping == {}


def test_extract_ruby_empty_surface_passes_through() -> None:
    text = "[[|レイイチバンブツ]] が発表しました。"
    cleaned, mapping = extract_ruby(text)
    assert cleaned == text
    assert mapping == {}


def test_extract_ruby_unclosed_passes_through() -> None:
    text = "[[零一万物|レイイチバンブツ が発表しました。"
    cleaned, mapping = extract_ruby(text)
    assert cleaned == text
    assert mapping == {}


def test_extract_ruby_nested_passes_through() -> None:
    text = "[[零一万物|[[入れ子|ネスト]]]] が発表しました。"
    cleaned, mapping = extract_ruby(text)
    # 最内 (最短一致) の `[[入れ子|ネスト]]` のみ有効なルビとして解釈され除去される。
    # 外側の `[[零一万物|` `]]` は対応するペアが崩れているため素通しする。
    assert "[[零一万物|" in cleaned
    assert mapping == {"入れ子": "ネスト"}


def test_extract_ruby_multiline_content_passes_through() -> None:
    text = "[[零一万物|レイイチ\nバンブツ]] が発表しました。"
    cleaned, mapping = extract_ruby(text)
    assert cleaned == text
    assert mapping == {}


# ---------- extract_ruby: 重複表記は初出優先 ----------


def test_extract_ruby_duplicate_surface_keeps_first_reading() -> None:
    text = "[[零一万物|レイイチバンブツ]] の続報です。[[零一万物|ゼロイチマンブツ]] も参照。"
    cleaned, mapping = extract_ruby(text)
    assert cleaned == "零一万物 の続報です。零一万物 も参照。"
    assert mapping == {"零一万物": "レイイチバンブツ"}


# ---------- load_auto_readings ----------


def test_load_auto_readings_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_auto_readings(tmp_path / "nope.yaml") == {}


def test_load_auto_readings_reads_flat_yaml(tmp_path: Path) -> None:
    path = tmp_path / "auto.yaml"
    path.write_text("零一万物: レイイチバンブツ\nGPU: ジーピーユー\n", encoding="utf-8")
    assert load_auto_readings(path) == {"零一万物": "レイイチバンブツ", "GPU": "ジーピーユー"}


def test_load_auto_readings_broken_yaml_fails_open(tmp_path: Path) -> None:
    path = tmp_path / "auto.yaml"
    path.write_text("not: [valid", encoding="utf-8")
    assert load_auto_readings(path) == {}


def test_load_auto_readings_non_mapping_fails_open(tmp_path: Path) -> None:
    path = tmp_path / "auto.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    assert load_auto_readings(path) == {}


def test_load_auto_readings_non_utf8_fails_open(tmp_path: Path) -> None:
    path = tmp_path / "auto.yaml"
    path.write_bytes(b"\xff\xfe\x00broken")
    assert load_auto_readings(path) == {}


# ---------- append_auto_readings ----------


def test_append_auto_readings_creates_new_file(tmp_path: Path) -> None:
    path = tmp_path / "sub" / "auto.yaml"
    append_auto_readings(path, {"零一万物": "レイイチバンブツ"})
    assert load_auto_readings(path) == {"零一万物": "レイイチバンブツ"}


def test_append_auto_readings_adds_to_existing(tmp_path: Path) -> None:
    path = tmp_path / "auto.yaml"
    append_auto_readings(path, {"零一万物": "レイイチバンブツ"})
    append_auto_readings(path, {"GPU": "ジーピーユー"})
    assert load_auto_readings(path) == {
        "零一万物": "レイイチバンブツ",
        "GPU": "ジーピーユー",
    }


def test_append_auto_readings_does_not_overwrite_existing_key(tmp_path: Path) -> None:
    path = tmp_path / "auto.yaml"
    append_auto_readings(path, {"零一万物": "レイイチバンブツ"})
    append_auto_readings(path, {"零一万物": "別の読み"})
    assert load_auto_readings(path) == {"零一万物": "レイイチバンブツ"}


def test_append_auto_readings_empty_mapping_is_noop(tmp_path: Path) -> None:
    path = tmp_path / "auto.yaml"
    append_auto_readings(path, {})
    assert not path.exists()


def test_append_auto_readings_broken_existing_file_fails_open(tmp_path: Path) -> None:
    """既存ファイルが壊れていても、新規マッピングの追記自体は落とさない (fail-open)."""
    path = tmp_path / "auto.yaml"
    path.write_text("not: [valid", encoding="utf-8")
    append_auto_readings(path, {"零一万物": "レイイチバンブツ"})
    # 壊れた既存ファイルは空として扱われるため、新規追記のみが反映される。
    assert load_auto_readings(path) == {"零一万物": "レイイチバンブツ"}


# ---------- マージ優先度: manual が auto に勝つ (二層マージ, produce 側の契約) ----------


def test_merge_priority_manual_overrides_auto(tmp_path: Path) -> None:
    """produce 側の `{**auto, **manual}` マージ契約: 同一キーは manual が勝つ."""
    auto_path = tmp_path / "auto.yaml"
    append_auto_readings(auto_path, {"共通語": "オート読み", "auto専用語": "オート専用読み"})
    auto_dict = load_auto_readings(auto_path)
    manual_dict = {"共通語": "マニュアル読み"}

    merged = {**auto_dict, **manual_dict}

    assert merged["共通語"] == "マニュアル読み"  # 競合キーは manual が勝つ
    assert merged["auto専用語"] == "オート専用読み"  # auto 単独のキーは残る
