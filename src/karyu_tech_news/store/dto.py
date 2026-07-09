"""store 層専用の永続化 DTO (Data Transfer Object).

DESIGN.md §5 は「collect → store ← deliver」の逆向き依存を禁止する。store は
最下層のハブであり、上位層 (edit / script) のドメイン型を import してはならない。

このモジュールは repo.py が受け取る永続化専用の軽量 dataclass を定義する。
呼び出し側 (例: script/runner.py) が edit/script のドメイン型からここの DTO へ
変換してから repo 関数を呼ぶ。DTO 自身は primitive 型のみで構成し、
edit/ や script/ を import しない (T45)。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class EpisodeDraftInput:
    """`create_episode_draft` への入力 (EpisodeScript の永続化に必要な部分集合)."""

    generated_at: datetime
    variant: str
    title: str
    estimated_minutes: int
    notices: list[str]
    markdown: str


@dataclass(frozen=True, slots=True)
class TopicCandidateInput:
    """`insert_topic_candidates` への入力 (JudgedTopic の永続化に必要な部分集合)."""

    item_id: int
    prescore: int
    llm_score: int
    tone: str
    source_tier: int
    corroboration_count: int


@dataclass(frozen=True, slots=True)
class ScriptVersionInput:
    """`insert_script_versions` への入力 (TopicScriptResult の永続化に必要な部分集合)."""

    method: str
    attempts: int
    body: str
