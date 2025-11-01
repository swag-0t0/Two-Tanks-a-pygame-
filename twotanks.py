import os
from ai_approach_1 import AIApproach1
from ai_approach_2 import AIApproach2

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

import pygame
from random import randint
import webbrowser
import tempfile
import heapq

pygame.init()
pygame.mixer.init()
pygame.mixer.set_num_channels(64)
CH_BLUE_MOVE = 0
CH_RED_MOVE = 1

WIDTH, HEIGHT = 640, 480
FPS = 60
TILE = 32

window = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

fontUI = pygame.font.Font(None, 30)
bigFont = pygame.font.Font(None, 60)

def load_image(path):
    try:
        return pygame.image.load(path)
    except:
        surf = pygame.Surface((TILE, TILE))
        surf.fill((200, 0, 200))
        return surf

imgBrick = load_image('images/block_brick.png')
imgTanks = [load_image(f'images/tank{i}.png') for i in range(1, 9)]
imgBangs = [load_image(f'images/bang{i}.png') for i in range(1, 4)]
imgBonuses = [load_image('images/bonus_star.png'), load_image('images/bonus_tank.png')]

snd_shoot = snd_explosion = snd_bonus = snd_dead = snd_move = None
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    pygame.mixer.set_num_channels(64)
    snd_shoot = pygame.mixer.Sound('sounds/shot.wav')
    snd_explosion = pygame.mixer.Sound('sounds/destroy.wav')
    snd_bonus = pygame.mixer.Sound('sounds/star.wav')
    snd_dead = pygame.mixer.Sound('sounds/dead.wav')
    snd_move = pygame.mixer.Sound('sounds/engine.wav')
except Exception as e:
    print("Sound error:", e)

DIRECTS = [[0, -1], [1, 0], [0, 1], [-1, 0]]
MOVE_SPEED =    [1, 2, 2, 1, 2, 3, 3, 2]
BULLET_SPEED =  [4, 5, 6, 5, 5, 5, 6, 7]
BULLET_DAMAGE = [1, 1, 2, 3, 2, 2, 3, 4]
SHOT_DELAY =    [60, 50, 30, 40, 30, 25, 25, 30]

bullets = []
objects = []
game_started = False
game_over = False
winner = None
state = "menu" 
game_mode = "human_vs_human"

# Button rects
menu_new_hvh_rect = pygame.Rect(0, 0, 1, 1)
menu_new_hva_rect = pygame.Rect(0, 0, 1, 1)
menu_new_ava_rect = pygame.Rect(0, 0, 1, 1)
menu_resume_rect = pygame.Rect(0, 0, 1, 1)
menu_controls_rect = pygame.Rect(0, 0, 1, 1)
menu_exit_rect = pygame.Rect(0, 0, 1, 1)
controls_back_rect = pygame.Rect(WIDTH//2 - 80, HEIGHT - 100, 160, 50)
gameover_new_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 40, 200, 50)
gameover_exit_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 100, 200, 50)

