"""GUI Controller via pyautogui.

Provides desktop GUI automation:
- click, double_click, right_click, type_text, hotkey
- screenshot, find_element, move_to, drag_to

All GUI actions default to tier 4 (explicit approval required).

Requires: pip install pyautogui Pillow
"""

from __future__ import annotations

import time
from typing import Dict, Optional

from infrastructure.os_control.risk_tier import RiskTier
from infrastructure.os_control.schemas import (
    GUIAction,
    GUIActionType,
    GUIResult,
)
from utils.log import log_debug, log_error, log_info, log_warning


class GUIController:
    """pyautogui-based GUI controller for desktop automation.

    All actions require explicit user approval (tier 4) before execution.
    pyautogui's FAILSAFE is enabled by default — move mouse to top-left
    corner to abort any GUI action.
    """

    def __init__(self) -> None:
        self._initialized = False
        self._pyautogui = None

    def _ensure_initialized(self) -> None:
        """Lazily import and configure pyautogui on first use."""
        if self._initialized:
            return

        try:
            import pyautogui

            # Enable failsafe: moving mouse to (0, 0) raises FailSafeException
            pyautogui.FAILSAFE = True
            # Small pause between actions for safety
            pyautogui.PAUSE = 0.25

            self._pyautogui = pyautogui
            self._initialized = True
            log_info("[GUI] pyautogui initialized (FAILSAFE=True)")
        except ImportError:
            raise RuntimeError("pyautogui is not installed. Run: pip install pyautogui Pillow")

    def execute(self, action: GUIAction) -> GUIResult:
        """Execute a GUI action.

        Args:
            action: GUIAction describing what to do.

        Returns:
            GUIResult with outcome.
        """
        start_time = time.time()

        try:
            self._ensure_initialized()

            handler = {
                GUIActionType.CLICK: self._click,
                GUIActionType.DOUBLE_CLICK: self._double_click,
                GUIActionType.RIGHT_CLICK: self._right_click,
                GUIActionType.TYPE_TEXT: self._type_text,
                GUIActionType.HOTKEY: self._hotkey,
                GUIActionType.SCREENSHOT: self._screenshot,
                GUIActionType.FIND_ELEMENT: self._find_element,
                GUIActionType.MOVE_TO: self._move_to,
                GUIActionType.DRAG_TO: self._drag_to,
            }.get(action.action)

            if handler is None:
                return GUIResult(
                    action=action.action, success=False,
                    error=f"Unknown GUI action: {action.action}",
                    risk_tier=action.risk_tier,
                )

            result = handler(action)
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            return result

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            log_error(f"[GUI] Action {action.action} failed: {e}")
            return GUIResult(
                action=action.action, success=False,
                error=str(e), execution_time_ms=execution_time_ms,
                risk_tier=action.risk_tier,
            )

    def _click(self, action: GUIAction) -> GUIResult:
        if action.x is None or action.y is None:
            return GUIResult(
                action=action.action, success=False,
                error="x and y coordinates required", risk_tier=action.risk_tier,
            )
        log_info(f"[GUI] Click at ({action.x}, {action.y})")
        self._pyautogui.click(action.x, action.y)
        return GUIResult(
            action=action.action, success=True,
            position={"x": action.x, "y": action.y},
            risk_tier=action.risk_tier,
        )

    def _double_click(self, action: GUIAction) -> GUIResult:
        if action.x is None or action.y is None:
            return GUIResult(
                action=action.action, success=False,
                error="x and y coordinates required", risk_tier=action.risk_tier,
            )
        log_info(f"[GUI] Double-click at ({action.x}, {action.y})")
        self._pyautogui.doubleClick(action.x, action.y)
        return GUIResult(
            action=action.action, success=True,
            position={"x": action.x, "y": action.y},
            risk_tier=action.risk_tier,
        )

    def _right_click(self, action: GUIAction) -> GUIResult:
        if action.x is None or action.y is None:
            return GUIResult(
                action=action.action, success=False,
                error="x and y coordinates required", risk_tier=action.risk_tier,
            )
        log_info(f"[GUI] Right-click at ({action.x}, {action.y})")
        self._pyautogui.rightClick(action.x, action.y)
        return GUIResult(
            action=action.action, success=True,
            position={"x": action.x, "y": action.y},
            risk_tier=action.risk_tier,
        )

    def _type_text(self, action: GUIAction) -> GUIResult:
        if not action.text:
            return GUIResult(
                action=action.action, success=False,
                error="Text required for type_text", risk_tier=action.risk_tier,
            )
        log_info(f"[GUI] Typing {len(action.text)} chars")
        self._pyautogui.typewrite(action.text, interval=0.02)
        return GUIResult(
            action=action.action, success=True,
            risk_tier=action.risk_tier,
        )

    def _hotkey(self, action: GUIAction) -> GUIResult:
        if not action.text:
            return GUIResult(
                action=action.action, success=False,
                error="Hotkey combo required (e.g. 'ctrl+c')", risk_tier=action.risk_tier,
            )
        keys = [k.strip() for k in action.text.split("+")]
        log_info(f"[GUI] Hotkey: {'+'.join(keys)}")
        self._pyautogui.hotkey(*keys)
        return GUIResult(
            action=action.action, success=True,
            risk_tier=action.risk_tier,
        )

    def _screenshot(self, action: GUIAction) -> GUIResult:
        import tempfile
        path = tempfile.mktemp(suffix=".png")
        log_info(f"[GUI] Screenshot → {path}")
        self._pyautogui.screenshot(path)
        return GUIResult(
            action=action.action, success=True,
            content=path, risk_tier=action.risk_tier,
        )

    def _find_element(self, action: GUIAction) -> GUIResult:
        if not action.image_path:
            return GUIResult(
                action=action.action, success=False,
                error="image_path required for find_element",
                risk_tier=action.risk_tier,
            )
        log_info(f"[GUI] Finding element: {action.image_path}")
        location = self._pyautogui.locateOnScreen(
            action.image_path,
            confidence=action.confidence,
        )
        if location:
            center = self._pyautogui.center(location)
            return GUIResult(
                action=action.action, success=True,
                position={"x": center.x, "y": center.y},
                content=f"Found at ({center.x}, {center.y})",
                risk_tier=action.risk_tier,
            )
        return GUIResult(
            action=action.action, success=False,
            error="Element not found on screen",
            risk_tier=action.risk_tier,
        )

    def _move_to(self, action: GUIAction) -> GUIResult:
        if action.x is None or action.y is None:
            return GUIResult(
                action=action.action, success=False,
                error="x and y coordinates required", risk_tier=action.risk_tier,
            )
        self._pyautogui.moveTo(action.x, action.y, duration=0.3)
        return GUIResult(
            action=action.action, success=True,
            position={"x": action.x, "y": action.y},
            risk_tier=action.risk_tier,
        )

    def _drag_to(self, action: GUIAction) -> GUIResult:
        if action.x is None or action.y is None:
            return GUIResult(
                action=action.action, success=False,
                error="x and y (target) coordinates required",
                risk_tier=action.risk_tier,
            )
        log_info(f"[GUI] Drag to ({action.x}, {action.y})")
        self._pyautogui.dragTo(action.x, action.y, duration=0.5)
        return GUIResult(
            action=action.action, success=True,
            position={"x": action.x, "y": action.y},
            risk_tier=action.risk_tier,
        )
