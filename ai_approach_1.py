import pygame
import heapq
from random import randint

# Constants and utility functions reused from original code
WIDTH, HEIGHT, TILE = 640, 480, 32
DIRECTS = [[0, -1], [1, 0], [0, 1], [-1, 0]]
MOVE_SPEED = [1, 2, 2, 1, 2, 3, 3, 2]
SHOT_DELAY = [60, 50, 30, 40, 30, 25, 25, 30]
BULLET_SPEED = [4, 5, 6, 5, 5, 5, 6, 7]
BULLET_DAMAGE = [1, 1, 2, 3, 2, 2, 3, 4]

def count_blocks_in_path(pos1, pos2, blocks):
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

class AIApproach1:
    def __init__(self, tank, objects, snd_move=None, snd_shoot=None):
        self.tank = tank
        self.objects = objects
        self.snd_move = snd_move
        self.snd_shoot = snd_shoot
        self.path = []
        self.path_index = 0
        self.has_seen_enemy = False

    def update(self):
        enemy = None
        bonuses = []
        blocks = [obj for obj in self.objects if obj.type == 'block']

        for obj in self.objects:
            if obj.type == 'tank' and obj != self.tank:
                enemy = obj
            elif obj.type == 'bonus':
                bonuses.append(obj)

        my_center = (self.tank.rect.centerx, self.tank.rect.centery)

        # FIS Rule 1: Enemy visibility (0 blocks = visible)
        visible_enemy = False
        if enemy:
            enemy_block_count = count_blocks_in_path(my_center, (enemy.rect.centerx, enemy.rect.centery), blocks)
            visible_enemy = (enemy_block_count == 0)
        if visible_enemy:
            self.has_seen_enemy = True

        # Target: nearest bonus or center
        if bonuses:
            nearest_bonus = min(bonuses, key=lambda b: (b.rect.centerx - self.tank.rect.centerx) ** 2 + (b.rect.centery - self.tank.rect.centery) ** 2)
            target = (nearest_bonus.rect.centerx, nearest_bonus.rect.centery)
            block_count_to_bonus = count_blocks_in_path(my_center, target, blocks)
        else:
            target = (WIDTH // 2, HEIGHT // 2)
            block_count_to_bonus = 0

        # Inference: Apply rules
        # Inference: Apply rules - Only shoot when it makes sense
        should_shoot = False
        
        # Rule 1: Shoot at visible enemy (no blocks in between)
        if visible_enemy:
            should_shoot = True
            self.has_seen_enemy = True
        
        # Rule 2: Shoot to clear path to bonus (only if we're actually moving toward a bonus)
        elif bonuses and block_count_to_bonus == 1:
            # Only shoot if we're facing roughly toward the bonus
            dx_to_bonus = target[0] - self.tank.rect.centerx
            dy_to_bonus = target[1] - self.tank.rect.centery
            
            # Check if we're facing the right direction (within 45 degrees)
            facing_correct = False
            if self.tank.direct == 0 and dy_to_bonus < 0 and abs(dx_to_bonus) < abs(dy_to_bonus):  # Up
                facing_correct = True
            elif self.tank.direct == 1 and dx_to_bonus > 0 and abs(dy_to_bonus) < abs(dx_to_bonus):  # Right
                facing_correct = True
            elif self.tank.direct == 2 and dy_to_bonus > 0 and abs(dx_to_bonus) < abs(dy_to_bonus):  # Down
                facing_correct = True
            elif self.tank.direct == 3 and dx_to_bonus < 0 and abs(dy_to_bonus) < abs(dx_to_bonus):  # Left
                facing_correct = True
                
            if facing_correct:
                should_shoot = True

        # Pathfinding
        if not self.path or self.path_index >= len(self.path):
            self.path = self._a_star_path(my_center, target, blocks)
            self.path_index = 0

        # Movement
        oldX, oldY = self.tank.rect.topleft
        moving_now = False
        if self.path and self.path_index < len(self.path):
            next_pos = self.path[self.path_index]
            dx = next_pos[0] - self.tank.rect.centerx
            dy = next_pos[1] - self.tank.rect.centery
            if abs(dx) > abs(dy):
                step_x = MOVE_SPEED[self.tank.rank] if dx > 0 else -MOVE_SPEED[self.tank.rank]
                step_y = 0
                new_dir = 1 if dx > 0 else 3
            else:
                step_x = 0
                step_y = MOVE_SPEED[self.tank.rank] if dy > 0 else -MOVE_SPEED[self.tank.rank]
                new_dir = 2 if dy > 0 else 0
            self.tank.rect.x += step_x
            self.tank.rect.y += step_y
            self.tank.direct = new_dir
            moving_now = True
            if abs(self.tank.rect.centerx - next_pos[0]) < MOVE_SPEED[self.tank.rank] and abs(self.tank.rect.centery - next_pos[1]) < MOVE_SPEED[self.tank.rank]:
                self.path_index += 1
        else:
            dx = target[0] - self.tank.rect.centerx
            dy = target[1] - self.tank.rect.centery
            if abs(dx) > abs(dy):
                step_x = MOVE_SPEED[self.tank.rank] if dx > 0 else -MOVE_SPEED[self.tank.rank]
                step_y = 0
                new_dir = 1 if dx > 0 else 3
            else:
                step_x = 0
                step_y = MOVE_SPEED[self.tank.rank] if dy > 0 else -MOVE_SPEED[self.tank.rank]
                new_dir = 2 if dy > 0 else 0
            self.tank.rect.x += step_x
            self.tank.rect.y += step_y
            self.tank.direct = new_dir
            moving_now = True

        # Clamp position and collision
        self.tank.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
        for obj in self.objects:
            if obj != self.tank and (obj.type == 'block' or obj.type == 'tank') and self.tank.rect.colliderect(obj.rect):
                self.tank.rect.topleft = oldX, oldY
                moving_now = False
                self.path = []
                self.path_index = 0
                break

        # Play sound if moving or stop if not
        if moving_now and not self.tank.is_moving:
            if self.tank.move_channel and self.snd_move:
                self.tank.move_channel.play(self.snd_move, loops=-1)
            self.tank.is_moving = True
        elif not moving_now and self.tank.is_moving:
            if self.tank.move_channel:
                self.tank.move_channel.stop()
            self.tank.is_moving = False

        # Shooting
        if should_shoot and self.tank.shotTimer == 0:
            from twotanks import Bullet
            Bullet(self.tank, self.tank.rect.centerx, self.tank.rect.centery,
                   DIRECTS[self.tank.direct][0] * BULLET_SPEED[self.tank.rank],
                   DIRECTS[self.tank.direct][1] * BULLET_SPEED[self.tank.rank],
                   BULLET_DAMAGE[self.tank.rank])
            if self.snd_shoot:
                self.snd_shoot.play()
            self.tank.shotTimer = SHOT_DELAY[self.tank.rank]

        if self.tank.shotTimer > 0:
            self.tank.shotTimer -= 1

    def _a_star_path(self, start, goal, blocks):
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        start_grid = (int(start[0] // TILE), int(start[1] // TILE))
        goal_grid = (int(goal[0] // TILE), int(goal[1] // TILE))

        open_set = []
        heapq.heappush(open_set, (0, start_grid))
        came_from = {}
        g_score = {start_grid: 0}
        f_score = {start_grid: heuristic(start_grid, goal_grid)}

        while open_set:
            current = heapq.heappop(open_set)[1]
            if current == goal_grid:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_grid)
                path.reverse()
                return [(p[0] * TILE + TILE // 2, p[1] * TILE + TILE // 2) for p in path]

            for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
                neighbor = (current[0] + dx, current[1] + dy)
                if not (0 <= neighbor[0] < WIDTH // TILE and 0 <= neighbor[1] < HEIGHT // TILE):
                    continue
                blocked = any((int(block.rect.x // TILE), int(block.rect.y // TILE)) == neighbor for block in blocks)
                if blocked:
                    continue
                tentative_g_score = g_score[current] + 1
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal_grid)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        return None