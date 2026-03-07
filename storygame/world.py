# storygame/world.py
from kivy.graphics import Color, Rectangle
from characters.npc import NPC
from characters.enemy import Enemy
from characters.reaper import REAPER_START_POS
from items.star import Star
from assets.Tiles.map_loader import KivyTiledMap
from settings import *
import random

class WorldManager:
    def __init__(self, game):
        self.game = game
        
    def create_npcs(self):
        """สร้างพิกัดและรูปภาพจากข้อมูลเริ่มต้นใน settings.py"""
        for i in range(min(NPC_COUNT, len(NPC_IMAGE_LIST))):
            # ตรรกะการแสดง NPC ตามวัน (ดึงมาจาก Story Manager)
            if not self.game.story_manager.is_npc_visible(i):
                continue
                
            img_path = NPC_IMAGE_LIST[i]
            npc = NPC(self.game.sorting_layer, image_path=img_path)
            self.game.npcs.append(npc)

    def create_enemies(self):
        """สร้างพิกัดและชนิดของศัตรูตามที่กำหนดใน settings.py"""
        for i, data in enumerate(ENEMY_SPAWN_DATA):
            x, y = data['pos']
            etype = data.get('type', 1)
            
            # ถ้าศัตรูตัวนี้ถูกกำจัดไปแล้วในเซฟนี้ ไม่ต้องสร้างใหม่
            if i in self.game.destroyed_enemies:
                continue
                
            enemy = Enemy(self.game.sorting_layer, x, y, enemy_id=i, enemy_type=etype)
            self.game.enemies.append(enemy)

        # หากพิกัดอันตรายถูกเปิดแล้ว ให้สุ่มศัตรูเพิ่มเติม (จะถูกเรียกตอนโหลดเซฟด้วย)
        if self.game.warning_dismissed and self.game.game_map.filename == MAP_FILE:
            self.spawn_random_enemies()

    def spawn_random_enemies(self):
        """สุ่มเกิดศัตรูเพิ่มเติมเมื่อผู้เล่นเปิดพิกัดอันตรายแล้ว (ใช้ Seed คงที่เพื่อให้กลับมายังจุดเดิมเมื่อโหลดเซฟ)"""
        r = random.Random(999)
        
        count = 60 # ศัตรูแบบสุ่ม เพิ่มความท้าทายในโซนอันตราย
        base_id = 100 
        
        spawned = 0
        attempts = 0
        solid_rects = self.game.game_map.solid_rects
        
        candidate_positions = list(ENEMY_SPAWN_DATA)
        candidates_xy = [(d['pos'][0], d['pos'][1]) for d in candidate_positions]
        
        while spawned < count and attempts < 2000:
            attempts += 1
            x = r.randint(32, MAP_WIDTH - 64)
            y = r.randint(32, MAP_HEIGHT - 64)
            
            # บังคับให้เกิดเฉพาะใน 'เขตอันตราย' (ฝั่งซ้ายหรือบน ตามที่เคยกั้นหมอก)
            # แต่ให้กระจายตัวดีขึ้น โดยแบ่งโซนเป็น 2 ส่วน: ซ้ายและบนขวา
            if x >= 656 and y <= 464:
                continue
            
            # เพิ่มโอกาสให้เกิดในโซนบนขวามากขึ้น (50% ของการสุ่ม)
            if r.random() < 0.5:
                # โซนบนขวา: x > 656 และ y < 464
                x = r.randint(656, MAP_WIDTH - 64)
                y = r.randint(32, 464)
            else:
                # โซนซ้าย: x < 656 หรือ y > 464 (แบบเดิม)
                if r.random() < 0.7:  # 70% โอกาสไปซ้าย
                    x = r.randint(32, 656)
                    y = r.randint(32, MAP_HEIGHT - 64)
                else:  # 30% โอกาสไปล่างซ้าย
                    x = r.randint(32, MAP_WIDTH - 64)
                    y = r.randint(464, MAP_HEIGHT - 64)

            
            # ไม่ให้ศัตรูสุ่มเกิดใกล้กับตำแหน่งคงที่เกินไป (เพิ่มระยะห่าง)
            too_close = False
            for cx, cy in candidates_xy:
                if ((x - cx)**2 + (y - cy)**2)**0.5 < 250:  # เพิ่มจาก 180 เป็น 250
                    too_close = True
                    break
            if too_close:
                continue
                
            # ไม่ทับกำแพง
            rect = (x, y, ENEMY_WIDTH, ENEMY_HEIGHT)
            collision = False
            for solid in solid_rects:
                if (rect[0] < solid[0] + solid[2] and rect[0] + rect[2] > solid[0] and
                    rect[1] < solid[1] + solid[3] and rect[1] + rect[3] > solid[1]):
                    collision = True
                    break
            if collision:
                continue
                
            candidates_xy.append((x, y))
            
            enemy_id = base_id + spawned
            etype = r.choice([1, 2, 3])
            
            # ถ้ายังไม่ถูกกำจัดในเซฟ
            if enemy_id not in self.game.destroyed_enemies:
                enemy = Enemy(self.game.sorting_layer, x, y, enemy_id=enemy_id, enemy_type=etype)
                self.game.enemies.append(enemy)
                
            spawned += 1
            
    def create_stars(self):
        """สร้างดาวตามพิกัดที่กำหนดใน Day 1"""
        if self.game.current_day != 1:
            return
            
        for i, (x, y) in enumerate(STAR_SPAWN_LOCATIONS):
            # ตรวจสอบว่าดาวจุดนี้ถูกเก็บไปแล้วหรือยัง
            if [x, y] in self.game.collected_stars or (x, y) in self.game.collected_stars:
                continue
            
            # 3 ดวงแรกเป็นของจริง ดวงที่เหลือเป็นของหลอก (ตาม Logic เดิม)
            is_true = (i < 3)
            star = Star(self.game.sorting_layer, x, y, is_true=is_true)
            self.game.stars.append(star)

    def change_map(self, map_file):
        """โหลดแมพใหม่และรีเซ็ตกราฟิกแมพ (รับประกันความสะอาด 100%)"""
        # 1. ล้าง Containers ทั้งหมด
        self.game.map_before_group.clear()
        self.game.map_after_group.clear()
        
        # 2. สร้าง instance แมพใหม่
        self.game.game_map = KivyTiledMap(map_file)
        
        # อัปเดตขนาด Clipping ตามแมพใหม่
        map_w_px = self.game.game_map.width * TILE_SIZE
        map_h_px = self.game.game_map.height * TILE_SIZE
        self.game.clip_rect.size = (map_w_px, map_h_px)
        
        # 3. วาดกราฟิกแผนที่ใหม่
        self.game.map_before_group.add(Color(1, 1, 1, 1))
        self.game.game_map.draw_ground(self.game.map_before_group)
        self.game.game_map.draw_background(self.game.map_before_group)
        self.game.game_map.draw_foreground(self.game.map_before_group) # ขยะ/ผนัง อยู่ใต้ตัวละคร
        
        self.game.map_after_group.add(Color(1, 1, 1, 1))
        self.game.game_map.draw_roof(self.game.map_after_group)       # หลังคา/เหนือ อยู่บนสุดทับตัวละคร
        
        # 4. รีเฟรชตำแหน่งกล้อง
        self.game.update_camera()
        self.game.game_map.update_chunks(self.game.player.logic_pos[0], self.game.player.logic_pos[1])
        
        # 5. อัปเดตเสียงเดินตามประเภทแมพ
        self.game.player.is_in_home = 'home.tmj' in map_file
        
        print(f"DEBUG: Map swapped to {map_file} (via World Manager)")

    def refresh_darkness(self):
        """วาดหรือล้างหมอกสีดำปิดโซนอันตราย"""
        if not hasattr(self.game, 'darkness_group') or self.game.darkness_group is None:
            return
            
        self.game.darkness_group.clear()
        
        # โชว์หมอกเฉพาะแมพหลักและยังไม่ได้ Dismiss Warning
        if not self.game.warning_dismissed and self.game.game_map.filename == MAP_FILE:
            base_alpha = 0.4
            fade_range = 160
            
            if self.game.current_day == 1:
                dark_x_start = 656 - fade_range
                dark_y_start = 464 + fade_range
                
                # ส่วนทึบ
                self.game.darkness_group.add(Color(0, 0, 0, base_alpha))
                self.game.darkness_group.add(Rectangle(pos=(0, 0), size=(dark_x_start, MAP_HEIGHT)))
                self.game.darkness_group.add(Rectangle(pos=(dark_x_start, dark_y_start), size=(MAP_WIDTH - dark_x_start, MAP_HEIGHT - dark_y_start)))
                
                # ส่วนไล่สี (Gradient) - ปรับให้เนียนขึ้นเป็น 40 ขั้น
                fade_steps = 40
                step_size = fade_range / fade_steps
                for i in range(fade_steps):
                    alpha = base_alpha * (1 - (i / fade_steps))
                    self.game.darkness_group.add(Color(0, 0, 0, alpha))
                    
                    # วาดแถบแนวตั้ง (จากซ้ายไปขวา) - จำกัดความสูงไม่ให้ซ้อนกับแถบแนวนอน
                    self.game.darkness_group.add(Rectangle(
                        pos=(dark_x_start + (i * step_size), 0), 
                        size=(step_size + 0.5, dark_y_start)
                    ))
                    
                    # วาดแถบแนวนอน (จากบนลงล่าง) 
                    self.game.darkness_group.add(Rectangle(
                        pos=(dark_x_start, dark_y_start - ((i+1) * step_size)), 
                        size=(MAP_WIDTH - dark_x_start, step_size + 0.5)
                    ))

            self.game.darkness_group.add(Color(1, 1, 1, 1))

    def recreate_world(self):
        """รีโหลดโลกทั้งหมดเมื่อข้ามวัน"""
        # 1. Cleanup
        for e_list in [self.game.npcs, self.game.enemies, self.game.stars]:
            for entity in e_list:
                if hasattr(entity, 'group') and entity.group in self.game.sorting_layer.children:
                    self.game.sorting_layer.remove(entity.group)
        self.game.npcs, self.game.enemies, self.game.stars = [], [], []
        
        # 2. Map Reset
        if self.game.game_map.filename != MAP_FILE:
            self.change_map(MAP_FILE)
            
        # 3. Player Reset
        start_x = (PLAYER_START_X // TILE_SIZE) * TILE_SIZE
        start_y = (PLAYER_START_Y // TILE_SIZE) * TILE_SIZE
        self.game.player.logic_pos = [start_x, start_y]
        self.game.player.target_pos = [start_x, start_y]
        self.game.player.direction = 'up'
        self.game.player.sync_graphics_pos()
        self.game.player.update_frame()
        
        # 4. Respawn Entities
        if hasattr(self.game, 'reaper') and self.game.reaper:
            self.game.reaper.x, self.game.reaper.y = REAPER_START_POS
            self.game.reaper.logic_pos = list(REAPER_START_POS)
            self.game.reaper.target_pos = list(REAPER_START_POS)
            self.game.reaper.update_visual_positions()
            
        self.create_npcs()
        self.create_enemies()
        self.create_stars()
        self.refresh_darkness()
        self.game.request_keyboard_back()