def open_controls_window():
    html = """
    <!doctype html>
    <html>
      <head><meta charset="utf-8"><title>Tank Controls</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 20px; background:#111; color:#eee; }
          h1 { color: #ffcc00; }
          .tank { margin-bottom: 16px; padding:10px; border-radius:8px; background:#222; }
          .key { display:inline-block; min-width:70px; font-weight:bold; }
        </style>
      </head>
      <body>
        <h1>Tank Controls</h1>
        <div class="tank">
          <h2 style="color:#6ec6ff">Blue Tank (Player)</h2>
          <p><span class="key">Move:</span> W A S D</p>
          <p><span class="key">Shoot:</span> SPACE</p>
        </div>
        <div class="tank">
          <h2 style="color:#ff6e6e">Red Tank</h2>
          <p><span class="key">Human:</span> Arrow Keys + ENTER</p>
          <p><span class="key">AI:</span> Fully Automatic</p>
        </div>
        <p>Press ESC in-game to pause.</p>
      </body>
    </html>
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8')
    tmp.write(html)
    tmp.close()
    webbrowser.open_new_tab('file://' + os.path.abspath(tmp.name))

def count_blocks_in_path(pos1, pos2, blocks):
    """Count unique blocks between two points (for FIS rule: shoot if exactly 1 block)"""
    x1, y1 = pos1
    x2, y2 = pos2
    dx = x2 - x1
    dy = y2 - y1
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        return 0

    block_set = set()
    for i in range(1, int(steps)):
        t = i / steps
        x = x1 + dx * t
        y = y1 + dy * t
        for block in blocks:
            if block.rect.collidepoint(x, y):
                block_set.add(id(block))
                break
    return len(block_set)

def spawn_bonus_safely():
    """Spawn a bonus at a random position not inside any block or other object."""
    for _ in range(100):
        x = randint(50, WIDTH - 50)
        y = randint(50, HEIGHT - 50)
        bonus_rect = pygame.Rect(x - TILE//2, y - TILE//2, TILE, TILE)
        if not any(hasattr(obj, 'rect') and obj.rect.colliderect(bonus_rect) for obj in objects):
            return Bonus(x, y, randint(0, len(imgBonuses)-1))
    # Fallback
    return Bonus(randint(50, WIDTH-50), randint(50, HEIGHT-50), randint(0, len(imgBonuses)-1))

class UI:
    def update(self): pass
    def draw(self):
        i = 0
        for obj in objects:
            if obj.type == 'tank':
                panel_x = 10 + i * 100
                pygame.draw.rect(window, (30, 30, 40), (panel_x, 10, 90, 40), border_radius=8)
                pygame.draw.rect(window, obj.color, (panel_x + 5, 15, 20, 20))
                rank_text = fontUI.render(f"R{obj.rank}", True, "white")
                window.blit(rank_text, (panel_x + 30, 15))
                hp_text = fontUI.render(f"HP: {obj.hp}", True, "white")
                window.blit(hp_text, (panel_x + 30, 32))
                i += 1

class Tank:
    def __init__(self, color, px, py, direct, keyList, ai_controlled=False, ai_approach=None):
        objects.append(self)
        self.type = 'tank'
        self.color = color
        self.rect = pygame.Rect(px, py, TILE, TILE)
        self.direct = direct
        self.hp = 5
        self.shotTimer = 0
        self.rank = 0
        self.image = pygame.transform.rotate(imgTanks[self.rank], -self.direct * 90)
        self.rect = self.image.get_rect(center=self.rect.center)
        self.keyLEFT, self.keyRIGHT, self.keyUP, self.keyDOWN, self.keySHOT = keyList
        self.ai_controlled = ai_controlled
        self.is_moving = False
        self.move_channel = pygame.mixer.Channel(CH_BLUE_MOVE if color == 'blue' else CH_RED_MOVE)

        self.ai_approach = None
        if ai_controlled and ai_approach:  # Inject AI behavior
            if ai_approach == AIApproach1:
                self.ai_approach = ai_approach(self, objects, snd_move, snd_shoot)
            elif ai_approach == AIApproach2:
                self.ai_approach = ai_approach(self, objects, snd_shoot)
            else:
                self.ai_approach = ai_approach(self, objects)

    def update(self):
        self.image = pygame.transform.rotate(imgTanks[self.rank], -self.direct * 90)
        w, h = self.image.get_width(), self.image.get_height()
        self.image = pygame.transform.scale(self.image, (max(8, w - 5), max(8, h - 5)))
        self.rect = self.image.get_rect(center=self.rect.center)

        self.moveSpeed = MOVE_SPEED[self.rank]
        self.shotDelay = SHOT_DELAY[self.rank]
        self.bulletSpeed = BULLET_SPEED[self.rank]
        self.bulletDamage = BULLET_DAMAGE[self.rank]

        if self.ai_controlled and self.ai_approach:
            self.ai_approach.update()
        else:
            self._player_update()

    def _player_update(self):
        oldX, oldY = self.rect.topleft
        moving_now = False
        if keys[self.keyLEFT]:
            self.rect.x -= self.moveSpeed; self.direct = 3; moving_now = True
        elif keys[self.keyRIGHT]:
            self.rect.x += self.moveSpeed; self.direct = 1; moving_now = True
        elif keys[self.keyUP]:
            self.rect.y -= self.moveSpeed; self.direct = 0; moving_now = True
        elif keys[self.keyDOWN]:
            self.rect.y += self.moveSpeed; self.direct = 2; moving_now = True

        self.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))

        for obj in objects:
            if obj != self and (obj.type == 'block' or obj.type == 'tank') and self.rect.colliderect(obj.rect):
                self.rect.topleft = oldX, oldY
                moving_now = False

        if moving_now and not self.is_moving:
            if snd_move: self.move_channel.play(snd_move, loops=-1)
            self.is_moving = True
        elif not moving_now and self.is_moving:
            self.move_channel.stop()
            self.is_moving = False

        if keys[self.keySHOT] and self.shotTimer == 0:
            Bullet(self, self.rect.centerx, self.rect.centery,
                   DIRECTS[self.direct][0] * self.bulletSpeed,
                   DIRECTS[self.direct][1] * self.bulletSpeed,
                   self.bulletDamage)
            if snd_shoot: snd_shoot.play()
            self.shotTimer = self.shotDelay

        if self.shotTimer > 0:
            self.shotTimer -= 1

    def draw(self):
        window.blit(self.image, self.rect)

    def damage(self, value):
        global game_over, winner, state
        self.hp -= value
        if self.hp <= 0:
            try: objects.remove(self)
            except: pass
            if hasattr(self, 'move_channel'):
                self.move_channel.stop()
            game_over = True
            state = "gameover"
            winner = "Red Wins!" if self.color == "blue" else "Blue Wins!"
            if snd_explosion: snd_explosion.play()
            if snd_dead: snd_dead.play()

class Bullet:
    def __init__(self, parent, px, py, dx, dy, damage):
        bullets.append(self)
        self.parent = parent
        self.px, self.py = float(px), float(py)
        self.dx, self.dy = dx, dy
        self.damage = damage
    def update(self):
        self.px += self.dx; self.py += self.dy
        if not (0 <= self.px <= WIDTH and 0 <= self.py <= HEIGHT):
            if self in bullets: bullets.remove(self)
        else:
            for obj in objects[:]:
                if obj != self.parent and obj.type not in ['bang', 'bonus']:
                    if obj.rect.collidepoint(int(self.px), int(self.py)):
                        obj.damage(self.damage)
                        if self in bullets: bullets.remove(self)
                        Bang(self.px, self.py)
                        if snd_explosion: snd_explosion.play()
                        break
    def draw(self):
        pygame.draw.circle(window, 'yellow', (int(self.px), int(self.py)), 2)

class Bang:
    def __init__(self, px, py):
        objects.append(self); self.type='bang'; self.px,self.py=px,py; self.frame=0
    def update(self):
        self.frame += 0.2
        if self.frame >= 3:
            if self in objects: objects.remove(self)
    def draw(self):
        img = imgBangs[int(self.frame)]
        rect = img.get_rect(center=(int(self.px), int(self.py)))
        window.blit(img, rect)

class Block:
    def __init__(self, px, py, size):
        objects.append(self); self.type='block'; self.rect=pygame.Rect(px,py,size,size); self.hp=1
    def update(self): pass
    def draw(self): window.blit(imgBrick, self.rect)
    def damage(self, value):
        self.hp -= value
        if self.hp <= 0:
            if self in objects: objects.remove(self)

class Bonus:
    def __init__(self, px, py, bonusNum):
        objects.append(self)
        self.type = 'bonus'
        self.image = imgBonuses[bonusNum]
        self.rect = self.image.get_rect(center=(px, py))
        self.timer = 900  # 15 seconds
        self.bonusNum = bonusNum
    def update(self):
        if self.timer > 0:
            self.timer -= 1
        else:
            if self in objects: objects.remove(self)
            return
        for obj in objects[:]:
            if obj.type == 'tank' and self.rect.colliderect(obj.rect):
                if self.bonusNum == 0 and obj.rank < len(imgTanks) - 1:
                    obj.rank += 1
                    if snd_bonus: snd_bonus.play()
                elif self.bonusNum == 1:
                    obj.hp += 1
                    if snd_bonus: snd_bonus.play()
                if self in objects: objects.remove(self)
                break
    def draw(self):
        if self.timer % 30 < 15:
            window.blit(self.image, self.rect)

def reset_game():
    global bullets, objects, ui, game_over, winner
    bullets = []; objects = []
    if game_mode == "ai_vs_ai":
        Tank('blue', TILE, TILE, 1, (0,0,0,0,0), ai_controlled=True, ai_approach=AIApproach1)
        Tank('red', WIDTH - 2*TILE, HEIGHT - 2*TILE, 3, (0,0,0,0,0), ai_controlled=True, ai_approach=AIApproach2)
        for _ in range(3):
            spawn_bonus_safely()
    elif game_mode == "human_vs_ai":
        Tank('blue', 100, HEIGHT//2 - TILE//2, 0, (pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s, pygame.K_SPACE), ai_controlled=False)
        Tank('red', WIDTH - 100 - TILE, HEIGHT//2 - TILE//2, 0, (0,0,0,0,0), ai_controlled=True, ai_approach=AIApproach1)
    else:
        Tank('blue', 100, HEIGHT//2 - TILE//2, 0, (pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s, pygame.K_SPACE), ai_controlled=False)
        Tank('red', WIDTH - 100 - TILE, HEIGHT//2 - TILE//2, 0, (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_RETURN), ai_controlled=False)

    ui = UI()
    for _ in range(50):
        while True:
            x = randint(0, WIDTH // TILE - 1) * TILE
            y = randint(1, HEIGHT // TILE - 1) * TILE
            rect = pygame.Rect(x, y, TILE, TILE)
            if not any(rect.colliderect(obj.rect) for obj in objects if hasattr(obj, 'rect')):
                break
        Block(x, y, TILE)
    game_over = False
    winner = None

def draw_button(text, x, y, w, h):
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(window, (70, 130, 180), rect, border_radius=12)
    pygame.draw.rect(window, (200, 220, 255), rect, 2, border_radius=12)
    label = fontUI.render(text, True, "white")
    window.blit(label, label.get_rect(center=rect.center))
    return rect

reset_game()
play = True
keys = pygame.key.get_pressed()

while play:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            play = False
        if state == "game" and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            state = "menu"
            pygame.mixer.stop()
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            if state == "menu":
                if menu_new_hvh_rect.collidepoint(mx, my):
                    game_mode = "human_vs_human"
                    reset_game(); state = "game"; game_started = True
                elif menu_new_hva_rect.collidepoint(mx, my):
                    game_mode = "human_vs_ai"
                    reset_game(); state = "game"; game_started = True
                elif menu_new_ava_rect.collidepoint(mx, my):
                    game_mode = "ai_vs_ai"
                    reset_game(); state = "game"; game_started = True
                elif menu_resume_rect.collidepoint(mx, my) and game_started and not game_over:
                    state = "game"
                elif menu_controls_rect.collidepoint(mx, my):
                    open_controls_window()
                    state = "controls"
                elif menu_exit_rect.collidepoint(mx, my):
                    play = False
            elif state == "controls" and controls_back_rect.collidepoint(mx, my):
                state = "menu"
            elif state == "gameover":
                if gameover_new_rect.collidepoint(mx, my):
                    reset_game(); state = "game"
                elif gameover_exit_rect.collidepoint(mx, my):
                    play = False

    keys = pygame.key.get_pressed()
    window.fill((10, 10, 20))

    if state == "menu":
        window.fill((10, 10, 20))
        title = bigFont.render("TANK BATTLE", True, "yellow")
        window.blit(title, title.get_rect(center=(WIDTH//2, 80)))

        button_w, button_h = 220, 45
        start_x = WIDTH//2 - button_w//2
        y0 = 160
        spacing = 55

        menu_new_hvh_rect = draw_button("Human vs Human", start_x, y0, button_w, button_h)
        menu_new_hva_rect = draw_button("Human vs AI", start_x, y0 + spacing, button_w, button_h)
        menu_new_ava_rect = draw_button("AI vs AI", start_x, y0 + 2*spacing, button_w, button_h)
        menu_controls_rect = draw_button("Controls", start_x, y0 + 3*spacing, button_w, button_h)
        menu_exit_rect = draw_button("Exit", start_x, y0 + 4*spacing, button_w, button_h)

        if game_started and not game_over:
            menu_resume_rect = draw_button("Resume Game", start_x, y0 + 5*spacing, button_w, button_h)

    elif state == "controls":
        window.fill((15, 15, 25))
        title = bigFont.render("Game Controls", True, "cyan")
        window.blit(title, title.get_rect(center=(WIDTH//2, 60)))
        lines = [
            "🔵 Blue Tank: W A S D to move, SPACE to shoot",
            "🔴 Red Tank: Arrow Keys + ENTER (Human) or Auto (AI)",
            "Press ESC anytime to pause and return to Menu",
            "Click 'Back' to return to main menu.",
        ]
        for i, line in enumerate(lines):
            label = fontUI.render(line, True, "lightgray")
            window.blit(label, (60, 160 + i*40))
        draw_button("Back", *controls_back_rect)

    elif state == "game":
        if not game_over:
            # FIS: Always maintain ≥4 bonuses, safely spawned
            bonuses = [obj for obj in objects if obj.type == 'bonus']
            while len(bonuses) < 4:
                spawn_bonus_safely()
                bonuses = [obj for obj in objects if obj.type == 'bonus']
            
            for bullet in bullets[:]: bullet.update()
            for obj in objects[:]: obj.update()
            ui.update()
        for bullet in bullets[:]: bullet.draw()
        for obj in objects[:]: obj.draw()
        ui.draw()

    elif state == "gameover":
        window.fill((20, 10, 10))
        text = bigFont.render("GAME OVER", True, "red")
        window.blit(text, text.get_rect(center=(WIDTH//2, HEIGHT//3 - 20)))
        if winner:
            win_text = fontUI.render(winner, True, "gold")
            window.blit(win_text, win_text.get_rect(center=(WIDTH//2, HEIGHT//2)))
        draw_button("New Game", *gameover_new_rect)
        draw_button("Exit", *gameover_exit_rect)
        pygame.mixer.stop()

    pygame.display.update()
    clock.tick(FPS)

pygame.quit()