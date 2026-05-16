"""隐藏关：元素余晖 — 火柴人、跳跃，躲避九种元素怪。"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto

import pygame

from constants import (
    COLOR_ACCENT,
    COLOR_TEXT,
    SCREEN_H,
    SCREEN_W,
)


class ElementKind(Enum):
    WATER = auto()  # 水：攻速快
    FIRE = auto()  # 火：持续伤
    YIN = auto()  # 阴：远程
    YANG = auto()  # 阳：远程
    METAL = auto()  # 金：高伤
    WOOD = auto()  # 木：自愈
    EARTH = auto()  # 土：高血
    WIND = auto()  # 风：速度快
    THUNDER = auto()  # 雷：第九种，预警后直线打击


ALL_KINDS: tuple[ElementKind, ...] = tuple(ElementKind)


@dataclass
class Projectile:
    rect: pygame.Rect
    vx: float
    vy: float
    damage: float
    life: float
    color: tuple[int, int, int]
    burn: bool = False
    wood_heal: bool = False


@dataclass
class ThunderStrike:
    x: float
    t: float
    phase: str  # warn | hit
    damage: float = 38.0
    hit_done: bool = False


WOOD_BULLET_HEAL = 12.0
ENEMY_LIFETIME = 5.0
TELEPORT_PAD_W = 44
TELEPORT_PAD_H = 14
TELEPORT_DOUBLE_GAP = 0.45
TELEPORT_PICKUP_R = 72.0


@dataclass
class Enemy:
    kind: ElementKind
    x: float
    y: float
    w: int
    h: int
    hp: float
    max_hp: float
    vx: float
    vy: float
    t: float = 0.0
    cd: float = 0.0
    age: float = 0.0


@dataclass
class ElementHiddenSession:
    rng: random.Random
    ground_y: int = field(default_factory=lambda: SCREEN_H - 88)
    player_x: float = field(default_factory=lambda: SCREEN_W * 0.5)
    player_y: float = 0.0
    vel_x: float = 0.0
    vel_y: float = 0.0
    on_ground: bool = False
    facing: int = 1
    hp: float = 100.0
    max_hp: float = 100.0
    burn_stacks: float = 0.0
    burn_tick: float = 0.0
    time: float = 0.0
    spawn_acc: float = 0.0
    enemies: list[Enemy] = field(default_factory=list)
    projectiles: list[Projectile] = field(default_factory=list)
    thunders: list[ThunderStrike] = field(default_factory=list)
    hit_flash: float = 0.0
    heal_flash: float = 0.0
    win_time: float = 55.0
    enemy_lifetime: float = ENEMY_LIFETIME
    difficulty_mult: float = 1.0
    endless_vitality: bool = False
    regen_acc: float = 0.0
    jump_released: bool = True
    tele_inventory: int = 2
    tele_pads: list[pygame.Rect | None] = field(default_factory=lambda: [None, None])
    tele_last_tap: float = -100.0
    prev_space: bool = False
    prev_one: bool = False

    @classmethod
    def create_standard(cls, rng: random.Random) -> ElementHiddenSession:
        """2000 分余晖：标准难度，坚持 55 秒通关，100 生命。"""
        s = cls(rng)
        s.max_hp = 100.0
        s.hp = 100.0
        s.enemy_lifetime = ENEMY_LIFETIME
        s.win_time = 55.0
        s.difficulty_mult = 1.0
        s.endless_vitality = False
        return s

    @classmethod
    def create_twilight(cls, rng: random.Random) -> ElementHiddenSession:
        """10000 分余晖：难度×2、敌存活 10s、无限时长、生生不息。"""
        s = cls(rng)
        s.max_hp = 200.0
        s.hp = 200.0
        s.enemy_lifetime = 10.0
        s.win_time = math.inf
        s.difficulty_mult = 2.0
        s.endless_vitality = True
        s.regen_acc = 0.0
        return s

    def __post_init__(self) -> None:
        self.player_y = float(self.ground_y - 72)

    def _stick_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.player_x - 14), int(self.player_y), 28, 72)

    def _feet_rect(self, pr: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(pr.centerx - 12, pr.bottom - 10, 24, 12)

    def _pad_under_feet(self, feet: pygame.Rect) -> int | None:
        for i, p in enumerate(self.tele_pads):
            if p is not None and feet.colliderect(p):
                return i
        return None

    def _place_next_pad(self) -> None:
        if self.tele_inventory <= 0:
            return
        slot = 0 if self.tele_pads[0] is None else (1 if self.tele_pads[1] is None else -1)
        if slot < 0:
            return
        x = int(self.player_x - TELEPORT_PAD_W // 2)
        y = self.ground_y - TELEPORT_PAD_H
        r = pygame.Rect(x, y, TELEPORT_PAD_W, TELEPORT_PAD_H)
        r.x = max(20, min(SCREEN_W - TELEPORT_PAD_W - 20, r.x))
        self.tele_pads[slot] = r
        self.tele_inventory -= 1

    def _try_pickup_pad(self) -> None:
        if self.tele_inventory >= 2:
            return
        bx, by = self.player_x, float(self.player_y + 62)
        for i in range(2):
            p = self.tele_pads[i]
            if p is None:
                continue
            cx, cy = float(p.centerx), float(p.centery)
            if math.hypot(bx - cx, by - cy) <= TELEPORT_PICKUP_R:
                self.tele_pads[i] = None
                self.tele_inventory += 1
                return

    def update(self, dt: float, keys: pygame.key.ScancodeWrapper) -> str | None:
        """返回 'won' | 'dead' | None"""
        self.time += dt
        self.hit_flash = max(0.0, self.hit_flash - dt * 4)
        self.heal_flash = max(0.0, self.heal_flash - dt * 4)

        # 火 DOT
        if self.burn_stacks > 0:
            self.burn_tick += dt
            if self.burn_tick >= 0.35:
                self.burn_tick = 0.0
                self.hp -= 2.0 + self.burn_stacks * 1.2
                self.burn_stacks = max(0.0, self.burn_stacks - 0.15)
        else:
            self.burn_tick = 0.0

        # 生生不息：每秒 +1 生命（满血不叠）
        if self.endless_vitality and self.hp < self.max_hp:
            self.regen_acc += dt
            while self.regen_acc >= 1.0 and self.hp < self.max_hp:
                self.regen_acc -= 1.0
                self.hp = min(self.max_hp, self.hp + 1.0)

        dm = self.difficulty_mult

        # 移动
        move = 0.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move -= 1.0
            self.facing = -1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move += 1.0
            self.facing = 1
        speed = 280.0
        self.vel_x = move * speed
        self.player_x += self.vel_x * dt
        self.player_x = max(40.0, min(float(SCREEN_W - 40), self.player_x))

        pr = self._stick_rect()
        feet = self._feet_rect(pr)
        stand_idx = self._pad_under_feet(feet)

        space_edge = keys[pygame.K_SPACE] and not self.prev_space
        one_edge = keys[pygame.K_1] and not self.prev_one
        self.prev_space = bool(keys[pygame.K_SPACE])
        self.prev_one = bool(keys[pygame.K_1])

        if one_edge:
            self._try_pickup_pad()

        both_pads = self.tele_pads[0] is not None and self.tele_pads[1] is not None
        if space_edge:
            if stand_idx is not None and both_pads:
                if self.time - self.tele_last_tap <= TELEPORT_DOUBLE_GAP:
                    other = 1 - stand_idx
                    tgt = self.tele_pads[other]
                    if tgt is not None:
                        self.player_x = float(tgt.centerx)
                        self.vel_y = 0.0
                    self.tele_last_tap = -100.0
                else:
                    self.tele_last_tap = self.time
            elif self.tele_inventory > 0 and self.on_ground and stand_idx is None:
                self._place_next_pad()
                self.jump_released = False
            elif (
                self.on_ground
                and self.jump_released
                and stand_idx is None
                and self.tele_inventory == 0
            ):
                self.vel_y = -560.0
                self.on_ground = False
                self.jump_released = False

        # 跳跃：W/上 任意地面可跳；空格仅在不需放置时作为跳跃（站上双次空格用于传送）
        jump_keys = keys[pygame.K_w] or keys[pygame.K_UP]
        can_space_jump = (
            keys[pygame.K_SPACE]
            and stand_idx is None
            and self.tele_inventory == 0
            and not space_edge
        )
        if not jump_keys and not keys[pygame.K_SPACE]:
            self.jump_released = True
        elif self.on_ground and self.jump_released and (jump_keys or can_space_jump):
            self.vel_y = -560.0
            self.on_ground = False
            self.jump_released = False

        self.vel_y += 2350.0 * dt
        self.player_y += self.vel_y * dt
        floor = float(self.ground_y - 72)
        if self.player_y >= floor:
            self.player_y = floor
            self.vel_y = 0.0
            self.on_ground = True

        pr = self._stick_rect()

        # 敌人（存活至多 enemy_lifetime 秒）
        for e in self.enemies:
            e.age += dt
        self.enemies = [e for e in self.enemies if e.age < self.enemy_lifetime]

        for e in self.enemies:
            e.t += dt
            dx = self.player_x - (e.x + e.w * 0.5)
            dy = self.player_y + 36 - (e.y + e.h * 0.5)
            dist = max(1.0, math.hypot(dx, dy))
            nx, ny = dx / dist, dy / dist
            spd = {
                ElementKind.WIND: 95.0,
                ElementKind.EARTH: 28.0,
                ElementKind.WOOD: 40.0,
                ElementKind.WATER: 55.0,
                ElementKind.FIRE: 50.0,
                ElementKind.METAL: 45.0,
                ElementKind.YIN: 38.0,
                ElementKind.YANG: 48.0,
                ElementKind.THUNDER: 35.0,
            }[e.kind]
            e.x += nx * spd * dm * dt
            e.y += ny * spd * 0.35 * dm * dt

            # 木：自愈
            if e.kind == ElementKind.WOOD and e.hp < e.max_hp:
                e.hp = min(e.max_hp, e.hp + 9.0 * dt)

            er = pygame.Rect(int(e.x), int(e.y), e.w, e.h)
            if pr.colliderect(er):
                dmg = {
                    ElementKind.METAL: 42.0,
                    ElementKind.FIRE: 8.0,
                    ElementKind.EARTH: 18.0,
                    ElementKind.WIND: 12.0,
                    ElementKind.WATER: 10.0,
                    ElementKind.WOOD: 7.0,
                    ElementKind.YIN: 9.0,
                    ElementKind.YANG: 9.0,
                    ElementKind.THUNDER: 11.0,
                }[e.kind]
                self._hurt(dmg * dt * 3.5 * dm, fire=e.kind == ElementKind.FIRE)

            e.cd -= dt
            self._enemy_attack(e)

        # 雷
        for ts in list(self.thunders):
            ts.t += dt
            if ts.phase == "warn" and ts.t >= 0.42:
                ts.phase = "hit"
                ts.t = 0.0
            elif ts.phase == "hit":
                band = pygame.Rect(int(ts.x - 18), 0, 36, SCREEN_H)
                if not ts.hit_done and pr.colliderect(band):
                    self._hurt(ts.damage, fire=False)
                    ts.hit_done = True
                if ts.t >= 0.12:
                    self.thunders.remove(ts)

        # 弹道
        newp: list[Projectile] = []
        for p in self.projectiles:
            p.rect.x += int(p.vx * dt)
            p.rect.y += int(p.vy * dt)
            p.life -= dt
            if p.life <= 0 or p.rect.right < 0 or p.rect.left > SCREEN_W or p.rect.bottom < 0:
                continue
            if pr.colliderect(p.rect):
                if p.wood_heal:
                    self.hp = min(self.max_hp, self.hp + WOOD_BULLET_HEAL * dm)
                    self.burn_stacks = max(0.0, self.burn_stacks - 0.4)
                    self.heal_flash = 0.4
                else:
                    self._hurt(p.damage * dm, fire=p.burn)
                continue
            newp.append(p)
        self.projectiles = newp

        # 生成（难度倍率：刷怪更快、同屏更多）
        rate = max(0.28, (1.85 - self.time * 0.018) / dm)
        cap = int(14 * dm)
        self.spawn_acc += dt
        while self.spawn_acc >= rate and len(self.enemies) < cap:
            self.spawn_acc -= rate
            self._spawn_one()

        if self.hp <= 0:
            return "dead"
        if math.isfinite(self.win_time) and self.time >= self.win_time:
            return "won"
        return None

    def _hurt(self, amount: float, fire: bool = False) -> None:
        self.hp -= amount
        self.hit_flash = 1.0
        if fire:
            self.burn_stacks = min(8.0, self.burn_stacks + 0.35)

    def _enemy_attack(self, e: Enemy) -> None:
        if e.cd > 0:
            return
        cx, cy = e.x + e.w * 0.5, e.y + e.h * 0.5
        px, py = self.player_x, self.player_y + 30
        dx, dy = px - cx, py - cy
        dist = max(1.0, math.hypot(dx, dy))
        dx, dy = dx / dist * 260.0, dy / dist * 260.0

        if e.kind == ElementKind.WATER:
            e.cd = 0.32
            self.projectiles.append(
                Projectile(pygame.Rect(int(cx), int(cy), 10, 10), dx, dy, 9.0, 2.2, (100, 180, 255))
            )
        elif e.kind == ElementKind.FIRE:
            e.cd = 0.55
            self.projectiles.append(
                Projectile(pygame.Rect(int(cx), int(cy), 14, 14), dx * 0.85, dy * 0.85, 11.0, 1.8, (255, 120, 60), burn=True)
            )
        elif e.kind == ElementKind.YIN:
            e.cd = 0.7
            self.projectiles.append(
                Projectile(pygame.Rect(int(cx), int(cy), 16, 16), dx * 0.65, dy * 0.65, 13.0, 3.5, (120, 80, 160))
            )
        elif e.kind == ElementKind.YANG:
            e.cd = 0.5
            self.projectiles.append(
                Projectile(pygame.Rect(int(cx), int(cy), 12, 12), dx * 1.05, dy * 1.05, 12.0, 2.4, (255, 240, 160))
            )
        elif e.kind == ElementKind.METAL:
            e.cd = 1.1
            self.projectiles.append(
                Projectile(pygame.Rect(int(cx), int(cy), 22, 10), dx * 0.75, dy * 0.75, 26.0, 2.0, (200, 200, 220))
            )
        elif e.kind == ElementKind.WOOD:
            e.cd = 0.9
            self.projectiles.append(
                Projectile(
                    pygame.Rect(int(cx), int(cy), 12, 12),
                    dx * 0.55,
                    dy * 0.55,
                    0.0,
                    2.6,
                    (90, 200, 120),
                    wood_heal=True,
                )
            )
        elif e.kind == ElementKind.EARTH:
            e.cd = 1.4
            self.projectiles.append(
                Projectile(pygame.Rect(int(cx), int(cy), 20, 18), dx * 0.45, dy * 0.45, 16.0, 2.8, (160, 130, 90))
            )
        elif e.kind == ElementKind.WIND:
            e.cd = 0.4
            self.projectiles.append(
                Projectile(pygame.Rect(int(cx), int(cy), 8, 8), dx * 1.2, dy * 1.2, 7.0, 1.5, (180, 255, 220))
            )
        elif e.kind == ElementKind.THUNDER:
            e.cd = 1.25
            tx = self.player_x + self.rng.uniform(-80, 80)
            tx = max(60.0, min(float(SCREEN_W - 60), tx))
            self.thunders.append(ThunderStrike(tx, 0.0, "warn"))

    def _spawn_one(self) -> None:
        k = self.rng.choice(ALL_KINDS)
        side = self.rng.choice(["top", "left", "right"])
        if side == "top":
            x, y = float(self.rng.randint(80, SCREEN_W - 120)), -40.0
        elif side == "left":
            x, y = -30.0, float(self.rng.randint(80, SCREEN_H - 200))
        else:
            x, y = float(SCREEN_W - 20), float(self.rng.randint(80, SCREEN_H - 200))

        base = {
            ElementKind.WATER: (26, 26, 14, 1.4),
            ElementKind.FIRE: (30, 30, 22, 1.2),
            ElementKind.YIN: (32, 32, 18, 1.0),
            ElementKind.YANG: (28, 28, 16, 1.0),
            ElementKind.METAL: (34, 30, 12, 0.9),
            ElementKind.WOOD: (32, 34, 32, 1.0),
            ElementKind.EARTH: (40, 40, 85, 0.7),
            ElementKind.WIND: (24, 24, 16, 1.1),
            ElementKind.THUNDER: (30, 30, 18, 0.85),
        }[k]
        w, h, mhp, cd0 = base
        self.enemies.append(Enemy(k, x, y, w, h, mhp, mhp, 0.0, 0.0, 0.0, self.rng.uniform(0, 0.6) * cd0))

    def draw(
        self,
        surf: pygame.Surface,
        title_f: pygame.font.Font,
        body_f: pygame.font.Font,
        small_f: pygame.font.Font,
    ) -> None:
        surf.fill((18, 14, 32))
        pygame.draw.rect(surf, (45, 38, 70), (0, self.ground_y, SCREEN_W, SCREEN_H - self.ground_y))
        pygame.draw.line(surf, COLOR_ACCENT, (0, self.ground_y), (SCREEN_W, self.ground_y), 2)

        for i, pad in enumerate(self.tele_pads):
            if pad is None:
                continue
            col = ((70, 200, 240) if i == 0 else (240, 120, 200))
            pygame.draw.rect(surf, col, pad, border_radius=5)
            pygame.draw.rect(surf, (255, 255, 255), pad, 2, border_radius=5)
            mark = "A" if i == 0 else "B"
            tx = small_f.render(mark, True, (30, 30, 45))
            surf.blit(tx, tx.get_rect(center=pad.center))

        for e in self.enemies:
            col = {
                ElementKind.WATER: (80, 160, 255),
                ElementKind.FIRE: (255, 100, 60),
                ElementKind.YIN: (130, 70, 180),
                ElementKind.YANG: (255, 230, 140),
                ElementKind.METAL: (200, 210, 230),
                ElementKind.WOOD: (80, 200, 110),
                ElementKind.EARTH: (150, 110, 70),
                ElementKind.WIND: (160, 255, 200),
                ElementKind.THUNDER: (220, 220, 255),
            }[e.kind]
            er = pygame.Rect(int(e.x), int(e.y), e.w, e.h)
            pygame.draw.ellipse(surf, col, er)
            pygame.draw.ellipse(surf, (20, 20, 30), er, 2)

        for p in self.projectiles:
            pygame.draw.ellipse(surf, p.color, p.rect)

        for ts in self.thunders:
            if ts.phase == "warn":
                a = max(0, 120 - int(ts.t * 220))
                pygame.draw.line(surf, (255, 255, 100), (int(ts.x), 0), (int(ts.x), SCREEN_H), 3)
                s = pygame.Surface((36, SCREEN_H), pygame.SRCALPHA)
                s.fill((255, 200, 80, a))
                surf.blit(s, (int(ts.x - 18), 0))
            else:
                pygame.draw.line(surf, (255, 255, 255), (int(ts.x), 0), (int(ts.x), SCREEN_H), 6)

        pr = self._stick_rect()
        if self.hit_flash > 0:
            pygame.draw.rect(surf, (255, 80, 80), pr.inflate(10, 10), 2)
        if self.heal_flash > 0:
            pygame.draw.rect(surf, (80, 255, 140), pr.inflate(12, 12), 2)

        # 火柴人
        hx, hy = pr.centerx, pr.top
        pygame.draw.circle(surf, COLOR_TEXT, (hx, hy + 10), 10, 2)
        pygame.draw.line(surf, COLOR_TEXT, (hx, hy + 20), (hx, hy + 48), 3)
        arm_y = hy + 28
        pygame.draw.line(surf, COLOR_TEXT, (hx, arm_y), (hx - 22, arm_y + 8), 2)
        pygame.draw.line(surf, COLOR_TEXT, (hx, arm_y), (hx + 22, arm_y + 8), 2)
        pygame.draw.line(surf, COLOR_TEXT, (hx, hy + 48), (hx - 12, hy + 70), 3)
        pygame.draw.line(surf, COLOR_TEXT, (hx, hy + 48), (hx + 12, hy + 70), 3)

        bar_w = 220
        pygame.draw.rect(surf, (40, 40, 55), (24, 20, bar_w, 16))
        pygame.draw.rect(surf, (255, 90, 120), (24, 20, int(bar_w * max(0, self.hp / self.max_hp)), 16))
        mhp = int(self.max_hp)
        t = small_f.render(f"生命 {int(max(0, self.hp))}/{mhp}", True, COLOR_TEXT)
        surf.blit(t, (26, 40))
        inv = self.tele_inventory
        placed = sum(1 for p in self.tele_pads if p is not None)
        if self.endless_vitality:
            buff = small_f.render("生生不息：生命×2 · 每秒+1HP", True, (140, 255, 180))
            surf.blit(buff, (26, 58))
        if math.isfinite(self.win_time):
            remain = max(0.0, self.win_time - self.time)
            time_line = (
                f"坚持 {self.time:.1f}s / {self.win_time:.0f}s（余 {remain:.1f}s）"
            )
        else:
            time_line = f"余晖时长 ∞  ·  已坚持 {self.time:.1f}s"
        k = body_f.render(
            f"{time_line} · 敌 {self.enemy_lifetime:.0f}s 消失"
            f" · 难度×{self.difficulty_mult:.0f} · 传送×{inv} 已布{placed}/2",
            True,
            COLOR_ACCENT,
        )
        y_hud = 78 if self.endless_vitality else 64
        surf.blit(k, (24, y_hud))
        tp = small_f.render(
            "空格放置 · 1 拾起 · 两垫都布好后站上其一并 0.45s 内再按空格→传到另一"
            " · W/↑ 跳跃（占点时空格用于传送）",
            True,
            (180, 195, 220),
        )
        y_tp = 102 if self.endless_vitality else 88
        surf.blit(tp, (24, y_tp))
        if self.burn_stacks > 0.1:
            f = small_f.render(f"灼烧 x{self.burn_stacks:.1f}", True, (255, 140, 80))
            surf.blit(f, (24, y_tp + 24))
        legend = small_f.render(
            "九怪：水(快射) 火(灼烧) 阴/阳(远程) 金(高伤) 木(绿弹射中回血) 土(厚血) 风(疾行) 雷(落雷)",
            True,
            (160, 170, 200),
        )
        surf.blit(legend, (24, SCREEN_H - 36))
        title_s = title_f.render("元素余晖", True, (255, 220, 160))
        surf.blit(title_s, title_s.get_rect(center=(SCREEN_W // 2, 36)))
