"""俄罗斯方块 (Tetris)

运行:
    python 俄罗斯方块.py

操作 (方向键 与 WASD 都支持):
    移动 (可长按)   <- ->    或  A D
    旋转            ↑        或  W / X
    反转            Z
    软降 (可长按)   ↓        或  S
    硬降            空格     或  E
    暂停 / 重开 / 退出   P / R / ESC

提示: 若按键无反应, 说明窗口没拿到键盘焦点, 用鼠标点一下游戏窗口即可。
"""

import random
import sys

import pygame

# ---------------- 参数 ----------------
COLS, ROWS = 10, 20
BLOCK = 30
MARGIN = 20
PANEL_W = 220
WIDTH  = MARGIN + COLS * BLOCK + MARGIN + PANEL_W
HEIGHT = MARGIN + ROWS * BLOCK + MARGIN
FPS = 60

# ---------------- 颜色 ----------------
BG       = (18, 18, 24)
BOARD_BG = (30, 30, 40)
GRID     = (46, 46, 62)
FRAME    = (74, 74, 100)
TEXT     = (232, 232, 240)
TEXT_DIM = (150, 150, 172)
PANEL_BG = (26, 26, 38)
DANGER   = (240, 90, 90)

COLORS = {
    'I': (0, 220, 220),
    'O': (240, 220, 0),
    'T': (172, 64, 220),
    'S': (64, 200, 80),
    'Z': (222, 62, 62),
    'J': (64, 96, 222),
    'L': (232, 152, 40),
}

SHAPES = {
    'I': [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]],
    'O': [[1, 1], [1, 1]],
    'T': [[0, 1, 0], [1, 1, 1], [0, 0, 0]],
    'S': [[0, 1, 1], [1, 1, 0], [0, 0, 0]],
    'Z': [[1, 1, 0], [0, 1, 1], [0, 0, 0]],
    'J': [[1, 0, 0], [1, 1, 1], [0, 0, 0]],
    'L': [[0, 0, 1], [1, 1, 1], [0, 0, 0]],
}

LINE_SCORE = [0, 100, 300, 500, 800]


def rotate_cw(shape):
    return [list(r) for r in zip(*shape[::-1])]


def rotate_ccw(shape):
    return [list(r) for r in zip(*shape)[::-1]]


class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.shape = [row[:] for row in SHAPES[kind]]
        self.x = (COLS - len(self.shape[0])) // 2
        self.y = 0


