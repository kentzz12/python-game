import pygame
import random
import math
import noise
import os
from pygame.locals import *
from pygame import mixer
from collections import defaultdict

# Initialize pygame
pygame.init()
mixer.init()

# Game constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
TILE_SIZE = 40
PLAYER_SIZE = 30
GRAVITY = 0.5
JUMP_STRENGTH = -20
WORLD_WIDTH = 200 * TILE_SIZE
CHUNK_SIZE = 8  # In tiles
BOSS_ARENA_WIDTH = 15 * TILE_SIZE  # Width of boss arena

# Colors
SKY_BLUE = (135, 206, 235)
SKY_NIGHT = (10, 10, 50)
GRASS_GREEN = (34, 139, 34)
DIRT_BROWN = (139, 69, 19)
STONE_GRAY = (105, 105, 105)
BEDROCK_GRAY = (50, 50, 50)
WATER_BLUE = (65, 105, 225)
LAVA_ORANGE = (207, 16, 32)
PLAYER_SKIN = (255, 213, 170)
PLAYER_SHIRT = (30, 144, 255)
PLAYER_PANTS = (25, 25, 112)
ENEMY_RED = (255, 50, 50)
ENEMY_GREEN = (50, 255, 50)
ENEMY_BLUE = (50, 50, 255)
COIN_YELLOW = (255, 215, 0)
GOAL_FLAG = (200, 0, 0)
BOSS_PURPLE = (150, 0, 150)

# Load sounds
try:
    jump_sound = mixer.Sound('jump.wav')
    break_sound = mixer.Sound('break.wav')
    place_sound = mixer.Sound('place.wav')
    hurt_sound = mixer.Sound('hurt.wav')
    coin_sound = mixer.Sound('coin.wav')
    attack_sound = mixer.Sound('attack.wav')
    level_complete_sound = mixer.Sound('level_complete.wav')
    boss_roar_sound = mixer.Sound('boss_roar.wav')
    boss_death_sound = mixer.Sound('boss_death.wav')
    background_music = 'background.mp3'
    mixer.music.load(background_music)
    mixer.music.set_volume(0.5)
    mixer.music.play(-1)  # Loop indefinitely
except:
    print("Warning: Sound files not found. Continuing without sound.")
    jump_sound = None
    break_sound = None
    place_sound = None
    hurt_sound = None
    coin_sound = None
    attack_sound = None
    level_complete_sound = None
    boss_roar_sound = None
    boss_death_sound = None

# Create screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Enhanced Blocky Adventure")
clock = pygame.time.Clock()

class Particle:
    def __init__(self, x, y, color, velocity, lifetime):
        self.x = x
        self.y = y
        self.color = color
        self.velocity = velocity
        self.lifetime = lifetime
        self.size = random.randint(2, 5)
    
    def update(self):
        self.x += self.velocity[0]
        self.y += self.velocity[1]
        self.velocity[1] += 0.1  # Gravity
        self.lifetime -= 1
        return self.lifetime > 0
    
    def draw(self, offset):
        pygame.draw.circle(
            screen,
            self.color,
            (int(self.x - offset[0]), int(self.y - offset[1])),
            max(1, int(self.size * (self.lifetime / 20)))
        )

class ParticleSystem:
    def __init__(self):
        self.particles = []
    
    def add_particles(self, x, y, color, count=10):
        for _ in range(count):
            velocity = [random.uniform(-2, 2), random.uniform(-5, -1)]
            self.particles.append(Particle(x, y, color, velocity, random.randint(20, 40)))
    
    def update(self):
        self.particles = [p for p in self.particles if p.update()]
    
    def draw(self, offset):
        for p in self.particles:
            p.draw(offset)

class Entity:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
    
    def update_physics(self, blocks):
        self.vel_y += GRAVITY
        self.x += self.vel_x
        self.y += self.vel_y
        
        self.on_ground = False
        nearby_blocks = world.get_nearby_blocks(self.x, self.y)
        
        for block in nearby_blocks:
            if self.check_collision(block):
                if self.vel_y > 0 and self.y + self.height > block.y and self.y < block.y:
                    self.y = block.y - self.height
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0 and self.y < block.y + TILE_SIZE and self.y + self.height > block.y + TILE_SIZE:
                    self.y = block.y + TILE_SIZE
                    self.vel_y = 0
                elif self.vel_x > 0 and self.x + self.width > block.x and self.x < block.x:
                    self.x = block.x - self.width
                    self.vel_x = 0
                elif self.vel_x < 0 and self.x < block.x + TILE_SIZE and self.x + self.width > block.x + TILE_SIZE:
                    self.x = block.x + TILE_SIZE
                    self.vel_x = 0
    
    def check_collision(self, block):
        return (self.x + self.width > block.x and 
                self.x < block.x + TILE_SIZE and 
                self.y + self.height > block.y and 
                self.y < block.y + TILE_SIZE)

