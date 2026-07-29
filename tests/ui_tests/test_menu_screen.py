"""
test_menu_screen.py
Covers: view/menu_screen.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import cv2
from view.menu_screen import MenuScreen


def _center(rect):
    x1, y1, x2, y2 = rect
    return (x1 + x2) // 2, (y1 + y2) // 2


# ── error display ────────────────────────────────────────────────────────────

def test_constructor_stores_error():
    menu = MenuScreen(error="That room doesn't exist.")
    assert menu._error == "That room doesn't exist."


def test_constructor_defaults_to_no_error():
    menu = MenuScreen()
    assert menu._error is None


# ── main screen hit-testing ─────────────────────────────────────────────────

def test_click_play_sets_quick_match_result():
    menu = MenuScreen()
    x, y = _center(menu._play_rect())
    menu._on_mouse(cv2.EVENT_LBUTTONDOWN, x, y, 0, None)
    assert menu._result == ("quick_match", None)


def test_click_room_transitions_to_room_screen():
    menu = MenuScreen()
    x, y = _center(menu._room_rect())
    menu._on_mouse(cv2.EVENT_LBUTTONDOWN, x, y, 0, None)
    assert menu._screen == "room"
    assert menu._result is None


def test_click_outside_buttons_does_nothing():
    menu = MenuScreen()
    menu._on_mouse(cv2.EVENT_LBUTTONDOWN, 1, 1, 0, None)
    assert menu._result is None
    assert menu._screen == "main"


def test_mouse_move_updates_hover():
    menu = MenuScreen()
    x, y = _center(menu._play_rect())
    menu._on_mouse(cv2.EVENT_MOUSEMOVE, x, y, 0, None)
    assert menu._hover == "play"


def test_mouse_move_off_buttons_clears_hover():
    menu = MenuScreen()
    menu._hover = "play"
    menu._on_mouse(cv2.EVENT_MOUSEMOVE, 1, 1, 0, None)
    assert menu._hover is None


# ── room screen: typing ──────────────────────────────────────────────────────

def test_typing_appends_to_room_code():
    menu = MenuScreen()
    menu._screen = "room"
    for ch in "abc123":
        menu._handle_key(ord(ch))
    assert menu._room_code == "abc123"


def test_backspace_trims_room_code():
    menu = MenuScreen()
    menu._screen = "room"
    menu._room_code = "abc"
    menu._handle_key(8)
    assert menu._room_code == "ab"


def test_backspace_on_empty_code_does_not_crash():
    menu = MenuScreen()
    menu._screen = "room"
    menu._handle_key(8)
    assert menu._room_code == ""


def test_enter_submits_join_when_code_present():
    menu = MenuScreen()
    menu._screen = "room"
    menu._room_code = "xyz"
    menu._handle_key(13)
    assert menu._result == ("join", "xyz")


def test_enter_does_nothing_when_code_empty():
    menu = MenuScreen()
    menu._screen = "room"
    menu._handle_key(13)
    assert menu._result is None


def test_room_code_length_is_capped():
    menu = MenuScreen()
    menu._screen = "room"
    for _ in range(100):
        menu._handle_key(ord('a'))
    assert len(menu._room_code) <= 40


# ── room screen: buttons ─────────────────────────────────────────────────────

def test_click_create_sets_create_result():
    menu = MenuScreen()
    menu._screen = "room"
    x, y = _center(menu._create_rect())
    menu._on_mouse(cv2.EVENT_LBUTTONDOWN, x, y, 0, None)
    assert menu._result == ("create", None)


def test_click_create_with_typed_code_uses_it_as_custom_name():
    menu = MenuScreen()
    menu._screen = "room"
    menu._room_code = "efrat_room"
    x, y = _center(menu._create_rect())
    menu._on_mouse(cv2.EVENT_LBUTTONDOWN, x, y, 0, None)
    assert menu._result == ("create", "efrat_room")


def test_click_join_without_code_does_nothing():
    menu = MenuScreen()
    menu._screen = "room"
    x, y = _center(menu._join_rect())
    menu._on_mouse(cv2.EVENT_LBUTTONDOWN, x, y, 0, None)
    assert menu._result is None


def test_click_join_with_code_sets_join_result():
    menu = MenuScreen()
    menu._screen = "room"
    menu._room_code = "abc123"
    x, y = _center(menu._join_rect())
    menu._on_mouse(cv2.EVENT_LBUTTONDOWN, x, y, 0, None)
    assert menu._result == ("join", "abc123")


def test_click_back_returns_to_main_and_clears_code():
    menu = MenuScreen()
    menu._screen = "room"
    menu._room_code = "abc"
    x, y = _center(menu._back_rect())
    menu._on_mouse(cv2.EVENT_LBUTTONDOWN, x, y, 0, None)
    assert menu._screen == "main"
    assert menu._room_code == ""
