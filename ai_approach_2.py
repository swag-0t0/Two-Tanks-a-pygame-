import pygame
import random
import heapq

WIDTH, HEIGHT, TILE = 640, 480, 32
DIRECTS = [[0, -1], [1, 0], [0, 1], [-1, 0]]
MOVE_SPEED = [1, 2, 2, 1, 2, 3, 3, 2]
SHOT_DELAY = [60, 50, 30, 40, 30, 25, 25, 30]
BULLET_SPEED = [4, 5, 6, 5, 5, 5, 6, 7]
BULLET_DAMAGE = [1, 1, 2, 3, 2, 2, 3, 4]

class AIApproach2:
    def __init__(self, tank, objects, snd_shoot=None):
        self.tank = tank
        self.objects = objects
        self.snd_shoot = snd_shoot
        self.shoot_cooldown = 0
        self.path = []
        self.path_index = 0
        self.target = None
        self.target_type = None
        self.last_known_enemy_pos = None
        self.aggression_level = 0.7  # 0-1, higher = more aggressive
        self.has_seen_enemy = False

    def update(self):
        # Find targets
        enemy = None
        bonuses = []
        blocks = [obj for obj in self.objects if obj.type == 'block']
        
        for obj in self.objects:
            if obj.type == 'tank' and obj != self.tank:
                enemy = obj
                self.last_known_enemy_pos = (obj.rect.centerx, obj.rect.centery)
                self.has_seen_enemy = True
            elif obj.type == 'bonus':
                bonuses.append(obj)

        # Strategic target selection
        if not self.target or random.random() < 0.03:  # Re-evaluate more frequently
            self.choose_strategic_target(enemy, bonuses)

        # Get current target position
        target_pos = self.get_target_position()

        # Advanced pathfinding with obstacle avoidance
        if (not self.path or self.path_index >= len(self.path) or 
            random.random() < 0.02 or self.is_path_blocked()):
            self.path = self._a_star_path(
                (self.tank.rect.centerx, self.tank.rect.centery),
                target_pos,
                blocks
            )
            self.path_index = 0

        # Smart movement with predictive positioning
        oldX, oldY = self.tank.rect.topleft
        moving_now = False
        
        if self.path and self.path_index < len(self.path):
            next_pos = self.path[self.path_index]
            dx = next_pos[0] - self.tank.rect.centerx
            dy = next_pos[1] - self.tank.rect.centery
            
            # Choose optimal direction
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

            # Progress to next path point
            if (abs(self.tank.rect.centerx - next_pos[0]) < MOVE_SPEED[self.tank.rank] + 2 and 
                abs(self.tank.rect.centery - next_pos[1]) < MOVE_SPEED[self.tank.rank] + 2):
                self.path_index += 1

        # Enhanced collision handling
        self.tank.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
        collision = False
        for obj in self.objects:
            if obj != self.tank and (obj.type == 'block' or obj.type == 'tank') and self.tank.rect.colliderect(obj.rect):
                collision = True
                # Try to path around the obstacle
                if obj.type == 'block' and random.random() < 0.3:
                    self.path = []
                    self.path_index = 0
                break

        if collision:
            self.tank.rect.topleft = oldX, oldY
            if random.random() < 0.5:  # 50% chance to recalculate path
                self.path = []
                self.path_index = 0

        # TACTICAL SHOOTING - Competitive against FIS AI
        if self.shoot_cooldown == 0:
            should_shoot = self.should_shoot(enemy, blocks, bonuses)
            
            if should_shoot:
                from twotanks import Bullet
                Bullet(self.tank, self.tank.rect.centerx, self.tank.rect.centery,
                       DIRECTS[self.tank.direct][0] * BULLET_SPEED[self.tank.rank],
                       DIRECTS[self.tank.direct][1] * BULLET_SPEED[self.tank.rank],
                       BULLET_DAMAGE[self.tank.rank])
                if self.snd_shoot:
                    self.snd_shoot.play()
                self.shoot_cooldown = max(20, SHOT_DELAY[self.tank.rank] - 10)  # Slightly faster shooting

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

    def should_shoot(self, enemy, blocks, bonuses):
        """Advanced shooting logic to compete with FIS AI"""
        
        # 1. HIGH PRIORITY: Shoot at visible enemy
        if enemy and self.has_line_of_sight(enemy, blocks):
            # Check if we're facing the enemy
            dx = enemy.rect.centerx - self.tank.rect.centerx
            dy = enemy.rect.centery - self.tank.rect.centery
            
            facing_enemy = False
            if self.tank.direct == 0 and dy < -10 and abs(dx) < abs(dy):  # Up
                facing_enemy = True
            elif self.tank.direct == 1 and dx > 10 and abs(dy) < abs(dx):  # Right
                facing_enemy = True
            elif self.tank.direct == 2 and dy > 10 and abs(dx) < abs(dy):  # Down
                facing_enemy = True
            elif self.tank.direct == 3 and dx < -10 and abs(dy) < abs(dx):  # Left
                facing_enemy = True
                
            if facing_enemy:
                return True
        
        # 2. MEDIUM PRIORITY: Predictive shooting at last known enemy position
        if self.last_known_enemy_pos and not enemy and self.has_seen_enemy:
            if random.random() < 0.1:  # 10% chance to shoot at last known position
                return True
        
        # 3. MEDIUM PRIORITY: Clear path to bonus
        if bonuses and self.target_type == 'bonus':
            nearest_bonus = self.target
            if nearest_bonus:
                blocks_to_bonus = self.count_blocks_to_target(nearest_bonus, blocks)
                if blocks_to_bonus == 1 and random.random() < 0.3:
                    return True
        
        # 4. LOW PRIORITY: Area denial/random suppression
        if random.random() < 0.02:  # 2% chance for random shots
            return True
            
        return False

    def choose_strategic_target(self, enemy, bonuses):
        """Choose targets with high priority on bonus collection for leveling up"""
        priorities = []
        
        current_health = self.tank.hp
        current_rank = self.tank.rank
        enemy_distance = float('inf')
        if enemy:
            enemy_distance = ((enemy.rect.centerx - self.tank.rect.centerx)**2 + 
                            (enemy.rect.centery - self.tank.rect.centery)**2)

        # STRATEGY 1: HIGHEST PRIORITY - Always collect bonuses when behind in rank
        if bonuses:
            # Sort bonuses by value (star bonuses give ranks, tank bonuses give health)
            for bonus in bonuses:
                bonus_value = 2 if bonus.bonusNum == 0 else 1  # Stars are more valuable for leveling
                distance_to_bonus = ((bonus.rect.centerx - self.tank.rect.centerx)**2 + 
                                   (bonus.rect.centery - self.tank.rect.centery)**2)
                
                # Calculate priority score for each bonus
                priority_score = bonus_value * (100000 / (distance_to_bonus + 100))
                
                # Boost priority if we're behind in rank
                if enemy and current_rank < enemy.rank:
                    priority_score *= 2
                
                priorities.append((bonus, 'bonus', int(priority_score)))

        # STRATEGY 2: If we have rank advantage, be more aggressive
        if enemy and current_rank > enemy.rank and current_health >= 3:
            # We're stronger - hunt the enemy
            aggression_score = 6 + (current_rank - enemy.rank) * 2
            priorities.append((enemy, 'enemy', aggression_score))

        # STRATEGY 3: If enemy is very close and we're similar rank, engage
        elif enemy and enemy_distance < 20000 and abs(current_rank - enemy.rank) <= 1:
            priorities.append((enemy, 'enemy', 5))

        # STRATEGY 4: If low health, prioritize tank bonuses for healing
        if current_health <= 2:
            tank_bonuses = [b for b in bonuses if b.bonusNum == 1]  # Health bonuses
            if tank_bonuses:
                nearest_health_bonus = min(tank_bonuses, key=lambda b: 
                    (b.rect.centerx - self.tank.rect.centerx)**2 + 
                    (b.rect.centery - self.tank.rect.centery)**2)
                priorities.append((nearest_health_bonus, 'bonus', 8))  # Very high priority

        # STRATEGY 5: Default to bonus collection if no immediate threats
        if not priorities and bonuses:
            nearest_bonus = min(bonuses, key=lambda b: 
                (b.rect.centerx - self.tank.rect.centerx)**2 + 
                (b.rect.centery - self.tank.rect.centery)**2)
            priorities.append((nearest_bonus, 'bonus', 4))

        # STRATEGY 6: Fallback - strategic positioning near bonus spawn areas
        bonus_hotspots = [
            (WIDTH//4, HEIGHT//4),      # Top-left common bonus area
            (3*WIDTH//4, HEIGHT//4),    # Top-right common bonus area  
            (WIDTH//4, 3*HEIGHT//4),    # Bottom-left common bonus area
            (3*WIDTH//4, 3*HEIGHT//4),  # Bottom-right common bonus area
            (WIDTH//2, HEIGHT//2),      # Center bonus area
        ]
        strategic_pos = random.choice(bonus_hotspots)
        priorities.append((strategic_pos, 'strategic', 2))

        # Choose the highest priority target
        if priorities:
            # Sort by priority score (highest first)
            priorities.sort(key=lambda x: x[2], reverse=True)
            self.target = priorities[0][0]
            self.target_type = priorities[0][1]
        else:
            # Default to center if no targets found
            self.target = (WIDTH//2, HEIGHT//2)
            self.target_type = 'strategic'
    
    def find_safe_position(self, enemy):
        """Find a position away from enemy"""
        if not enemy:
            return (WIDTH//2, HEIGHT//2)
            
        # Move to opposite side of map from enemy
        safe_x = WIDTH - enemy.rect.centerx if enemy.rect.centerx < WIDTH//2 else WIDTH//4
        safe_y = HEIGHT - enemy.rect.centery if enemy.rect.centery < HEIGHT//2 else HEIGHT//4
        
        return (safe_x, safe_y)

    def count_blocks_to_target(self, target, blocks):
        """Count how many blocks are between tank and target"""
        start = (self.tank.rect.centerx, self.tank.rect.centery)
        end = (target.rect.centerx, target.rect.centery)
        
        steps = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
        if steps == 0:
            return 0
            
        block_set = set()
        for i in range(1, int(steps)):
            t = i / steps
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            
            for block in blocks:
                if block.rect.collidepoint(x, y):
                    block_set.add(id(block))
                    break
        return len(block_set)

    def is_path_blocked(self):
        """Check if current path is blocked by dynamic obstacles"""
        if not self.path or self.path_index >= len(self.path):
            return False
            
        # Check next few path points for tanks
        for i in range(self.path_index, min(self.path_index + 3, len(self.path))):
            path_point = self.path[i]
            for obj in self.objects:
                if obj.type == 'tank' and obj != self.tank:
                    distance = ((obj.rect.centerx - path_point[0])**2 + 
                               (obj.rect.centery - path_point[1])**2)
                    if distance < 400:  # If tank is near path
                        return True
        return False

    def get_target_position(self):
        if hasattr(self.target, 'rect'):
            return (self.target.rect.centerx, self.target.rect.centery)
        else:
            return self.target

    def has_line_of_sight(self, target, blocks):
        start = (self.tank.rect.centerx, self.tank.rect.centery)
        end = (target.rect.centerx, target.rect.centery)
        
        steps = max(abs(end[0] - start[0]), abs(end[1] - start[1]))
        if steps == 0:
            return True
            
        for i in range(1, int(steps)):
            t = i / steps
            x = start[0] + (end[0] - start[0]) * t
            y = start[1] + (end[1] - start[1]) * t
            
            for block in blocks:
                if block.rect.collidepoint(x, y):
                    return False
        return True

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
                
                blocked = any(
                    (int(block.rect.x // TILE), int(block.rect.y // TILE)) == neighbor 
                    for block in blocks
                )
                if blocked:
                    continue

                tentative_g_score = g_score[current] + 1
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal_grid)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        return None