class Player(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_SIZE, PLAYER_SIZE * 1.5)
        self.is_jumping = False
        self.facing = "right"
        self.animation_frame = 0
        self.inventory = {"grass": 20, "dirt": 20, "stone": 10, "wood": 5, "coin": 0, "iron": 0}
        self.selected_block = "grass"
        self.health = 100
        self.max_health = 100
        self.invincible = 0
        self.attack_cooldown = 0
        self.attacking = False
        self.attack_frame = 0
    
    def update(self, blocks, enemies, items):
        super().update_physics(blocks)
        self.is_jumping = not self.on_ground
        
        # Keep player in world bounds
        self.x = max(0, min(self.x, WORLD_WIDTH - self.width))
        
        # Update animation frame if moving
        if abs(self.vel_x) > 0.1 or abs(self.vel_y) > 0.1:
            self.animation_frame += 0.2
            if self.animation_frame >= 4:
                self.animation_frame = 0
        
        # Attack cooldown
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        # Attack animation
        if self.attacking:
            self.attack_frame += 0.5
            if self.attack_frame >= 4:
                self.attacking = False
                self.attack_frame = 0
        
        # Check enemy collisions
        if self.invincible <= 0:
            for enemy in enemies[:]:
                if (self.x < enemy.x + enemy.width and
                    self.x + self.width > enemy.x and
                    self.y < enemy.y + enemy.height and
                    self.y + self.height > enemy.y):
                    self.health -= enemy.damage
                    self.invincible = 60  # 1 second invincibility
                    if hurt_sound: hurt_sound.play()
                    # Knockback
                    if enemy.x < self.x:
                        self.vel_x = 5
                    else:
                        self.vel_x = -5
                    self.vel_y = -5
                    break
        else:
            self.invincible -= 1
        
        # Check item collisions
        for item in items[:]:
            if (self.x < item.x + item.width and
                self.x + self.width > item.x and
                self.y < item.y + item.height and
                self.y + self.height > item.y):
                self.inventory[item.type] += 1
                if coin_sound and item.type == "coin": coin_sound.play()
                items.remove(item)
                particle_system.add_particles(item.x + item.width//2, item.y + item.height//2, 
                                           COIN_YELLOW if item.type == "coin" else (150, 150, 150), 
                                           15)
    
    def jump(self):
        if self.on_ground and not self.is_jumping:
            self.vel_y = JUMP_STRENGTH
            self.is_jumping = True
            if jump_sound: jump_sound.play()
    
    def attack(self, enemies):
        if self.attack_cooldown <= 0:
            self.attacking = True
            self.attack_cooldown = 20
            if attack_sound: attack_sound.play()
            
            attack_rect = pygame.Rect(
                self.x - 1000 if self.facing == "left" else self.x + self.width,
                self.y + 10,
                1000,
                self.height - 20
            )
            
            for enemy in enemies[:]:
                enemy_rect = pygame.Rect(enemy.x, enemy.y, enemy.width, enemy.height)
                if attack_rect.colliderect(enemy_rect):
                    # Reduced damage against boss
                    damage = 5 if enemy.type == "boss" else 20
                    enemy.health -= damage
                    
                    particle_system.add_particles(
                        enemy.x + enemy.width//2,
                        enemy.y + enemy.height//2,
                        ENEMY_RED,
                        10
                    )
                    
                    if enemy.health <= 0:
                        enemies.remove(enemy)
                        # Drop more items when boss dies
                        drop_count = 10 if enemy.type == "boss" else random.randint(1, 3)
                        for _ in range(drop_count):
                            items.append(Item(
                                enemy.x + random.randint(-10, 10),
                                enemy.y + random.randint(-10, 10),
                                "coin" if random.random() < 0.7 else "iron"
                            ))
    
    def draw(self, offset):
        leg_swing = math.sin(self.animation_frame * math.pi) * 5
        head_x = self.x + (self.width - PLAYER_SIZE//2) // 2
        head_y = self.y

        # Head
        pygame.draw.rect(screen, PLAYER_SKIN, (head_x - offset[0], head_y - offset[1], PLAYER_SIZE//2, PLAYER_SIZE//2))

        # Body
        pygame.draw.rect(screen, PLAYER_SHIRT, 
                        (self.x + 5 - offset[0], self.y + PLAYER_SIZE//2 - offset[1], self.width - 10, PLAYER_SIZE//2))

        # Legs
        pygame.draw.rect(screen, PLAYER_PANTS, 
                        (self.x + 5 - offset[0], self.y + PLAYER_SIZE - offset[1], PLAYER_SIZE//3, PLAYER_SIZE//2 + leg_swing))
        pygame.draw.rect(screen, PLAYER_PANTS, 
                        (self.x + self.width - 5 - PLAYER_SIZE//3 - offset[0], self.y + PLAYER_SIZE - offset[1], PLAYER_SIZE//3, PLAYER_SIZE//2 - leg_swing))

        # Eyes
        pygame.draw.rect(screen, (0, 0, 0), (head_x + 8 - offset[0], head_y + 8 - offset[1], 3, 3))
        pygame.draw.rect(screen, (0, 0, 0), (head_x + 18 - offset[0], head_y + 8 - offset[1], 3, 3))
        # Sword (simple visual cue)
        if self.attacking:
            if self.facing == "right":
            # Sword extends right (40px long)
                pygame.draw.rect(screen, (160, 160, 160), 
                                 (self.x + self.width - offset[0], self.y + self.height//2 - offset[1], 100, 5))
            else:
            # Sword extends left (40px long)
                pygame.draw.rect(screen, (160, 160, 160), 
                                 (self.x - 40 - offset[0], self.y + self.height//2 - offset[1], 100, 5))

class Enemy(Entity):
    def __init__(self, x, y, enemy_type):
        # Boss is much larger
        if enemy_type == "boss":
            width = PLAYER_SIZE * 6
            height = PLAYER_SIZE * 7
        else:
            width = PLAYER_SIZE
            height = PLAYER_SIZE * 1.5
            
        super().__init__(x, y, width, height)
        self.type = enemy_type
        self.health = 30 if enemy_type == "zombie" else 20 if enemy_type == "slime" else 40 if enemy_type == "ice_golem" else 200  # Boss has more health
        self.max_health = self.health
        self.speed = 1 if enemy_type == "zombie" else 1.5 if enemy_type == "slime" else 0.7 if enemy_type == "ice_golem" else 0.8  # Boss is slightly faster
        self.damage = 10 if enemy_type == "zombie" else 5 if enemy_type == "slime" else 15 if enemy_type == "ice_golem" else 25  # Boss hits harder
        self.direction = 1  # 1 for right, -1 for left
        self.animation_frame = 0
        self.idle_timer = random.randint(0, 100)
        self.attack_cooldown = 0
        self.activated = False  # For boss activation
        self.attack_patterns = ["jump", "projectile", "charge"]
        self.current_pattern = None
        self.pattern_timer = 0
    
    def update(self, blocks, player):
        # Boss-specific behavior
        if self.type == "boss":
            # Activate when player gets close
            if not self.activated and abs(player.x - self.x) < 400:
                self.activated = True
                if boss_roar_sound: 
                    boss_roar_sound.play()
                # Screen shake effect
                for _ in range(10):
                    camera_offset[0] += random.randint(-5, 5)
                    camera_offset[1] += random.randint(-5, 5)
            
            # Only attack if activated
            if self.activated:
                if self.attack_cooldown <= 0:
                    # Choose new attack pattern
                    self.current_pattern = random.choice(self.attack_patterns)
                    self.pattern_timer = 120  # 2 seconds per pattern
                    self.attack_cooldown = 60  # 1 second cooldown
                
                self.pattern_timer -= 1
                
                # Execute current pattern
                if self.current_pattern == "jump":
                    if self.on_ground and self.pattern_timer == 100:
                        self.vel_y = -20  # Big jump
                elif self.current_pattern == "projectile":
                    if self.pattern_timer % 30 == 0:  # Shoot every 0.5 seconds
                        # Shoot in player's direction
                        dx = player.x - self.x
                        dy = player.y - self.y
                        dist = max(1, math.sqrt(dx*dx + dy*dy))
                        projectiles.append(Projectile(
                            self.x + self.width//2,
                            self.y + self.height//2,
                            dx/dist * 6, dy/dist * 6, 
                            "boss_fire"
                        ))
                elif self.current_pattern == "charge":
                    if self.pattern_timer > 60:
                        # Charge toward player
                        if player.x < self.x:
                            self.vel_x = -5
                        else:
                            self.vel_x = 5
                    else:
                        self.vel_x = 0
                
                self.attack_cooldown -= 1
        else:
            # Normal enemy behavior
            if abs(self.x - player.x) < 300:
                if player.x < self.x:
                    self.direction = -1
                else:
                    self.direction = 1
                
                # Special behavior for different enemies
                if self.type == "zombie":
                    self.vel_x = self.direction * self.speed
                elif self.type == "slime":
                    if self.on_ground and abs(self.x - player.x) < 100:
                        self.vel_y = -10  # Jump toward player
                    self.vel_x = self.direction * self.speed
                elif self.type == "ice_golem":
                    if self.idle_timer <= 0 and abs(self.x - player.x) < 200:
                        # Shoot ice projectile
                        projectiles.append(Projectile(
                            self.x + self.width//2,
                            self.y + self.height//2,
                            self.direction * 5, 0, "ice"
                        ))
                        self.idle_timer = 120  # 2 second cooldown
                    self.vel_x = self.direction * self.speed * 0.5
            else:
                # Random wandering
                if random.random() < 0.01:
                    self.direction *= -1
                self.vel_x = self.direction * self.speed
            
            if self.type in ["ice_golem"]:
                self.idle_timer -= 1
        
        super().update_physics(blocks)
        
        # Animation
        if abs(self.vel_x) > 0.1 or abs(self.vel_y) > 0.1:
            self.animation_frame += 0.1
            if self.animation_frame >= 4:
                self.animation_frame = 0
    
    def draw(self, offset):
        if self.type == "boss":
            # Draw boss
            body_x = self.x - offset[0]
            body_y = self.y - offset[1]
            
            # Main body
            pygame.draw.rect(screen, BOSS_PURPLE, 
                            (body_x, body_y, self.width, self.height))
            
            # Eyes (glowing red)
            pygame.draw.circle(screen, (255, 50, 50), 
                             (int(body_x + self.width//4), 
                              int(body_y + self.height//3)), 10)
            pygame.draw.circle(screen, (255, 50, 50), 
                             (int(body_x + self.width*3//4), 
                              int(body_y + self.height//3)), 10)

            # Health bar
            health_width = int((self.health / self.max_health) * self.width)
            pygame.draw.rect(screen, (255, 0, 0), 
                           (body_x, body_y - 20, self.width, 10))
            pygame.draw.rect(screen, (0, 255, 0), 
                           (body_x, body_y - 20, health_width, 10))
            
            # Health text
            font = pygame.font.SysFont(None, 20)
            health_text = font.render(f"{self.health}/{self.max_health}", True, (255, 255, 255))
            screen.blit(health_text, 
                       (body_x + self.width//2 - health_text.get_width()//2, 
                        body_y - 25))
            
            # Spikes/horns
            pygame.draw.polygon(screen, (100, 0, 100), [
                (body_x + 10, body_y),
                (body_x + self.width//2, body_y - 30),
                (body_x + self.width - 10, body_y)
            ])
        elif self.type == "zombie":
            color = ENEMY_RED
        elif self.type == "slime":
            color = ENEMY_GREEN
        elif self.type == "ice_golem":
            color = ENEMY_BLUE
        
        if self.type != "boss":
            leg_swing = math.sin(self.animation_frame * math.pi) * 5
            head_x = self.x + (self.width - PLAYER_SIZE//2) // 2
            head_y = self.y
            
            if self.type == "slime":
                # Draw slime as a blob
                pygame.draw.ellipse(screen, color, 
                                  (self.x - offset[0], self.y - offset[1] + 5, self.width, self.height - 10))
                # Eyes
                eye_offset = 0
                if abs(self.animation_frame - 2) < 0.5:  # Squish animation
                    eye_offset = 2
                pygame.draw.ellipse(screen, (0, 0, 0), 
                                  (self.x + 10 - offset[0], self.y + 15 - offset[1] - eye_offset, 8, 8))
                pygame.draw.ellipse(screen, (0, 0, 0), 
                                  (self.x + self.width - 18 - offset[0], self.y + 15 - offset[1] - eye_offset, 8, 8))
                return
            else:
                pygame.draw.rect(screen, color, (head_x - offset[0], head_y - offset[1], PLAYER_SIZE//2, PLAYER_SIZE//2))
            
            # Body
            pygame.draw.rect(screen, (color[0]//2, color[1]//2, color[2]//2), 
                            (self.x + 5 - offset[0], self.y + PLAYER_SIZE//2 - offset[1], self.width - 10, PLAYER_SIZE//2))
            
            # Legs
            pygame.draw.rect(screen, (color[0]//3, color[1]//3, color[2]//3), 
                            (self.x + 5 - offset[0], self.y + PLAYER_SIZE - offset[1], PLAYER_SIZE//3, PLAYER_SIZE//2 + leg_swing))
            pygame.draw.rect(screen, (color[0]//3, color[1]//3, color[2]//3), 
                            (self.x + self.width - 5 - PLAYER_SIZE//3 - offset[0], self.y + PLAYER_SIZE - offset[1], PLAYER_SIZE//3, PLAYER_SIZE//2 - leg_swing))
            
            # Eyes
            pygame.draw.rect(screen, (0, 0, 0), (head_x + 8 - offset[0], head_y + 8 - offset[1], 3, 3))
            pygame.draw.rect(screen, (0, 0, 0), (head_x + 18 - offset[0], head_y + 8 - offset[1], 3, 3))
            
            # Special features for ice golem
            if self.type == "ice_golem":
                # Icicles
                for i in range(3):
                    pygame.draw.polygon(screen, (200, 200, 255), [
                        (head_x + 5 + i*10 - offset[0], head_y - 5 - offset[1]),
                        (head_x + 10 + i*10 - offset[0], head_y - 15 - offset[1]),
                        (head_x + 15 + i*10 - offset[0], head_y - 5 - offset[1])
                    ])

class Projectile:
    def __init__(self, x, y, vel_x, vel_y, proj_type):
        self.x = x
        self.y = y
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.type = proj_type
        self.lifetime = 60  # 1 second
        self.size = 10
        self.glow = 0  # For boss projectiles
    
    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.lifetime -= 1
        
        if self.type == "boss_fire":
            self.glow = (self.glow + 0.1) % (2 * math.pi)
            
        return self.lifetime > 0
    
    def draw(self, offset):
        if self.type == "ice":
            pygame.draw.circle(screen, (200, 200, 255), 
                             (int(self.x - offset[0]), int(self.y - offset[1])), 
                             self.size)
        elif self.type == "fire":
            pygame.draw.circle(screen, (255, 100, 0), 
                             (int(self.x - offset[0]), int(self.y - offset[1])), 
                             self.size)
        elif self.type == "boss_fire":
            # Draw pulsing fireball
            glow_size = int(math.sin(self.glow) * 5)
            pygame.draw.circle(screen, (255, 200, 0), 
                             (int(self.x - offset[0]), int(self.y - offset[1])), 
                             self.size + glow_size)
            pygame.draw.circle(screen, (255, 100, 0), 
                             (int(self.x - offset[0]), int(self.y - offset[1])), 
                             self.size)

class Item:
    def __init__(self, x, y, item_type):
        self.x = x
        self.y = y
        self.type = item_type
        self.width = 15
        self.height = 15
        self.bob_offset = random.random() * math.pi * 2
        self.bob_speed = random.uniform(0.05, 0.1)
    
    def update(self):
        self.bob_offset += self.bob_speed
    
    def draw(self, offset):
        y_offset = math.sin(self.bob_offset) * 5
        if self.type == "coin":
            pygame.draw.circle(screen, COIN_YELLOW, 
                             (int(self.x - offset[0] + self.width//2), 
                              int(self.y - offset[1] + self.height//2 + y_offset)), 
                             self.width//2)
            # Add shine to coin
            pygame.draw.circle(screen, (255, 255, 200), 
                             (int(self.x - offset[0] + self.width//2 + 3), 
                              int(self.y - offset[1] + self.height//2 + y_offset - 3)), 
                             3)
        elif self.type == "iron":
            pygame.draw.rect(screen, (150, 150, 150), 
                           (int(self.x - offset[0]), 
                            int(self.y - offset[1] + y_offset), 
                            self.width, self.height))
            # Add shine
            pygame.draw.rect(screen, (200, 200, 200), 
                           (int(self.x - offset[0] + 3), 
                            int(self.y - offset[1] + y_offset + 3), 
                            5, 5))

class GoalFlag:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = TILE_SIZE
        self.height = TILE_SIZE * 3
        self.wave_offset = 0
    
    def update(self):
        self.wave_offset += 0.1
    
    def draw(self, offset):
        # Bigger pole
        pygame.draw.rect(screen, (139, 69, 19), 
                        (self.x - offset[0], self.y - offset[1], 10, self.height))
        
        # Bigger waving red flag
        flag_height = 60
        flag_width = 80 + math.sin(self.wave_offset) * 10  # animate width a bit
        top_y = self.y - offset[1] + 20
        pygame.draw.polygon(screen, GOAL_FLAG, [
            (self.x - offset[0] + 10, top_y),
            (self.x - offset[0] + 10 + flag_width, top_y + flag_height // 3),
            (self.x - offset[0] + 10, top_y + flag_height)
        ])

class Block:
    def __init__(self, x, y, block_type):
        self.x = x
        self.y = y
        self.type = block_type
        if block_type == "stone":
            self.health = 5
        elif block_type == "dirt":
            self.health = 3
        elif block_type == "wood":
            self.health = 4
        elif block_type == "iron":
            self.health = 8
        elif block_type == "bedrock":
            self.health = float('inf')  # Unbreakable
        else:
            self.health = 1
   
    def draw(self, offset, time_of_day=0):
        if self.type == "grass":
            color = GRASS_GREEN
        elif self.type == "dirt":
            color = DIRT_BROWN
        elif self.type == "stone":
            color = STONE_GRAY
        elif self.type == "bedrock":
            color = BEDROCK_GRAY
        elif self.type == "water":
            # Animate water with time_of_day
            wave = math.sin(time_of_day + self.x/50) * 2
            color = (WATER_BLUE[0], WATER_BLUE[1], min(255, WATER_BLUE[2] + 30))
            pygame.draw.rect(screen, color, (self.x - offset[0], self.y - offset[1] + wave, TILE_SIZE, TILE_SIZE))
            
            # Draw wave lines
            for i in range(3):
                wave_height = math.sin(time_of_day + self.x/50 + i) * 3
                pygame.draw.line(screen, (WATER_BLUE[0]-20, WATER_BLUE[1]-20, WATER_BLUE[2]+20),
                                (self.x - offset[0], self.y - offset[1] + TILE_SIZE//2 + wave_height),
                                (self.x - offset[0] + TILE_SIZE, self.y - offset[1] + TILE_SIZE//2 + wave_height - 2), 1)
            return
        elif self.type == "lava":
            # Animate lava
            bubble = math.sin(time_of_day * 2 + self.x/30) * 3
            color = (LAVA_ORANGE[0], LAVA_ORANGE[1], LAVA_ORANGE[2])
            pygame.draw.rect(screen, color, (self.x - offset[0], self.y - offset[1], TILE_SIZE, TILE_SIZE))
            
            # Draw bubbles
            for i in range(3):
                bubble_size = abs(math.sin(time_of_day * 3 + self.x/20 + i*2)) * 5
                bubble_x = self.x - offset[0] + 5 + i*10
                bubble_y = self.y - offset[1] + TILE_SIZE - 5 - abs(math.sin(time_of_day + i) * 5)
                pygame.draw.circle(screen, (255, 100 + i*20, 0), 
                                 (int(bubble_x), int(bubble_y)), 
                                 int(bubble_size))
            return
        elif self.type == "wood":
            color = (101, 67, 33)
        elif self.type == "iron":
            color = (150, 150, 150)
        
        pygame.draw.rect(screen, color, (self.x - offset[0], self.y - offset[1], TILE_SIZE, TILE_SIZE))
        
        # Add texture details
        if self.type == "grass":
            pygame.draw.rect(screen, (GRASS_GREEN[0]-20, GRASS_GREEN[1]-20, GRASS_GREEN[2]-20), 
                            (self.x - offset[0] + 5, self.y - offset[1] + 5, TILE_SIZE-10, 5))
        elif self.type == "stone":
            for i in range(3):
                x_pos = random.randint(5, TILE_SIZE-10)
                y_pos = random.randint(5, TILE_SIZE-10)
                pygame.draw.rect(screen, (STONE_GRAY[0]+20, STONE_GRAY[1]+20, STONE_GRAY[2]+20), 
                                (self.x - offset[0] + x_pos, self.y - offset[1] + y_pos, 3, 3))
        elif self.type == "wood":
            # Draw wood grain
            for i in range(5):
                pygame.draw.rect(screen, (color[0]-20, color[1]-20, color[2]-20), 
                                (self.x - offset[0] + 5, self.y - offset[1] + 5 + i*6, TILE_SIZE-10, 3))
        elif self.type == "iron":
            # Draw metal plates
            for i in range(2):
                for j in range(2):
                    pygame.draw.rect(screen, (color[0]+20, color[1]+20, color[2]+20), 
                                    (self.x - offset[0] + 5 + i*15, self.y - offset[1] + 5 + j*15, 10, 10))
    
class World:
    def __init__(self):
        self.blocks = []
        self.grid = {}  # Dictionary to store blocks by chunk
        self.generated_chunks = set()
        self.goal_flag = None
        self.boss_arena_ceiling = []  # To track ceiling blocks
    
    def add_block(self, block):
        self.blocks.append(block)
        chunk_x = int(block.x // (TILE_SIZE * CHUNK_SIZE))
        chunk_y = int(block.y // (TILE_SIZE * CHUNK_SIZE))
        if (chunk_x, chunk_y) not in self.grid:
            self.grid[(chunk_x, chunk_y)] = []
        self.grid[(chunk_x, chunk_y)].append(block)
    
    def remove_block(self, block):
        self.blocks.remove(block)
        chunk_x = int(block.x // (TILE_SIZE * CHUNK_SIZE))
        chunk_y = int(block.y // (TILE_SIZE * CHUNK_SIZE))
        if (chunk_x, chunk_y) in self.grid and block in self.grid[(chunk_x, chunk_y)]:
            self.grid[(chunk_x, chunk_y)].remove(block)
    
    def get_nearby_blocks(self, x, y, radius=3):
        """Get blocks within 'radius' chunks of the player's position"""
        nearby = []
        chunk_x = int(x // (TILE_SIZE * CHUNK_SIZE))
        chunk_y = int(y // (TILE_SIZE * CHUNK_SIZE))
        
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if (chunk_x + dx, chunk_y + dy) in self.grid:
                    nearby.extend(self.grid[(chunk_x + dx, chunk_y + dy)])
        return nearby
    
    def generate_level_1(self):
        """Generate level 1 terrain"""
        self.blocks = []
        self.grid = {}
        self.generated_chunks = set()
        
        # Generate flat terrain with some hills
        for x in range(0, WORLD_WIDTH, TILE_SIZE):
            height_variation = int(noise.pnoise1(x * 0.01, repeat=999999) * TILE_SIZE)
            surface_y = SCREEN_HEIGHT - TILE_SIZE * 3 + height_variation
            
            # Surface layer
            self.add_block(Block(x, surface_y, "grass"))
            
            # Dirt layer
            dirt_depth = random.randint(3, 5)
            for y_pos in range(surface_y + TILE_SIZE, surface_y + TILE_SIZE * dirt_depth, TILE_SIZE):
                self.add_block(Block(x, y_pos, "dirt"))
            
            # Stone layer
            for y_pos in range(surface_y + TILE_SIZE * dirt_depth, SCREEN_HEIGHT + TILE_SIZE * 10, TILE_SIZE):
                self.add_block(Block(x, y_pos, "stone"))
            
            # Bedrock
            self.add_block(Block(x, SCREEN_HEIGHT + TILE_SIZE * 10, "bedrock"))
            
            # Generate trees occasionally
            if random.random() < 0.03 and surface_y < SCREEN_HEIGHT - TILE_SIZE * 5:
                tree_height = random.randint(4, 6)
                # Trunk
                for y_pos in range(surface_y - TILE_SIZE * tree_height, surface_y, TILE_SIZE):
                    self.add_block(Block(x, y_pos, "wood"))
                # Leaves
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == -1:  # Skip top center (already wood)
                            continue
                        self.add_block(Block(x + dx * TILE_SIZE, surface_y - TILE_SIZE * tree_height - TILE_SIZE, "grass"))
        
        # Add some water pools
        for _ in range(5):
            pool_x = random.randint(5, WORLD_WIDTH // TILE_SIZE - 10) * TILE_SIZE
            pool_width = random.randint(3, 7)
            surface_block = next((b for b in self.blocks if b.x == pool_x and b.type == "grass"), None)
            if surface_block:
                for dx in range(pool_width):
                    self.add_block(Block(pool_x + dx * TILE_SIZE, surface_block.y + TILE_SIZE, "water"))
        
        # Add goal flag at the end
        self.goal_flag = GoalFlag(WORLD_WIDTH - TILE_SIZE * 10, SCREEN_HEIGHT - TILE_SIZE * 4)
        
        # Mark all chunks as generated
        for x in range(0, WORLD_WIDTH, CHUNK_SIZE * TILE_SIZE):
            for y in range(0, SCREEN_HEIGHT * 2, CHUNK_SIZE * TILE_SIZE):
                chunk_x = x // (CHUNK_SIZE * TILE_SIZE)
                chunk_y = y // (CHUNK_SIZE * TILE_SIZE)
                self.generated_chunks.add((chunk_x, chunk_y))
    
    def generate_level_2(self):
        """Generate level 2 with boss arena at the end"""
        self.blocks = []
        self.grid = {}
        self.generated_chunks = set()
        self.boss_arena_ceiling = []
        
        # Generate more varied terrain with caves
        for x in range(0, WORLD_WIDTH, TILE_SIZE):
            # Base terrain height
            height_variation = int(noise.pnoise1(x * 0.005, repeat=999999) * TILE_SIZE * 3)
            surface_y = SCREEN_HEIGHT - TILE_SIZE * 3 + height_variation
            
            # Cave generation
            cave = noise.pnoise2(x * 0.05, 0) > 0.2
            
            if not cave:
                # Surface layer - different biomes
                biome = noise.pnoise1(x * 0.003, repeat=999999)
                if biome > 0.3:
                    # Snow biome
                    self.add_block(Block(x, surface_y, "stone"))  # Snow blocks would go here
                elif biome < -0.3:
                    # Desert biome
                    self.add_block(Block(x, surface_y, "dirt"))  # Sand blocks would go here
                else:
                    # Grass biome
                    self.add_block(Block(x, surface_y, "grass"))
                
                # Underground layers
                dirt_depth = random.randint(2, 4)
                for y_pos in range(surface_y + TILE_SIZE, surface_y + TILE_SIZE * dirt_depth, TILE_SIZE):
                    self.add_block(Block(x, y_pos, "dirt"))
                
                # Stone layer with occasional iron
                for y_pos in range(surface_y + TILE_SIZE * dirt_depth, SCREEN_HEIGHT + TILE_SIZE * 10, TILE_SIZE):
                    if random.random() < 0.1:  # 10% chance for iron
                        self.add_block(Block(x, y_pos, "iron"))
                    else:
                        self.add_block(Block(x, y_pos, "stone"))
                
                # Bedrock
                self.add_block(Block(x, SCREEN_HEIGHT + TILE_SIZE * 10, "bedrock"))
            
            # Generate trees in grass biome
            biome = noise.pnoise1(x * 0.003, repeat=999999)
            if -0.3 <= biome <= 0.3 and random.random() < 0.05 and surface_y < SCREEN_HEIGHT - TILE_SIZE * 5 and not cave:
                tree_height = random.randint(4, 6)
                # Trunk
                for y_pos in range(surface_y - TILE_SIZE * tree_height, surface_y, TILE_SIZE):
                    self.add_block(Block(x, y_pos, "wood"))
                # Leaves
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx == 0 and dy == -1:  # Skip top center (already wood)
                            continue
                        self.add_block(Block(x + dx * TILE_SIZE, surface_y - TILE_SIZE * tree_height - TILE_SIZE, "grass"))
            
            # Generate lava pools underground
            if surface_y > SCREEN_HEIGHT and random.random() < 0.02 and not cave:
                pool_width = random.randint(2, 5)
                for dx in range(pool_width):
                    self.add_block(Block(x + dx * TILE_SIZE, surface_y + random.randint(2, 5) * TILE_SIZE, "lava"))
        
            # Add floating platforms for platforming challenge
            for _ in range(20):
                max_tiles = WORLD_WIDTH // TILE_SIZE - (BOSS_ARENA_WIDTH // TILE_SIZE) - 10
                if max_tiles <= 5:
                    continue  # Skip this loop iteration if the range would be invalid

                platform_x = random.randint(5, max_tiles) * TILE_SIZE
                platform_y = random.randint(SCREEN_HEIGHT // 2, SCREEN_HEIGHT - TILE_SIZE * 3)
                platform_width = random.randint(3, 7)

                for dx in range(platform_width):
                    self.add_block(Block(platform_x + dx * TILE_SIZE, platform_y, "stone"))

        # Create boss arena at the end
        arena_start_x = WORLD_WIDTH - BOSS_ARENA_WIDTH
        arena_floor_y = SCREEN_HEIGHT - TILE_SIZE * 2
        
        # Create platform
        for x in range(arena_start_x, arena_start_x + BOSS_ARENA_WIDTH, TILE_SIZE):
            self.add_block(Block(x, arena_floor_y, "stone"))
        
        # Add containment walls
        for y in range(arena_floor_y, SCREEN_HEIGHT + TILE_SIZE * 5, TILE_SIZE):
            self.add_block(Block(arena_start_x, y, "stone"))
            self.add_block(Block(arena_start_x + BOSS_ARENA_WIDTH - TILE_SIZE, y, "stone"))
        
        # Add ceiling to lock player in during fight
        ceiling_y = arena_floor_y - TILE_SIZE * 4
        for x in range(arena_start_x, arena_start_x + BOSS_ARENA_WIDTH, TILE_SIZE):
            self.add_block(Block(x, ceiling_y, "stone"))
            self.boss_arena_ceiling.append((x, ceiling_y))
        
        # Place flag above boss arena (locked until boss is defeated)
        self.goal_flag = GoalFlag(arena_start_x + BOSS_ARENA_WIDTH//2 - TILE_SIZE, ceiling_y - TILE_SIZE * 2)
        
        # Mark all chunks as generated
        for x in range(0, WORLD_WIDTH, CHUNK_SIZE * TILE_SIZE):
            for y in range(0, SCREEN_HEIGHT * 2, CHUNK_SIZE * TILE_SIZE):
                chunk_x = x // (CHUNK_SIZE * TILE_SIZE)
                chunk_y = y // (CHUNK_SIZE * TILE_SIZE)
                self.generated_chunks.add((chunk_x, chunk_y))
        
        return arena_start_x + BOSS_ARENA_WIDTH//2 - PLAYER_SIZE  # Return boss x position

def draw_hotbar(player):
    hotbar_width = 300
    hotbar_height = 50
    hotbar_x = SCREEN_WIDTH // 2 - hotbar_width // 2
    hotbar_y = SCREEN_HEIGHT - 60
    
    pygame.draw.rect(screen, (50, 50, 50, 150), (hotbar_x, hotbar_y, hotbar_width, hotbar_height))
    pygame.draw.rect(screen, (0, 0, 0), (hotbar_x, hotbar_y, hotbar_width, hotbar_height), 2)
    
    slot_width = 40
    for i, block_type in enumerate(["grass", "dirt", "stone", "wood", "iron"]):
        slot_x = hotbar_x + 10 + i * (slot_width + 10)
        
        if player.selected_block == block_type:
            pygame.draw.rect(screen, (255, 255, 255), (slot_x - 2, hotbar_y - 2, slot_width + 4, hotbar_height + 4), 2)
        
        if block_type == "grass":
            pygame.draw.rect(screen, GRASS_GREEN, (slot_x, hotbar_y + 5, slot_width - 4, slot_width - 4))
        elif block_type == "dirt":
            pygame.draw.rect(screen, DIRT_BROWN, (slot_x, hotbar_y + 5, slot_width - 4, slot_width - 4))
        elif block_type == "stone":
            pygame.draw.rect(screen, STONE_GRAY, (slot_x, hotbar_y + 5, slot_width - 4, slot_width - 4))
        elif block_type == "wood":
            pygame.draw.rect(screen, (101, 67, 33), (slot_x, hotbar_y + 5, slot_width - 4, slot_width - 4))
        elif block_type == "iron":
            pygame.draw.rect(screen, (150, 150, 150), (slot_x, hotbar_y + 5, slot_width - 4, slot_width - 4))
        
        font = pygame.font.SysFont(None, 20)
        text = font.render(str(player.inventory[block_type]), True, (255, 255, 255))
        screen.blit(text, (slot_x + slot_width - 15, hotbar_y + slot_width - 5))
    
    # Draw coin count
    coin_x = hotbar_x + hotbar_width - 50
    pygame.draw.circle(screen, COIN_YELLOW, (coin_x, hotbar_y + hotbar_height//2), 15)
    coin_text = font.render(str(player.inventory["coin"]), True, (255, 255, 255))
    screen.blit(coin_text, (coin_x + 20, hotbar_y + hotbar_height//2 - 8))

def draw_health_bar(player):
    bar_width = 200
    bar_height = 25
    bar_x = 20
    bar_y = 20
    
    # Background
    pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
    
    # Health level
    health_width = int((player.health / player.max_health) * bar_width)
    health_color = (int(255 * (1 - player.health/player.max_health)), 
                   int(255 * (player.health/player.max_health)), 
                   0)
    pygame.draw.rect(screen, health_color, (bar_x, bar_y, health_width, bar_height))
    
    # Border
    pygame.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_width, bar_height), 2)
    
    # Text
    font = pygame.font.SysFont(None, 24)
    text = font.render(f"Health: {player.health}/{player.max_health}", True, (255, 255, 255))
    screen.blit(text, (bar_x + 10, bar_y))

def draw_pause_menu():
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))
    
    font_large = pygame.font.SysFont(None, 72)
    font_small = pygame.font.SysFont(None, 36)
    
    title = font_large.render("PAUSED", True, (255, 255, 255))
    screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, SCREEN_HEIGHT//3))
    
    resume_text = font_small.render("Press ESC to Resume", True, (255, 255, 255))
    screen.blit(resume_text, (SCREEN_WIDTH//2 - resume_text.get_width()//2, SCREEN_HEIGHT//2))
    
    quit_text = font_small.render("Press Q to Quit", True, (255, 255, 255))
    screen.blit(quit_text, (SCREEN_WIDTH//2 - quit_text.get_width()//2, SCREEN_HEIGHT//2 + 50))

def draw_level_complete(level):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))
    
    font_large = pygame.font.SysFont(None, 72)
    font_medium = pygame.font.SysFont(None, 48)
    font_small = pygame.font.SysFont(None, 36)
    
    title = font_large.render("LEVEL COMPLETE!", True, (255, 255, 0))
    screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, SCREEN_HEIGHT//3))
    
    level_text = font_medium.render(f"Level {level} Finished", True, (255, 255, 255))
    screen.blit(level_text, (SCREEN_WIDTH//2 - level_text.get_width()//2, SCREEN_HEIGHT//2))
    
    if level < 2:
        next_text = font_small.render("Press SPACE to continue to next level", True, (255, 255, 255))
        screen.blit(next_text, (SCREEN_WIDTH//2 - next_text.get_width()//2, SCREEN_HEIGHT//2 + 100))
    else:
        congrats_text = font_medium.render("Congratulations! You beat the game!", True, (255, 255, 0))
        screen.blit(congrats_text, (SCREEN_WIDTH//2 - congrats_text.get_width()//2, SCREEN_HEIGHT//2 + 100))
    
    quit_text = font_small.render("Press Q to Quit", True, (255, 255, 255))
    screen.blit(quit_text, (SCREEN_WIDTH//2 - quit_text.get_width()//2, SCREEN_HEIGHT - 100))

def draw_parallax_background(offset, time_of_day, level):
    # Calculate sky color based on time of day
    day_factor = min(1, max(0, math.sin(time_of_day)))
    sky_color = (
        int(SKY_BLUE[0] * day_factor + SKY_NIGHT[0] * (1 - day_factor)),
        int(SKY_BLUE[1] * day_factor + SKY_NIGHT[1] * (1 - day_factor)),
        int(SKY_BLUE[2] * day_factor + SKY_NIGHT[2] * (1 - day_factor))
    )
    screen.fill(sky_color)
    
    # Draw stars at night
    if day_factor < 0.5:
        star_alpha = int(255 * (1 - day_factor * 2))
        for _ in range(100):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT//2)
            size = random.randint(1, 3)
            brightness = random.randint(150, 255)
            pygame.draw.circle(screen, (brightness, brightness, brightness, star_alpha), 
                             (x, y), size)
    
    # Draw mountains in the background (parallax effect)
    mountain_offset = offset[0] * 0.2
    for i in range(5):
        height = 150 + i * 30
        base_y = SCREEN_HEIGHT - height + 100
        darkness = 50 + i * 30
        
        # Different mountain colors for different levels
        if level == 1:
            color = (darkness, darkness, darkness)
        else:  # Level 2
            color = (darkness, darkness//2, darkness//2)  # Reddish mountains
            
        pygame.draw.polygon(screen, color, [
            (0 - mountain_offset % (SCREEN_WIDTH * 2) - SCREEN_WIDTH * 2 * i, base_y),
            (SCREEN_WIDTH//2 - mountain_offset % (SCREEN_WIDTH * 2) - SCREEN_WIDTH * 2 * i, base_y - height),
            (SCREEN_WIDTH - mountain_offset % (SCREEN_WIDTH * 2) - SCREEN_WIDTH * 2 * i, base_y)
        ])

def show_level_intro(level):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))
    
    font_large = pygame.font.SysFont(None, 72)
    font_small = pygame.font.SysFont(None, 36)
    
    title = font_large.render(f"LEVEL {level}", True, (255, 255, 255))
    screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, SCREEN_HEIGHT//3))
    
    if level == 1:
        desc = font_small.render("Reach the flag at the end of the level", True, (255, 255, 255))
    else:
        desc = font_small.render("Defeat the boss and reach the flag", True, (255, 255, 255))
    
    screen.blit(desc, (SCREEN_WIDTH//2 - desc.get_width()//2, SCREEN_HEIGHT//2))
    
    start_text = font_small.render("Press SPACE to start", True, (255, 255, 255))
    screen.blit(start_text, (SCREEN_WIDTH//2 - start_text.get_width()//2, SCREEN_HEIGHT//2 + 100))
    
    pygame.display.flip()
    
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    waiting = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return False
        clock.tick(60)
    
    return True

# Global game objects
world = World()
particle_system = ParticleSystem()
projectiles = []
items = []
enemies = []
camera_offset = [0, 0]

def main():
    global items, projectiles, enemies, camera_offset
    
    current_level = 1
    player = Player(100, SCREEN_HEIGHT // 2)
    time_of_day = 0  # For day/night cycle
    game_time = 0
    paused = False
    level_complete = False
    boss_spawned = False
    
    # Show level intro
    if not show_level_intro(current_level):
        return
    
    # Generate level 1
    world.generate_level_1()
    
    running = True
    placing_block = False
    breaking_block = False
    break_progress = 0
    current_breaking_block = None
    
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = not paused
                if paused or level_complete:
                    if event.key == pygame.K_q:
                        running = False
                    if event.key == pygame.K_SPACE and level_complete and current_level < 2:
                        current_level += 1
                        level_complete = False
                        player = Player(100, SCREEN_HEIGHT // 2)
                        enemies = []
                        projectiles = []
                        items = []
                        camera_offset = [0, 0]
                        boss_x = world.generate_level_2()
                        enemies.append(Enemy(boss_x, SCREEN_HEIGHT - TILE_SIZE * 5, "boss"))
                        if not show_level_intro(current_level):
                            return
                    continue
                
                if event.key == pygame.K_SPACE:
                    player.jump()
                if event.key == pygame.K_1:
                    player.selected_block = "grass"
                elif event.key == pygame.K_2:
                    player.selected_block = "dirt"
                elif event.key == pygame.K_3:
                    player.selected_block = "stone"
                elif event.key == pygame.K_4:
                    player.selected_block = "wood"
                elif event.key == pygame.K_5:
                    player.selected_block = "iron"
                elif event.key == pygame.K_f:
                    player.attack(enemies)
                elif event.key == pygame.K_y and current_level == 1 and world.goal_flag and (
                    player.x < world.goal_flag.x + world.goal_flag.width and
                    player.x + player.width > world.goal_flag.x and
                    player.y < world.goal_flag.y + world.goal_flag.height and
                    player.y + player.height > world.goal_flag.y
                ):
                    level_complete = True
                    if level_complete_sound: level_complete_sound.play()
            
            if event.type == pygame.MOUSEBUTTONDOWN and not paused and not level_complete:
                if event.button == 1:  # Left click
                    breaking_block = True
                elif event.button == 3:  # Right click
                    placing_block = True
            
            if event.type == pygame.MOUSEBUTTONUP and not paused and not level_complete:
                if event.button == 1:
                    breaking_block = False
                    break_progress = 0
                    current_breaking_block = None
                elif event.button == 3:
                    placing_block = False
        
        if paused:
            draw_pause_menu()
            pygame.display.flip()
            clock.tick(60)
            continue
        
        if level_complete:
            draw_level_complete(current_level)
            pygame.display.flip()
            clock.tick(60)
            continue
        
        # Update game time and day/night cycle
        game_time += 1
        time_of_day = game_time / 600  # 10 second day/night cycle
        
        # Player movement
        keys = pygame.key.get_pressed()
        player.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            player.vel_x = -3
            player.facing = "left"
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            player.vel_x = 3
            player.facing = "right"
        
        # Check if player reached the goal flag
        if world.goal_flag and (player.x < world.goal_flag.x + world.goal_flag.width and
                                player.x + player.width > world.goal_flag.x and
                                player.y < world.goal_flag.y + world.goal_flag.height and
                                player.y + player.height > world.goal_flag.y):
            if current_level == 1:
                # Draw prompt to press 'y' when at flag in level 1
                font = pygame.font.SysFont(None, 36)
                prompt_text = font.render("Press Y to advance to level 2", True, (255, 255, 255))
                screen.blit(prompt_text, (SCREEN_WIDTH//2 - prompt_text.get_width()//2, 50))
            elif current_level == 2 and not any(e.type == "boss" for e in enemies):
                level_complete = True
                if level_complete_sound: level_complete_sound.play()
        
        # Spawn enemies periodically (except in boss arena)
        spawn_allowed = (
            current_level == 1 or
            (current_level == 2 and player.x < WORLD_WIDTH - BOSS_ARENA_WIDTH - SCREEN_WIDTH)
        )

        if game_time % 300 == 0 and len(enemies) < (5 if current_level == 1 else 8) and spawn_allowed:
            enemy_types = ["zombie", "slime"] if current_level == 1 else ["zombie", "slime", "ice_golem"]
            enemy_type = random.choice(enemy_types)
            x = player.x + random.choice([-1, 1]) * random.randint(200, 400)
            y = SCREEN_HEIGHT - TILE_SIZE * 5
            enemies.append(Enemy(x, y, enemy_type))

        
        # Block breaking
        if breaking_block:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            world_x = mouse_x + camera_offset[0]
            world_y = mouse_y + camera_offset[1]
            
            clicked_block = None
            for block in world.get_nearby_blocks(world_x, world_y):
                if (world_x >= block.x and world_x <= block.x + TILE_SIZE and
                    world_y >= block.y and world_y <= block.y + TILE_SIZE):
                    clicked_block = block
                    break
            
            if clicked_block and clicked_block.type != "bedrock":
                if current_breaking_block != clicked_block:
                    current_breaking_block = clicked_block
                    break_progress = 0
                
                break_progress += 0.5
                if break_progress >= clicked_block.health:
                    world.remove_block(clicked_block)
                    player.inventory[clicked_block.type] += 1
                    if break_sound: break_sound.play()
                    particle_system.add_particles(
                        clicked_block.x + TILE_SIZE//2,
                        clicked_block.y + TILE_SIZE//2,
                        GRASS_GREEN if clicked_block.type == "grass" else
                        DIRT_BROWN if clicked_block.type == "dirt" else
                        STONE_GRAY if clicked_block.type == "stone" else
                        (101, 67, 33) if clicked_block.type == "wood" else
                        (150, 150, 150),
                        15
                    )
                    breaking_block = False
                    break_progress = 0
                    current_breaking_block = None
        
        # Block placing
        if placing_block and player.inventory[player.selected_block] > 0:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            world_x = mouse_x + camera_offset[0]
            world_y = mouse_y + camera_offset[1]
            
            grid_x = (world_x // TILE_SIZE) * TILE_SIZE
            grid_y = (world_y // TILE_SIZE) * TILE_SIZE
            
            valid_position = True
            
            # Check if position overlaps with player
            if (grid_x < player.x + player.width and
                grid_x + TILE_SIZE > player.x and
                grid_y < player.y + player.height and
                grid_y + TILE_SIZE > player.y):
                valid_position = False
            
            # Check if position already has a block
            for block in world.get_nearby_blocks(grid_x, grid_y):
                if block.x == grid_x and block.y == grid_y:
                    valid_position = False
                    break
            
            if valid_position:
                new_block = Block(grid_x, grid_y, player.selected_block)
                world.add_block(new_block)
                player.inventory[player.selected_block] -= 1
                if place_sound: place_sound.play()
                placing_block = False
        
        # Update entities
        player.update(world.blocks, enemies, items)
        
        for enemy in enemies[:]:
            enemy.update(world.blocks, player)
            if enemy.health <= 0:
                if enemy.type == "boss" and boss_death_sound:
                    boss_death_sound.play()
                enemies.remove(enemy)
                # Drop items when enemy dies
                for _ in range(random.randint(1, 3)):
                    items.append(Item(
                        enemy.x + random.randint(-10, 10),
                        enemy.y + random.randint(-10, 10),
                        "coin" if random.random() < 0.7 else "iron"
                    ))
        
        for item in items:
            item.update()
        
        # Update goal flag
        if world.goal_flag:
            world.goal_flag.update()
        
        # Update projectiles
        for projectile in projectiles[:]:
            if not projectile.update():
                projectiles.remove(projectile)
            else:
                # Check projectile collisions with player
                player_rect = pygame.Rect(player.x, player.y, player.width, player.height)
                proj_rect = pygame.Rect(
                    projectile.x - projectile.size,
                    projectile.y - projectile.size,
                    projectile.size * 2,
                    projectile.size * 2
                )
                if proj_rect.colliderect(player_rect) and player.invincible <= 0:
                    player.health -= 10 if projectile.type != "boss_fire" else 20
                    player.invincible = 30
                    if hurt_sound: hurt_sound.play()
                    if projectile in projectiles:
                        projectiles.remove(projectile)
                    particle_system.add_particles(
                        projectile.x, projectile.y,
                        (200, 200, 255) if projectile.type == "ice" else (255, 200, 200),
                        10
                    )
                
                # Check projectile collisions with enemies
                for enemy in enemies[:]:
                    enemy_rect = pygame.Rect(enemy.x, enemy.y, enemy.width, enemy.height)
                    if proj_rect.colliderect(enemy_rect):
                        enemy.health -= 10
                        if projectile in projectiles:
                            projectiles.remove(projectile)
                        particle_system.add_particles(
                            projectile.x, projectile.y,
                            (200, 200, 255) if projectile.type == "ice" else (255, 200, 200),
                            10
                        )
                        if enemy.health <= 0:
                            enemies.remove(enemy)
                            # Drop items when enemy dies
                            for _ in range(random.randint(1, 3)):
                                items.append(Item(
                                    enemy.x + random.randint(-10, 10),
                                    enemy.y + random.randint(-10, 10),
                                    "coin" if random.random() < 0.7 else "iron"
                                ))
                        break
        
        particle_system.update()
        
        # Update camera
        target_x = player.x - SCREEN_WIDTH // 2 + player.width // 2
        target_y = player.y - SCREEN_HEIGHT // 2 + player.height // 2
        
        camera_offset[0] += (target_x - camera_offset[0]) * 0.1
        camera_offset[1] += (target_y - camera_offset[1]) * 0.1
        
        camera_offset[0] = max(0, min(camera_offset[0], WORLD_WIDTH - SCREEN_WIDTH))
        camera_offset[1] = max(0, min(camera_offset[1], SCREEN_HEIGHT * 2 - SCREEN_HEIGHT))
        
        # Drawing
        draw_parallax_background(camera_offset, time_of_day, current_level)
        
        # Draw blocks
        nearby_blocks = world.get_nearby_blocks(camera_offset[0], camera_offset[1])
        for block in nearby_blocks:
            if (block.x + TILE_SIZE > camera_offset[0] and
                block.x < camera_offset[0] + SCREEN_WIDTH and
                block.y + TILE_SIZE > camera_offset[1] and
                block.y < camera_offset[1] + SCREEN_HEIGHT):
                block.draw(camera_offset, time_of_day)
        
        # Draw goal flag
        if world.goal_flag and (world.goal_flag.x + world.goal_flag.width > camera_offset[0] and
                                world.goal_flag.x < camera_offset[0] + SCREEN_WIDTH and
                                world.goal_flag.y + world.goal_flag.height > camera_offset[1] and
                                world.goal_flag.y < camera_offset[1] + SCREEN_HEIGHT):
            world.goal_flag.draw(camera_offset)
        
        # Draw items
        for item in items:
            if (item.x + item.width > camera_offset[0] and
                item.x < camera_offset[0] + SCREEN_WIDTH and
                item.y + item.height > camera_offset[1] and
                item.y < camera_offset[1] + SCREEN_HEIGHT):
                item.draw(camera_offset)
        
        # Draw enemies
        for enemy in enemies:
            if (enemy.x + enemy.width > camera_offset[0] and
                enemy.x < camera_offset[0] + SCREEN_WIDTH and
                enemy.y + enemy.height > camera_offset[1] and
                enemy.y < camera_offset[1] + SCREEN_HEIGHT):
                enemy.draw(camera_offset)
        
        # Draw projectiles
        for projectile in projectiles:
            if (projectile.x + projectile.size > camera_offset[0] and
                projectile.x - projectile.size < camera_offset[0] + SCREEN_WIDTH and
                projectile.y + projectile.size > camera_offset[1] and
                projectile.y - projectile.size < camera_offset[1] + SCREEN_HEIGHT):
                projectile.draw(camera_offset)
        
        # Draw particles
        particle_system.draw(camera_offset)
        
        # Draw block breaking progress
        if breaking_block and current_breaking_block:
            progress_width = int((break_progress / current_breaking_block.health) * TILE_SIZE)
            pygame.draw.rect(screen, (255, 255, 255, 100), 
                            (current_breaking_block.x - camera_offset[0], 
                             current_breaking_block.y - camera_offset[1] - 10, 
                             progress_width, 5), 0)
        
        player.draw(camera_offset)
        draw_hotbar(player)
        draw_health_bar(player)
        
        # Draw level indicator
        font = pygame.font.SysFont(None, 36)
        level_text = font.render(f"Level: {current_level}", True, (255, 255, 255))
        screen.blit(level_text, (SCREEN_WIDTH - level_text.get_width() - 20, 20))
        
        # Draw boss warning in level 2
        if current_level == 2 and any(e.type == "boss" for e in enemies):
            warning_text = font.render("BOSS AHEAD!", True, (255, 0, 0))
            screen.blit(warning_text, (SCREEN_WIDTH//2 - warning_text.get_width()//2, 50))
        
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