class Game:
    """游戏状态与规则 (与渲染、输入无关, 便于单独测试)。"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.bag = []
        self.score = 0
        self.lines = 0
        self.level = 0
        self.over = False
        self.paused = False
        self.piece = None
        self.next_kind = None
        self.fall_acc = 0
        self._spawn()

    # ---- 出块 (7-bag 随机) ----
    def _take(self):
        if not self.bag:
            self.bag = list(SHAPES)
            random.shuffle(self.bag)
        return self.bag.pop()

    def _spawn(self):
        if self.next_kind is None:
            self.next_kind = self._take()
        self.piece = Piece(self.next_kind)
        self.next_kind = self._take()
        self.fall_acc = 0
        if self._collide(self.piece):
            self.over = True

    # ---- 碰撞 / 落点 ----
    def _collide(self, piece, dx=0, dy=0, shape=None):
        shape = shape or piece.shape
        for y, row in enumerate(shape):
            for x, v in enumerate(row):
                if not v:
                    continue
                nx, ny = piece.x + x + dx, piece.y + y + dy
                if nx < 0 or nx >= COLS or ny >= ROWS:
                    return True
                if ny >= 0 and self.board[ny][nx]:
                    return True
        return False

    def drop_y(self):
        dy = 0
        while not self._collide(self.piece, 0, dy + 1):
            dy += 1
        return self.piece.y + dy

    def fall_interval(self):
        return max(90, 800 - self.level * 70)

    # ---- 操作 ----
    def move(self, dx):
        if self.over or self.paused:
            return
        if not self._collide(self.piece, dx, 0):
            self.piece.x += dx

    def rotate(self, cw=True):
        if self.over or self.paused or self.piece.kind == 'O':
            return
        new = rotate_cw(self.piece.shape) if cw else rotate_ccw(self.piece.shape)
        for dx in (0, -1, 1, -2, 2):          # 踢墙
            if not self._collide(self.piece, dx, 0, new):
                self.piece.shape = new
                self.piece.x += dx
                return

    def soft_drop(self):
        if self.over or self.paused:
            return
        if not self._collide(self.piece, 0, 1):
            self.piece.y += 1
            self.score += 1
            self.fall_acc = 0
        else:
            self._lock()

    def hard_drop(self):
        if self.over or self.paused:
            return
        dy = 0
        while not self._collide(self.piece, 0, dy + 1):
            dy += 1
        self.piece.y += dy
        self.score += dy * 2
        self._lock()

    # ---- 锁定 / 消行 ----
    def _lock(self):
        for y, row in enumerate(self.piece.shape):
            for x, v in enumerate(row):
                if v and self.piece.y + y >= 0:
                    self.board[self.piece.y + y][self.piece.x + x] = self.piece.kind
        self._clear_lines()
        self._spawn()

    def _clear_lines(self):
        kept = [row for row in self.board if not all(row)]
        cleared = ROWS - len(kept)
        while len(kept) < ROWS:
            kept.insert(0, [None] * COLS)
        self.board = kept
        if cleared:
            self.score += LINE_SCORE[cleared] * (self.level + 1)
            self.lines += cleared
            self.level = self.lines // 10

    def tick(self, dt):
        if self.over or self.paused:
            return
        self.fall_acc += dt
        if self.fall_acc >= self.fall_interval():
            self.fall_acc = 0
            if not self._collide(self.piece, 0, 1):
                self.piece.y += 1
            else:
                self._lock()


# ---------------- 渲染 ----------------
def load_font(size):
    for fam in ('microsoftyahei', 'msyh', 'simhei', 'simsun', 'notosanscjk', 'arial'):
        path = pygame.font.match_font(fam)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def draw_block(surf, px, py, color, size=BLOCK, ghost=False):
    r = pygame.Rect(px, py, size, size)
    if ghost:
        c = tuple(min(255, v // 3 + 30) for v in color)
        pygame.draw.rect(surf, c, r)
        pygame.draw.rect(surf, (255, 255, 255), r, 2)
        return
    light = tuple(min(255, v + 55) for v in color)
    dark = tuple(max(0, v - 55) for v in color)
    pygame.draw.rect(surf, color, r)
    pygame.draw.rect(surf, light, (px, py, size, 3))
    pygame.draw.rect(surf, light, (px, py, 3, size))
    pygame.draw.rect(surf, dark, (px, py + size - 3, size, 3))
    pygame.draw.rect(surf, dark, (px + size - 3, py, 3, size))
    pygame.draw.rect(surf, (0, 0, 0), r, 1)


def text(surf, s, font, color, x, y, align='left'):
    img = font.render(s, True, color)
    rect = img.get_rect()
    if align == 'center':
        rect.centerx = x
    elif align == 'right':
        rect.right = x
    else:
        rect.left = x
    rect.top = y
    surf.blit(img, rect)
    return rect


def draw_mini(screen, kind, cx, cy, cell=22):
    shape = SHAPES[kind]
    xs = [x for row in shape for x, v in enumerate(row) if v]
    ys = [y for row in shape for y, v in enumerate(row) if v]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    ox = cx - (maxx - minx + 1) * cell // 2
    oy = cy - (maxy - miny + 1) * cell // 2
    for y in range(miny, maxy + 1):
        for x in range(minx, maxx + 1):
            if shape[y][x]:
                draw_block(screen, ox + (x - minx) * cell, oy + (y - miny) * cell,
                           COLORS[kind], size=cell)


def draw(screen, game, bx, by, px, fonts, focused, started):
    f_big, f_mid, f_small = fonts
    screen.fill(BG)

    # 棋盘
    pygame.draw.rect(screen, BOARD_BG, (bx, by, COLS * BLOCK, ROWS * BLOCK))
    for c in range(COLS + 1):
        x = bx + c * BLOCK
        pygame.draw.line(screen, GRID, (x, by), (x, by + ROWS * BLOCK))
    for r in range(ROWS + 1):
        y = by + r * BLOCK
        pygame.draw.line(screen, GRID, (bx, y), (bx + COLS * BLOCK, y))

    for y in range(ROWS):
        for x in range(COLS):
            k = game.board[y][x]
            if k:
                draw_block(screen, bx + x * BLOCK, by + y * BLOCK, COLORS[k])

    if game.piece and not game.over:
        p = game.piece
        gy = game.drop_y()
        for y, row in enumerate(p.shape):
            for x, v in enumerate(row):
                if v and gy + y >= 0:
                    draw_block(screen, bx + (p.x + x) * BLOCK, by + (gy + y) * BLOCK,
                               COLORS[p.kind], ghost=True)
        for y, row in enumerate(p.shape):
            for x, v in enumerate(row):
                if v and p.y + y >= 0:
                    draw_block(screen, bx + (p.x + x) * BLOCK, by + (p.y + y) * BLOCK,
                               COLORS[p.kind])

    pygame.draw.rect(screen, FRAME, (bx - 3, by - 3, COLS * BLOCK + 6, ROWS * BLOCK + 6), 3)

    # 面板
    pygame.draw.rect(screen, PANEL_BG, (px, by, PANEL_W, ROWS * BLOCK), border_radius=8)
    if not focused:
        text(screen, '未聚焦 - 点击窗口', f_mid, DANGER, px + 20, by + 16)

    ty = by + 16
    text(screen, '得分', f_mid, TEXT_DIM, px + 20, ty)
    text(screen, str(game.score), f_big, TEXT, px + 20, ty + 28)
    ty += 92
    text(screen, '行数', f_mid, TEXT_DIM, px + 20, ty)
    text(screen, str(game.lines), f_big, TEXT, px + 20, ty + 28)
    text(screen, '等级', f_mid, TEXT_DIM, px + 120, ty)
    text(screen, str(game.level), f_big, TEXT, px + 120, ty + 28)
    ty += 100
    text(screen, '下一个', f_mid, TEXT_DIM, px + 20, ty)
    if game.next_kind:
        draw_mini(screen, game.next_kind, px + PANEL_W // 2, ty + 55)
    ty += 116
    text(screen, '操作', f_mid, TEXT_DIM, px + 20, ty)
    ty += 32
    for line in ('←→/AD  移动', '↑/W    旋转', 'Z      反转',
                 '↓/S    软降', '空格   硬降', 'P/R    暂停/重开'):
        text(screen, line, f_small, TEXT_DIM, px + 20, ty)
        ty += 23

    # 开场 / 暂停 / 结束 遮罩
    if not started or game.paused or game.over:
        ov = pygame.Surface((COLS * BLOCK, ROWS * BLOCK), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        screen.blit(ov, (bx, by))
        cx = bx + COLS * BLOCK // 2
        cy = by + ROWS * BLOCK // 2
        if not started:
            main_msg, sub = '俄罗斯方块', '按任意键 / 点击窗口 开始'
        elif game.over:
            main_msg, sub = '游戏结束', '按 R 重新开始   得分 %d' % game.score
        else:
            main_msg, sub = '已暂停', '按 P 继续'
        text(screen, main_msg, f_big, TEXT, cx, cy - 26, 'center')
        text(screen, sub, f_mid, TEXT_DIM, cx, cy + 14, 'center')


# ---------------- Windows 输入焦点 / 输入法 ----------------
def disable_ime_before_window():
    """必须在 pygame 创建窗口之前调用: 对整个进程禁用输入法(IME)。
    这样中文字符被输入法截走 (导致 WASD 字母键没反应) 的问题就不会发生。"""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        ctypes.windll.imm32.ImmDisableIME(0)
    except Exception:
        pass


def force_foreground():
    """把窗口置前并获得键盘焦点, 同时解除输入法与窗口的关联。失败也不影响运行。"""
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        hwnd = pygame.display.get_wm_info().get('window')
        if not hwnd:
            return
        u = ctypes.windll.user32
        u.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)  # TOPMOST | NOMOVE|NOSIZE
        u.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0002)  # NOTOPMOST
        u.SetForegroundWindow(hwnd)
        u.SetFocus(hwnd)
        # 解除输入法与窗口的关联, 让字母键直达游戏
        ctypes.windll.imm32.ImmAssociateContext(hwnd, 0)
    except Exception:
        pass


# ---------------- 输入映射 ----------------
MOVE_L = (pygame.K_LEFT, pygame.K_a)
MOVE_R = (pygame.K_RIGHT, pygame.K_d)
SOFT   = (pygame.K_DOWN, pygame.K_s)
ROT_CW = (pygame.K_UP, pygame.K_w, pygame.K_x)
ROT_CC = (pygame.K_z,)
HARD   = (pygame.K_SPACE, pygame.K_e)

DAS = 260   # 长按后开始连续移动的延迟 (毫秒) —— 越大, 越不容易"一按就冲出去"
ARR = 150   # 连续移动的间隔 (毫秒) —— 越大, 连续移动越慢


def main():
    disable_ime_before_window()      # 必须在创建窗口前禁用输入法
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption('俄罗斯方块')
    force_foreground()
    clock = pygame.time.Clock()
    fonts = (load_font(30), load_font(22), load_font(16))

    game = Game()
    bx, by = MARGIN, MARGIN
    px = bx + COLS * BLOCK + MARGIN

    started = False        # 是否已通过开场屏 (确保先拿到焦点)
    held = set()           # 当前按住的键
    hold_timer = 0         # 长按计时
    focus_loss_timer = 0   # 失焦后自动回到开场屏的计时

    while True:
        dt = min(clock.tick(FPS), 100)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if not started:                 # 开场屏: 任意键开始
                    started = True
                    held.clear()
                    continue
                held.add(e.key)
                if e.key == pygame.K_p and not game.over:
                    game.paused = not game.paused
                elif e.key == pygame.K_r:
                    game.reset()
                    game.paused = False
                elif e.key in ROT_CW:
                    game.rotate(cw=True)
                elif e.key in ROT_CC:
                    game.rotate(cw=False)
                elif e.key in HARD:
                    game.hard_drop()
            elif e.type == pygame.KEYUP:
                if e.key in MOVE_L or e.key in MOVE_R or e.key in SOFT:
                    hold_timer = 0
                held.discard(e.key)
            elif e.type == pygame.MOUSEBUTTONDOWN and not started:
                started = True
                held.clear()

        focused = pygame.key.get_focused()

        # 失焦保护: 若长时间无焦点, 自动回到开场屏, 避免"按键没反应"的困惑
        if started and not game.over and not focused:
            focus_loss_timer += dt
            if focus_loss_timer > 1200:
                started = False
                focus_loss_timer = 0
        else:
            focus_loss_timer = 0

        if started and not game.paused and not game.over:
            # 横向优先级: 后按的键优先
            if held & set(MOVE_L) and held & set(MOVE_R):
                horiz = -1 if max(held) in MOVE_L else 1
            elif held & set(MOVE_L):
                horiz = -1
            elif held & set(MOVE_R):
                horiz = 1
            else:
                horiz = 0
            soft = bool(held & set(SOFT))

            # 首次按下立即响应一次, 之后等待 DAS 才开始连发, 每隔 ARR 移动一格
            # (注意: 绝不能"每帧都移动", 否则 60fps 下会瞬间冲到墙边)
            moving = horiz != 0 or soft
            if moving:
                if hold_timer == 0:            # 刚按下: 只响应这一次
                    if horiz != 0:
                        game.move(horiz)
                    if soft:
                        game.soft_drop()
                    hold_timer = dt
                else:                          # 保持按住: 按 DAS/ARR 节流
                    hold_timer += dt
                    if hold_timer >= DAS:
                        hold_timer -= ARR
                        if horiz != 0:
                            game.move(horiz)
                        if soft:
                            game.soft_drop()
            else:
                hold_timer = 0

        game.tick(dt)
        draw(screen, game, bx, by, px, fonts, focused, started)
        pygame.display.flip()


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        # 出错时把完整错误写入日志文件, 便于排查"闪退"问题
        import traceback
        msg = traceback.format_exc()
        try:
            with open('俄罗斯方块_错误日志.txt', 'w', encoding='utf-8') as f:
                f.write(msg)
        except Exception:
            pass
        print(msg)
        raise
