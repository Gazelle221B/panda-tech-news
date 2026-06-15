"""TTS (音声合成) レイヤー — Sprint 2.

ADR-0006: エンジン抽象化レイヤー (`TTSEngine` Protocol) を1枚噛ませ、
Irodori-TTS v3 を主軸にしつつエンジンを差し替え可能にする。
台本生成 (script/) とミックス (mix/) はこの抽象に依存し、実エンジンには依存しない。
"""
