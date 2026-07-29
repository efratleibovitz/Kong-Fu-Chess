"""
test_overlay_renderer.py
Covers: view/renderers/overlay_renderer.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
from unittest.mock import MagicMock, patch
from view.renderers.overlay_renderer import OverlayRenderer
from view.render_state import RenderState, PlayerRenderInfo


def _player(name='White', score=0):
    return PlayerRenderInfo(name=name, score=score, captured=[], move_history=[])


def _make_rs(loser=None, white_score=5, black_score=3):
    return RenderState(
        num_cols=8, num_rows=8,
        pieces=[], selected_col=None, selected_row=None,
        pending_destinations=[],
        clock_ms=0,
        white=_player('White', white_score),
        black=_player('Black', black_score),
        game_over=loser is not None,
        loser=loser,
    )


def _make_renderer():
    with patch('view.renderers.overlay_renderer.Img') as MockImg:
        mock_bg = MagicMock()
        mock_bg.img = np.zeros((800, 800, 3), dtype=np.uint8)
        MockImg.return_value.read.return_value = mock_bg
        renderer = OverlayRenderer(800, 800)
        renderer._bg = mock_bg
    return renderer


def _make_canvas():
    canvas = MagicMock()
    canvas.img = np.zeros((800, 800, 3), dtype=np.uint8)
    canvas.put_text = MagicMock()
    canvas.draw_rect = MagicMock()
    return canvas


# ── draw_start ────────────────────────────────────────────────────────────────

def test_draw_start_calls_put_text_twice():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_start(canvas)
    assert canvas.put_text.call_count == 2

def test_draw_start_shows_title():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_start(canvas)
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('KONG' in t for t in texts)

def test_draw_start_shows_click_to_start():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_start(canvas)
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('Click' in t or 'start' in t.lower() for t in texts)


# ── draw_win ──────────────────────────────────────────────────────────────────

def test_draw_win_shows_game_over():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_win(canvas, _make_rs(loser='b'))
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('GAME' in t for t in texts)

def test_draw_win_white_wins_when_black_loses():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_win(canvas, _make_rs(loser='b'))
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('White' in t for t in texts)

def test_draw_win_black_wins_when_white_loses():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_win(canvas, _make_rs(loser='w'))
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('Black' in t for t in texts)

def test_draw_win_shows_score():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_win(canvas, _make_rs(loser='b', white_score=7))
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('7' in t for t in texts)

def test_draw_win_no_crash_when_loser_is_none():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_win(canvas, _make_rs(loser=None))


# ── draw_main_menu ────────────────────────────────────────────────────────────

def test_draw_main_menu_shows_title():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_main_menu(canvas, (0, 0, 10, 10), (0, 20, 10, 30))
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('KONG' in t for t in texts)


def test_draw_main_menu_draws_two_buttons():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_main_menu(canvas, (0, 0, 10, 10), (0, 20, 10, 30))
    assert canvas.draw_rect.call_count == 2
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('PLAY' in t for t in texts)
    assert any('ROOM' in t for t in texts)


def test_draw_main_menu_hover_does_not_crash():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_main_menu(canvas, (0, 0, 10, 10), (0, 20, 10, 30), hover="play")


def test_draw_main_menu_shows_error_when_given():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_main_menu(canvas, (0, 0, 10, 10), (0, 20, 10, 30), error="That room doesn't exist.")
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any("doesn't exist" in t for t in texts)


def test_draw_main_menu_no_error_text_when_none():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_main_menu(canvas, (0, 0, 10, 10), (0, 20, 10, 30))
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert len(texts) == 3  # title + 2 button labels, no error line


# ── draw_room_menu ────────────────────────────────────────────────────────────

def test_draw_room_menu_shows_room_code():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_room_menu(
            canvas, "abc123", (0, 0, 10, 10),
            (0, 20, 10, 30), (0, 40, 10, 50), (0, 60, 10, 70),
            cursor_visible=True,
        )
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('abc123' in t for t in texts)


def test_draw_room_menu_draws_code_box_and_three_buttons():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_room_menu(
            canvas, "", (0, 0, 10, 10),
            (0, 20, 10, 30), (0, 40, 10, 50), (0, 60, 10, 70),
            cursor_visible=False,
        )
    assert canvas.draw_rect.call_count == 4  # code box + create + join + back
    texts = [c[0][0] for c in canvas.put_text.call_args_list]
    assert any('CREATE' in t for t in texts)
    assert any('JOIN' in t for t in texts)
    assert any('BACK' in t for t in texts)


def test_draw_room_menu_cursor_toggles_trailing_bar():
    renderer = _make_renderer()
    canvas_on = _make_canvas()
    canvas_off = _make_canvas()
    with patch('cv2.addWeighted'):
        renderer.draw_room_menu(
            canvas_on, "abc", (0, 0, 10, 10),
            (0, 20, 10, 30), (0, 40, 10, 50), (0, 60, 10, 70),
            cursor_visible=True,
        )
        renderer.draw_room_menu(
            canvas_off, "abc", (0, 0, 10, 10),
            (0, 20, 10, 30), (0, 40, 10, 50), (0, 60, 10, 70),
            cursor_visible=False,
        )
    texts_on = [c[0][0] for c in canvas_on.put_text.call_args_list]
    texts_off = [c[0][0] for c in canvas_off.put_text.call_args_list]
    assert any(t == 'abc|' for t in texts_on)
    assert any(t == 'abc' for t in texts_off)


# ── _draw_dimmed_bg ───────────────────────────────────────────────────────────

def test_dimmed_bg_calls_add_weighted():
    renderer = _make_renderer()
    canvas = _make_canvas()
    with patch('cv2.addWeighted') as mock_blend:
        renderer._draw_dimmed_bg(canvas)
        mock_blend.assert_called_once()
