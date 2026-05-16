"""Pony · 星屑回避：操控飞船左右躲避下坠星屑，非平台跳跃类。"""
from __future__ import annotations

import math
import random
import sys
from enum import Enum, auto
from pathlib import Path

import _load_pony  # noqa: F401

import pony_local

pony_local.ensure_repo_on_path(Path(__file__).parent)
pony_local.configure_pycache("game", start=Path(__file__).parent)

import pygame

from constants import (
    COLOR_ACCENT,
    COLOR_BG,
    COLOR_BUTTON,
    COLOR_BUTTON_HOVER,
    COLOR_HAZARD,
    COLOR_HAZARD_CORE,
    COLOR_PLAYER,
    COLOR_STAR_FIELD,
    COLOR_TEXT,
    FPS,
    HIDDEN_GATE_STANDARD,
    HIDDEN_GATE_TWILIGHT,
    PLAYER_H,
    PLAYER_MARGIN_BOTTOM,
    PLAYER_SPEED,
    PLAYER_W,
    SCREEN_H,
    SCREEN_W,
    TITLE,
)
from persistence import SaveManager
from element_hidden import ElementHiddenSession


class Phase(Enum):
    MENU = auto()
    PLAY = auto()
    HIDDEN_INTRO = auto()
    HIDDEN = auto()
    GAME_OVER = auto()


def _fonts() -> tuple[pygame.font.Font, pygame.font.Font, pygame.font.Font]:
    try:
        title = pygame.font.SysFont("microsoftyahei,simhei,simsun", 40)
        body = pygame.font.SysFont("microsoftyahei,simhei,simsun", 24)
        small = pygame.font.SysFont("microsoftyahei,simhei,simsun", 18)
    except Exception:
        title = pygame.font.Font(None, 44)
        body = pygame.font.Font(None, 28)
        small = pygame.font.Font(None, 22)
    return title, body, small


def _letterbox_rect(screen: pygame.Surface) -> pygame.Rect:
    sw, sh = screen.get_size()
    lw, lh = SCREEN_W, SCREEN_H
    if sw <= 0 or sh <= 0:
        return pygame.Rect(0, 0, lw, lh)
    scale = min(sw / lw, sh / lh)
    nw, nh = max(1, int(lw * scale)), max(1, int(lh * scale))
    x = (sw - nw) // 2
    y = (sh - nh) // 2
    return pygame.Rect(x, y, nw, nh)


def _map_screen_to_logical(pos: tuple[int, int], letter: pygame.Rect) -> tuple[int, int]:
    if not letter.collidepoint(pos):
        return -1, -1
    lx = (pos[0] - letter.x) * SCREEN_W / letter.w
    ly = (pos[1] - letter.y) * SCREEN_H / letter.h
    return int(lx), int(ly)


def _present(screen: pygame.Surface, canvas: pygame.Surface) -> pygame.Rect:
    lr = _letterbox_rect(screen)
    if lr.width == SCREEN_W and lr.height == SCREEN_H and lr.x == 0 and lr.y == 0:
        screen.blit(canvas, (0, 0))
    else:
        scaled = pygame.transform.smoothscale(canvas, (lr.width, lr.height))
        screen.fill((6, 8, 14))
        screen.blit(scaled, lr.topleft)
    return lr


def _set_screen_mode(fullscreen: bool) -> pygame.Surface:
    if fullscreen:
        info = pygame.display.Info()
        return pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
    return pygame.display.set_mode((SCREEN_W, SCREEN_H))


def _build_bg_stars(count: int, rng: random.Random) -> list[tuple[int, int, int]]:
    out: list[tuple[int, int, int]] = []
    for _ in range(count):
        x = rng.randint(0, SCREEN_W - 1)
        y = rng.randint(0, SCREEN_H - 1)
        b = rng.randint(45, 120)
        out.append((x, y, b))
    return out


