# storygame/world.py
from kivy.graphics import Color, Rectangle
from characters.npc import NPC
from characters.enemy import Enemy
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
