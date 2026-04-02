"""Qwen3-TTS engine with voice cloning.

Provides a singleton TTS engine that clones a character voice from a
reference audio sample and generates speech in that voice.

Usage:
    engine = get_qwen3_engine()
    wav_data, sample_rate = engine.synthesize("Hello world")
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

from core.settings import get_tts_config
from utils.log import log_info, log_success, log_error, log_warning


class Qwen3TTSEngine:
    """Singleton Qwen3-TTS engine with cached voice clone prompt.

    Lazy-loads the model on first use. Creates a reusable voice clone
    prompt from the reference audio so every generation reuses the
    same voice identity without re-processing the sample.
    """

    def __init__(self) -> None:
        self._model = None
        self._voice_prompt = None
        self._sample_rate: int = 24000
        self._lock = threading.Lock()
        self._initialized = False
        self._failed = False

    def _ensure_loaded(self) -> None:
        """Lazy-load model and create voice clone prompt."""
        if self._initialized or self._failed:
            return

        config = get_tts_config()

        try:
            import torch
            from qwen_tts import Qwen3TTSModel

            if not torch.cuda.is_available() and "cuda" in config.device:
                log_error("[Qwen3-TTS] CUDA not available")
                self._failed = True
                return

            log_info(f"[Qwen3-TTS] Loading model: {config.model_name} on {config.device}...")

            # Determine attention implementation
            attn_impl = "flash_attention_2"
            try:
                import flash_attn  # noqa: F401
            except ImportError:
                attn_impl = "sdpa"
                log_warning("[Qwen3-TTS] flash-attn not installed, using SDPA (slightly more VRAM)")

            self._model = Qwen3TTSModel.from_pretrained(
                config.model_name,
                device_map=config.device,
                dtype=torch.bfloat16,
                attn_implementation=attn_impl,
            )

            log_success(f"[Qwen3-TTS] Model loaded ({attn_impl})")

            # Load reference voice and create reusable clone prompt
            ref_audio = config.ref_audio_path
            ref_text_path = config.ref_text_path

            if not os.path.exists(ref_audio):
                log_error(f"[Qwen3-TTS] Reference audio not found: {ref_audio}")
                self._failed = True
                return

            # Load reference transcript
            ref_text = ""
            if os.path.exists(ref_text_path):
                ref_text = Path(ref_text_path).read_text(encoding="utf-8").strip()
                log_info(f"[Qwen3-TTS] Reference transcript loaded ({len(ref_text)} chars)")
            else:
                log_warning(f"[Qwen3-TTS] No transcript at {ref_text_path}, using x_vector_only mode")

            # Create reusable voice clone prompt
            log_info(f"[Qwen3-TTS] Creating voice clone prompt from {ref_audio}...")

            if ref_text:
                self._voice_prompt = self._model.create_voice_clone_prompt(
                    ref_audio=ref_audio,
                    ref_text=ref_text,
                    x_vector_only_mode=False,
                )
            else:
                self._voice_prompt = self._model.create_voice_clone_prompt(
                    ref_audio=ref_audio,
                    ref_text="",
                    x_vector_only_mode=True,
                )

            self._initialized = True
            log_success("[Qwen3-TTS] Engine ready — voice prompt cached")

        except ImportError as e:
            log_error(f"[Qwen3-TTS] Missing dependency: {e}. Install: pip install qwen-tts")
            self._failed = True
        except Exception as e:
            log_error(f"[Qwen3-TTS] Failed to initialize: {e}")
            self._failed = True

    def synthesize(
        self,
        text: str,
        language: Optional[str] = None,
    ) -> Optional[Tuple[np.ndarray, int]]:
        """Generate speech in the cloned voice.

        Args:
            text: Text to synthesize.
            language: Language code (default from config).

        Returns:
            (wav_numpy_array, sample_rate) or None on failure.
        """
        with self._lock:
            self._ensure_loaded()

            if not self._initialized or self._model is None:
                return None

            config = get_tts_config()
            lang = language or config.language

            try:
                wavs, sr = self._model.generate_voice_clone(
                    text=text,
                    language=lang,
                    voice_clone_prompt=self._voice_prompt,
                )
                self._sample_rate = sr
                return wavs[0], sr

            except Exception as e:
                log_error(f"[Qwen3-TTS] Synthesis failed: {e}")
                return None

    @property
    def is_available(self) -> bool:
        """Check if the engine can be used (without loading)."""
        if self._failed:
            return False
        if self._initialized:
            return True
        # Check prerequisites without loading
        config = get_tts_config()
        if config.engine != "qwen3":
            return False
        if not os.path.exists(config.ref_audio_path):
            return False
        try:
            import torch
            return torch.cuda.is_available() or "cpu" in config.device
        except ImportError:
            return False


# ── Singleton ──

_engine: Optional[Qwen3TTSEngine] = None


def get_qwen3_engine() -> Optional[Qwen3TTSEngine]:
    """Get the Qwen3-TTS engine singleton.

    Returns None if TTS engine is disabled in config.
    """
    global _engine
    config = get_tts_config()
    if config.engine != "qwen3":
        return None
    if _engine is None:
        _engine = Qwen3TTSEngine()
    return _engine