def _draw_bg_stars(surface: pygame.Surface, stars: list[tuple[int, int, int]], drift_y: float) -> None:
    for x, y, b in stars:
        sy = int((y + drift_y) % SCREEN_H)
        pygame.draw.circle(surface, (b // 4, b // 2, min(255, b + 40)), (x, sy), 1)


def _draw_ship(surface: pygame.Surface, rect: pygame.Rect) -> None:
    x, y, w, h = rect.x, rect.y, rect.w, rect.h
    tip = (x + w // 2, y)
    left = (x, y + h)
    right = (x + w, y + h)
    mid = (x + w // 2, y + h - 6)
    pygame.draw.polygon(surface, COLOR_PLAYER, (tip, right, mid, left))
    pygame.draw.polygon(surface, (255, 230, 180), (tip, right, mid, left), 2)


def _draw_hazard(surface: pygame.Surface, rect: pygame.Rect) -> None:
    pygame.draw.ellipse(surface, COLOR_HAZARD, rect)
    pygame.draw.ellipse(surface, COLOR_HAZARD_CORE, rect.inflate(-8, -8))


def main() -> None:
    pygame.init()
    pygame.display.set_caption(TITLE)
    saves = SaveManager()
    clock = pygame.time.Clock()
    is_fullscreen = False
    screen = _set_screen_mode(is_fullscreen)
    letter_rect = _letterbox_rect(screen)
    canvas = pygame.Surface((SCREEN_W, SCREEN_H))
    title_f, body_f, small_f = _fonts()

    phase = Phase.MENU
    rng = random.Random()
    bg_stars = _build_bg_stars(100, random.Random(90210))

    # 游玩状态
    player_x = SCREEN_W * 0.5 - PLAYER_W * 0.5
    hazards: list[pygame.Rect] = []
    hazard_vy: list[float] = []
    spawn_acc = 0.0
    difficulty = 1.0
    score = 0
    survival = 0.0
    last_score_submit = 0
    hidden_2k_used = False
    hidden_10k_used = False
    hidden_pending_mode = ""  # "standard" | "twilight"
    hidden_bonus = 0
    hidden_intro_t = 0.0
    hidden_session: ElementHiddenSession | None = None
    dodge_snapshot_score = 0
    shield_stock = 0
    next_shield_milestone = 500
    shield_flash = 0.0
    play_space_cheat_taps = 0
    play_cheat_active = False
    play_last_space_cheat_ms = 0

    btn_start = pygame.Rect(SCREEN_W // 2 - 120, 320, 240, 48)
    btn_quit = pygame.Rect(SCREEN_W // 2 - 100, 400, 200, 44)
    btn_retry = pygame.Rect(SCREEN_W // 2 - 110, 360, 220, 46)
    btn_menu = pygame.Rect(SCREEN_W // 2 - 110, 420, 220, 44)
    fs_rect = pygame.Rect(SCREEN_W - 248, 10, 108, 36)

    def reset_play() -> None:
        nonlocal player_x, hazards, hazard_vy, spawn_acc, difficulty, score, survival, last_score_submit
        nonlocal hidden_2k_used, hidden_10k_used, hidden_pending_mode, hidden_bonus, hidden_intro_t
        nonlocal hidden_session, dodge_snapshot_score
        nonlocal shield_stock, next_shield_milestone, shield_flash
        nonlocal play_space_cheat_taps, play_cheat_active, play_last_space_cheat_ms
        player_x = SCREEN_W * 0.5 - PLAYER_W * 0.5
        hazards.clear()
        hazard_vy.clear()
        spawn_acc = 0.0
        difficulty = 1.0
        score = 0
        survival = 0.0
        last_score_submit = 0
        hidden_2k_used = False
        hidden_10k_used = False
        hidden_pending_mode = ""
        hidden_bonus = 0
        hidden_intro_t = 0.0
        hidden_session = None
        dodge_snapshot_score = 0
        shield_stock = 0
        next_shield_milestone = 500
        shield_flash = 0.0
        play_space_cheat_taps = 0
        play_cheat_active = False
        play_last_space_cheat_ms = 0

    def draw_corner_fs(mouse: tuple[int, int]) -> None:
        hov = fs_rect.collidepoint(mouse)
        bg = COLOR_BUTTON_HOVER if hov else COLOR_BUTTON
        pygame.draw.rect(canvas, bg, fs_rect, border_radius=6)
        pygame.draw.rect(canvas, COLOR_ACCENT, fs_rect, 2, border_radius=6)
        t = small_f.render("全屏", True, COLOR_TEXT)
        canvas.blit(t, t.get_rect(center=fs_rect.center))

    while True:
        dt = clock.tick(FPS) / 1000.0
        raw_mouse = pygame.mouse.get_pos()
        mouse = _map_screen_to_logical(raw_mouse, letter_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                saves.flush()
                pygame.quit()
                sys.exit(0)

            if event.type == pygame.KEYDOWN:
                alt_fs = event.key == pygame.K_RETURN and (pygame.key.get_mods() & pygame.KMOD_ALT)
                if event.key == pygame.K_F11 or alt_fs:
                    is_fullscreen = not is_fullscreen
                    screen = _set_screen_mode(is_fullscreen)
                    letter_rect = _letterbox_rect(screen)
                if phase == Phase.PLAY and not play_cheat_active and event.key == pygame.K_SPACE:
                    now = pygame.time.get_ticks()
                    if now - play_last_space_cheat_ms > 900:
                        play_space_cheat_taps = 0
                    play_last_space_cheat_ms = now
                    play_space_cheat_taps += 1
                    if play_space_cheat_taps >= 5:
                        play_cheat_active = True
                        play_space_cheat_taps = 0
                if event.key == pygame.K_ESCAPE:
                    if phase == Phase.HIDDEN:
                        hidden_session = None
                        saves.flush()
                        phase = Phase.MENU
                    elif phase not in (Phase.MENU, Phase.HIDDEN_INTRO):
                        saves.flush()
                        phase = Phase.MENU

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                ep = _map_screen_to_logical(event.pos, letter_rect)
                if fs_rect.collidepoint(ep):
                    is_fullscreen = not is_fullscreen
                    screen = _set_screen_mode(is_fullscreen)
                    letter_rect = _letterbox_rect(screen)
                    continue
                if phase == Phase.MENU:
                    if btn_start.collidepoint(ep):
                        reset_play()
                        phase = Phase.PLAY
                    elif btn_quit.collidepoint(ep):
                        saves.flush()
                        pygame.quit()
                        sys.exit(0)
                elif phase == Phase.GAME_OVER:
                    if btn_retry.collidepoint(ep):
                        reset_play()
                        phase = Phase.PLAY
                    elif btn_menu.collidepoint(ep):
                        phase = Phase.MENU

        canvas.fill(COLOR_BG)
        drift = (pygame.time.get_ticks() * 0.02) % SCREEN_H
        _draw_bg_stars(canvas, bg_stars, drift)

        if phase == Phase.MENU:
            t = title_f.render("Pony · 星屑回避", True, COLOR_TEXT)
            canvas.blit(t, t.get_rect(center=(SCREEN_W // 2, 160)))
            sub = body_f.render("左右移动躲避下坠星屑，坚持越久分数越高", True, COLOR_ACCENT)
            canvas.blit(sub, sub.get_rect(center=(SCREEN_W // 2, 230)))
            best = body_f.render(f"历史最高分: {saves.data.best_score}", True, COLOR_TEXT)
            canvas.blit(best, best.get_rect(center=(SCREEN_W // 2, 270)))

            for r, label, base in (
                (btn_start, "开始游戏", COLOR_BUTTON),
                (btn_quit, "退出", (70, 55, 65)),
            ):
                hov = r.collidepoint(mouse)
                pygame.draw.rect(
                    canvas,
                    COLOR_BUTTON_HOVER if hov and base == COLOR_BUTTON else base,
                    r,
                    border_radius=8,
                )
                pygame.draw.rect(canvas, COLOR_ACCENT, r, 2, border_radius=8)
                tx = body_f.render(label, True, COLOR_TEXT)
                canvas.blit(tx, tx.get_rect(center=r.center))

            hint = small_f.render(
                f"A D / 方向键 · 每500分+1盾牌 · {HIDDEN_GATE_STANDARD}/{HIDDEN_GATE_TWILIGHT} 分两档进余晖 · F11 全屏",
                True,
                COLOR_STAR_FIELD,
            )
            canvas.blit(hint, hint.get_rect(center=(SCREEN_W // 2, 500)))
            draw_corner_fs(mouse)

        elif phase == Phase.PLAY:
            shield_flash = max(0.0, shield_flash - dt)
            sd = dt * 10.0 if play_cheat_active else dt
            keys = pygame.key.get_pressed()
            dx = 0.0
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                dx -= 1.0
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx += 1.0
            player_x += dx * PLAYER_SPEED * sd
            margin = 16
            player_x = max(margin, min(SCREEN_W - PLAYER_W - margin, player_x))

            survival += sd
            difficulty = 1.0 + survival * 0.08
            base_score = int(survival * 18 + math.sin(survival) * 3)
            score = base_score + hidden_bonus

            if not play_cheat_active:
                while score >= next_shield_milestone:
                    shield_stock += 1
                    next_shield_milestone += 500

            enter_hidden = ""
            if score >= HIDDEN_GATE_TWILIGHT and not hidden_10k_used:
                enter_hidden = "twilight"
            elif score >= HIDDEN_GATE_STANDARD and not hidden_2k_used:
                enter_hidden = "standard"

            if enter_hidden:
                if enter_hidden == "twilight":
                    hidden_10k_used = True
                else:
                    hidden_2k_used = True
                hidden_pending_mode = enter_hidden
                dodge_snapshot_score = score
                phase = Phase.HIDDEN_INTRO
                hidden_intro_t = 0.0
            else:
                spawn_acc += sd * (1.4 + difficulty * 0.55)
                while spawn_acc >= 1.0:
                    spawn_acc -= 1.0
                    w = rng.randint(28, 52)
                    h = rng.randint(22, 40)
                    x = rng.randint(20, SCREEN_W - w - 20)
                    hazards.append(pygame.Rect(x, -h - 10, w, h))
                    hazard_vy.append(120.0 + rng.uniform(0, 180) * difficulty)

                py = int(SCREEN_H - PLAYER_MARGIN_BOTTOM - PLAYER_H)
                player_rect = pygame.Rect(int(player_x), py, PLAYER_W, PLAYER_H)

                dead = False
                new_h: list[pygame.Rect] = []
                new_v: list[float] = []
                for r, vy in zip(hazards, hazard_vy):
                    nr = r.move(0, int(vy * sd))
                    if nr.top > SCREEN_H + 40:
                        continue
                    if nr.colliderect(player_rect.inflate(-8, -10)):
                        if play_cheat_active:
                            shield_flash = max(shield_flash, 0.35)
                            continue
                        if shield_stock > 0:
                            shield_stock -= 1
                            shield_flash = 0.45
                            continue
                        dead = True
                    new_h.append(nr)
                    new_v.append(vy)
                hazards, hazard_vy = new_h, new_v

                if dead:
                    saves.maybe_update_best(score)
                    saves.flush()
                    last_score_submit = score
                    phase = Phase.GAME_OVER

            if phase == Phase.PLAY:
                py = int(SCREEN_H - PLAYER_MARGIN_BOTTOM - PLAYER_H)
                player_rect = pygame.Rect(int(player_x), py, PLAYER_W, PLAYER_H)
                for r in hazards:
                    _draw_hazard(canvas, r)
                if shield_flash > 0:
                    pygame.draw.circle(
                        canvas,
                        (120, 230, 255),
                        player_rect.center,
                        max(player_rect.w, player_rect.h) // 2 + 22,
                        3,
                    )
                elif play_cheat_active:
                    pygame.draw.circle(
                        canvas,
                        (255, 220, 140),
                        player_rect.center,
                        max(player_rect.w, player_rect.h) // 2 + 26,
                        2,
                    )
                elif shield_stock > 0:
                    pygame.draw.circle(
                        canvas,
                        (70, 160, 200),
                        player_rect.center,
                        max(player_rect.w, player_rect.h) // 2 + 18,
                        2,
                    )
                _draw_ship(canvas, player_rect)

                sc = body_f.render(f"分数 {score}", True, COLOR_TEXT)
                canvas.blit(sc, (16, 12))
                tm = small_f.render(f"存活 {survival:.1f}s  ·  难度 x{difficulty:.2f}", True, COLOR_ACCENT)
                canvas.blit(tm, (16, 44))
                if play_cheat_active:
                    sh_line = small_f.render(
                        "盾牌 ∞（无限之盾）· 游戏 10x 加速（彩蛋已开启）",
                        True,
                        (255, 220, 120),
                    )
                else:
                    sh_line = small_f.render(
                        f"盾牌 {shield_stock}  ·  每500分+1层（抵消一次致死撞击）",
                        True,
                        (140, 220, 255),
                    )
                canvas.blit(sh_line, (16, 66))
                if hidden_bonus > 0:
                    hb = small_f.render(f"余晖通关奖励 +{hidden_bonus}", True, (180, 255, 180))
                    canvas.blit(hb, (16, 90))
                draw_corner_fs(mouse)

        elif phase == Phase.HIDDEN_INTRO:
            hidden_intro_t += dt
            canvas.fill(COLOR_BG)
            drift = (pygame.time.get_ticks() * 0.02) % SCREEN_H
            _draw_bg_stars(canvas, bg_stars, drift)
            dim = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            dim.fill((0, 0, 0, min(200, int(hidden_intro_t * 100))))
            canvas.blit(dim, (0, 0))
            if hidden_pending_mode == "twilight":
                t1 = title_f.render("隐藏关 · 元素余晖（终焉）", True, (255, 215, 160))
                t2 = body_f.render(
                    "难度×2 · 敌存活10s · 时长∞ · 生生不息（200血、每秒+1）",
                    True,
                    COLOR_ACCENT,
                )
                t3 = small_f.render(
                    f"分数≥{HIDDEN_GATE_TWILIGHT} · 火柴人 W/↑ 跳 · 传送器×2 · 木弹回血",
                    True,
                    COLOR_TEXT,
                )
            else:
                t1 = title_f.render("隐藏关 · 元素余晖", True, (255, 215, 160))
                t2 = body_f.render(
                    "标准难度 · 敌存活5s · 坚持55秒通关 · 生命100",
                    True,
                    COLOR_ACCENT,
                )
                t3 = small_f.render(
                    f"分数≥{HIDDEN_GATE_STANDARD} · 火柴人 W/↑ 跳 · 传送器×2 · 木弹回血",
                    True,
                    COLOR_TEXT,
                )
            canvas.blit(t1, t1.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 60)))
            canvas.blit(t2, t2.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 5)))
            canvas.blit(t3, t3.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 40)))
            if hidden_intro_t >= 2.4:
                phase = Phase.HIDDEN
                if hidden_pending_mode == "twilight":
                    hidden_session = ElementHiddenSession.create_twilight(rng)
                else:
                    hidden_session = ElementHiddenSession.create_standard(rng)
                hidden_pending_mode = ""
            draw_corner_fs(mouse)

        elif phase == Phase.HIDDEN:
            hs = hidden_session
            if hs is None:
                phase = Phase.MENU
            else:
                keys = pygame.key.get_pressed()
                res = hs.update(dt, keys)
                hs.draw(canvas, title_f, body_f, small_f)
                if res == "dead":
                    saves.maybe_update_best(dodge_snapshot_score)
                    saves.flush()
                    last_score_submit = dodge_snapshot_score
                    phase = Phase.GAME_OVER
                    hidden_session = None
                elif res == "won":
                    hidden_bonus += 1200
                    phase = Phase.PLAY
                    hidden_session = None
                draw_corner_fs(mouse)

        elif phase == Phase.GAME_OVER:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            canvas.blit(overlay, (0, 0))

            t = title_f.render("星屑撞击", True, COLOR_HAZARD_CORE)
            canvas.blit(t, t.get_rect(center=(SCREEN_W // 2, 220)))
            s = body_f.render(f"本局分数 {last_score_submit}    最高 {saves.data.best_score}", True, COLOR_TEXT)
            canvas.blit(s, s.get_rect(center=(SCREEN_W // 2, 290)))

            for r, label in ((btn_retry, "再来一局"), (btn_menu, "返回菜单")):
                hov = r.collidepoint(mouse)
                pygame.draw.rect(canvas, COLOR_BUTTON_HOVER if hov else COLOR_BUTTON, r, border_radius=8)
                pygame.draw.rect(canvas, COLOR_ACCENT, r, 2, border_radius=8)
                tx = body_f.render(label, True, COLOR_TEXT)
                canvas.blit(tx, tx.get_rect(center=r.center))

            draw_corner_fs(mouse)

        letter_rect = _present(screen, canvas)
        pygame.display.flip()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
