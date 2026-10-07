"""按键检测工具: 运行后按几下键盘, 窗口会实时显示收到了什么。
   (用于排查游戏按键没反应的问题)"""

import sys
import pygame

LOG = '按键测试_日志.txt'

def main():
    # 创建窗口前禁用输入法(IME), 避免字母键被输入法截走
    try:
        import ctypes
        ctypes.windll.imm32.ImmDisableIME(0)
    except Exception:
        pass
    pygame.init()
    screen = pygame.display.set_mode((640, 420))
    pygame.display.set_caption('按键检测 - 请按几下键盘')
    try:
        import ctypes
        hwnd = pygame.display.get_wm_info().get('window')
        if hwnd:
            u = ctypes.windll.user32
            u.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)
            u.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0002)
            u.SetForegroundWindow(hwnd)
            u.SetFocus(hwnd)
            ctypes.windll.imm32.ImmAssociateContext(hwnd, 0)
    except Exception:
        pass

    for fam in ('microsoftyahei', 'msyh', 'simhei', 'arial'):
        p = pygame.font.match_font(fam)
        if p:
            font = pygame.font.Font(p, 26); font_s = pygame.font.Font(p, 20)
            break
    else:
        font = pygame.font.Font(None, 26); font_s = pygame.font.Font(None, 20)

    logf = open(LOG, 'w', encoding='utf-8')
    logf.write('按键检测开始\n'); logf.flush()

    clock = pygame.time.Clock()
    last_keys = []          # 最近按下的键 (最多 8 个)
    keydown_count = 0
    textinput_count = 0
    last_text = ''
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                    continue
                keydown_count += 1
                nm = pygame.key.name(e.key)
                last_keys.append(nm); last_keys = last_keys[-8:]
                logf.write('KEYDOWN name=%r key=%s mod=%s unicode=%r\n'
                           % (nm, e.key, e.mod, getattr(e, 'unicode', ''))); logf.flush()
            elif e.type == pygame.KEYUP:
                logf.write('KEYUP   name=%r\n' % pygame.key.name(e.key)); logf.flush()
            elif e.type == pygame.TEXTINPUT:
                textinput_count += 1
                last_text = e.text
                logf.write('TEXTINPUT text=%r  (这是输入法/文本输入事件!)\n' % e.text); logf.flush()

        focused = pygame.key.get_focused()
        screen.fill((20, 20, 28))
        y = 20
        screen.blit(font.render('窗口焦点: %s' % ('是 (OK)' if focused else '否 (请点一下窗口)'),
                                True, (90, 230, 130) if focused else (240, 90, 90)), (24, y)); y += 44
        screen.blit(font.render('收到按键次数: %d' % keydown_count, True, (235, 235, 245)), (24, y)); y += 40
        screen.blit(font.render('收到输入法事件: %d  文本=%r' % (textinput_count, last_text),
                                True, (250, 200, 90) if textinput_count else (150, 150, 172)), (24, y)); y += 48
        screen.blit(font_s.render('最近按下的键:', True, (150, 150, 172)), (24, y)); y += 32
        for k in reversed(last_keys):
            screen.blit(font.render('  ' + k, True, (235, 235, 245)), (24, y)); y += 30
        if keydown_count == 0:
            screen.blit(font_s.render('(还没有收到任何按键)', True, (150, 150, 172)), (24, y))
        screen.blit(font_s.render('按 ESC 退出', True, (150, 150, 172)), (24, 380))
        pygame.display.flip()
        clock.tick(60)
    logf.write('结束: 共收到 %d 个按键, %d 个输入法事件\n' % (keydown_count, textinput_count)); logf.flush()
    logf.close()
    pygame.quit()


if __name__ == '__main__':
    main()
