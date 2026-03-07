# storygame/world.py
from kivy.graphics import Color, Rectangle
from characters.npc import NPC
from characters.enemy import Enemy
from characters.reaper import REAPER_START_POS
from items.star import Star
from assets.Tiles.map_loader import KivyTiledMap
from kivy.core.image import Image as CoreImage
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
        """สร้างพิกัดและชนิดของศัตรู โดยลำดับความสำคัญคือ: ข้อมูลจากเซฟ > ข้อมูลเริ่มต้น"""
        # 1. ตรวจสอบว่ามีข้อมูลศัตรูจากเซฟล่าสุดหรือไม่
        has_saved_enemies = False
        initial_data = getattr(self.game, 'initial_data', None)
        
        if initial_data and 'enemies_data' in initial_data:
            # ใช้พิกัดล่าสุดที่เซฟไว้
            for edata in initial_data['enemies_data']:
                eid = edata['id']
                x, y = edata['pos']
                etype = edata['type']
                
                if eid not in self.game.destroyed_enemies:
                    enemy = Enemy(self.game.sorting_layer, x, y, enemy_id=eid, enemy_type=etype)
                    self.game.enemies.append(enemy)
            
            has_saved_enemies = True
            # ล้างข้อมูลออกหลังจากโหลดครั้งแรกเพื่อไม่ให้ค้างตอนเปลี่ยนแมพ/รีเซ็ตโลก
            initial_data.pop('enemies_data', None)

        # 2. หากไม่มีข้อมูลในเซฟ (เริ่มวันใหม่หรือเปลี่ยนแมพ) ให้ใช้ตรรกะปกติ
        if not has_saved_enemies:
            for i, data in enumerate(ENEMY_SPAWN_DATA):
                x, y = data['pos']
                etype = data.get('type', 1)
                
                if i in self.game.destroyed_enemies:
                    continue
                    
                enemy = Enemy(self.game.sorting_layer, x, y, enemy_id=i, enemy_type=etype)
                self.game.enemies.append(enemy)

            # หากพิกัดอันตรายถูกเปิดแล้ว ให้สุ่มศัตรูเพิ่มเติม
            if self.game.warning_dismissed and self.game.game_map.filename == MAP_FILE:
                self.spawn_random_enemies()

    def spawn_random_enemies(self):
        """สุ่มเกิดศัตรูเพิ่มเติมเมื่อผู้เล่นเปิดพิกัดอันตรายแล้ว (ใช้ Seed คงที่เพื่อให้กลับมายังจุดเดิมเมื่อโหลดเซฟ)"""
        r = random.Random(999)
        
        count = 25 # ศัตรูแบบสุ่ม เยอะๆ
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
            
            # บังคับให้เกิดเฉพาะใน 'เขตอันตราย'
            if self.game.current_day == 1:
                # สำหรับ Day 1: ห้ามเกิดในเขตปลอดภัย (ล่างขวา)
                if x >= 656 and y <= 464:
                    continue
            else:
                # สำหรับ Day 2+: ห้ามเกิดในเขตปลอดภัย (แถบล่างทั้งหมด)
                if y <= 464:
                    continue
            
            # ไม่ให้ศัตรูชิดกันเกินไปตามคำขอ
            too_close = False
            for cx, cy in candidates_xy:
                if ((x - cx)**2 + (y - cy)**2)**0.5 < 180:
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

    def create_house_marks(self):
        """สร้างรูปสัญลักษณ์ต่างๆ บนผนังหน้าบ้านใน Day 2"""
        self.game.house_marks_group.clear()
        if self.game.current_day != 2:
            return
            
        from kivy.core.image import Image as CoreImage
        from settings import HOUSE_MARKS_MAPPING
        
        self.game.house_marks_group.add(Color(1, 1, 1, 1))
        
        for (x, y), file_path in HOUSE_MARKS_MAPPING.items():
            try:
                tex = CoreImage(file_path).texture
                if tex:
                    tex.min_filter = 'nearest'
                    tex.mag_filter = 'nearest'
                    
                    # แปะไว้บนผนัง (y + 16) ขนาด 16px
                    rect = Rectangle(texture=tex, pos=(x, y + 16), size=(16, 16))
                    self.game.house_marks_group.add(rect)
            except Exception as e:
                print(f"Error loading mark texture {file_path}: {e}")

    def restore_delivered_marks(self):
        """วาดจดหมายที่วางไปแล้วใหม่ให้เชื่อมโยงกับ Graphic Layer (Persist visuals)"""
        self.game.delivered_marks_group.clear()
        if self.game.current_day != 2:
            return
            
        from kivy.core.image import Image as CoreImage
        from kivy.graphics import Rectangle, Color
        for entry in self.game.delivered_house_indices:
            if isinstance(entry, dict):
                try:
                    tex = CoreImage(entry["img"]).texture
                    if tex:
                        tex.min_filter = 'nearest'
                        tex.mag_filter = 'nearest'
                        self.game.delivered_marks_group.add(Color(1, 1, 1, 1))
                        self.game.delivered_marks_group.add(Rectangle(texture=tex, pos=entry["pos"], size=(16, 16)))
                except Exception as e:
                    print(f"Error restoring delivered mark: {e}")

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
            
            if self.game.current_day == 1 or self.game.current_day == 3:
                # Day 1: x=656, Day 3: x=480 (Safe area is bottom-right)
                dark_x_start = (656 if self.game.current_day == 1 else 480) - fade_range
                dark_y_start = 464 + fade_range
                
                # ส่วนทึบ
                self.game.darkness_group.add(Color(0, 0, 0, base_alpha))
                # แถบซ้ายทั้งหมด
                self.game.darkness_group.add(Rectangle(pos=(0, 0), size=(dark_x_start, MAP_HEIGHT)))
                # แถบบน (ในส่วนที่เหลือทางขวา)
                self.game.darkness_group.add(Rectangle(pos=(dark_x_start, dark_y_start), size=(MAP_WIDTH - dark_x_start, MAP_HEIGHT - dark_y_start)))
                
                # ส่วนไล่สี (Gradient)
                fade_steps = 40
                step_size = fade_range / fade_steps
                for i in range(fade_steps):
                    alpha = base_alpha * (1 - (i / fade_steps))
                    self.game.darkness_group.add(Color(0, 0, 0, alpha))
                    
                    # วาดแถบแนวตั้ง (จากซ้ายไปขวา)
                    self.game.darkness_group.add(Rectangle(
                        pos=(dark_x_start + (i * step_size), 0), 
                        size=(step_size + 0.5, dark_y_start)
                    ))
                    
                    # วาดแถบแนวนอน (จากบนลงล่าง) 
                    self.game.darkness_group.add(Rectangle(
                        pos=(dark_x_start, dark_y_start - ((i+1) * step_size)), 
                        size=(MAP_WIDTH - dark_x_start, step_size + 0.5)
                    ))
            else:
                # สำหรับ Day 2, 4, 5: ใช้เฉพาะพิกัด Y (Safe area คือแถบล่างทั้งหมด)
                dark_y_start = 464 + fade_range
                
                # ส่วนทึบ (ครอบคลุมพื้นที่ด้านบนทั้งหมด)
                self.game.darkness_group.add(Color(0, 0, 0, base_alpha))
                self.game.darkness_group.add(Rectangle(pos=(0, dark_y_start), size=(MAP_WIDTH, MAP_HEIGHT - dark_y_start)))
                
                # ส่วนไล่สี (Gradient) แนวนอนอย่างเดียว
                fade_steps = 40
                step_size = fade_range / fade_steps
                for i in range(fade_steps):
                    alpha = base_alpha * (1 - (i / fade_steps))
                    self.game.darkness_group.add(Color(0, 0, 0, alpha))
                    
                    self.game.darkness_group.add(Rectangle(
                        pos=(0, dark_y_start - ((i+1) * step_size)), 
                        size=(MAP_WIDTH, step_size + 0.5)
                    ))

            self.game.darkness_group.add(Color(1, 1, 1, 1))

    def recreate_world(self):
        """รีโหลดโลกทั้งหมดเมื่อข้ามวัน"""
        # 1. Cleanup
        for e_list in [self.game.npcs, self.game.enemies, self.game.stars]:
            for entity in e_list:
                if hasattr(entity, 'destroy'):
                    entity.destroy()
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
        self.game.player.is_in_home = False
        self.game.player.stamina = MAX_STAMINA
        self.game.player.is_moving = False
        self.game.player.state = 'idle'
        self.game.player.sync_graphics_pos()
        self.game.player.update_animation_speed()
        self.game.player.update_frame()
        
        # 4. Respawn Entities
        if hasattr(self.game, 'reaper') and self.game.reaper:
            # Re-add to sorting layer if it was cleared during cutscene transition
            if self.game.reaper.group not in self.game.sorting_layer.children:
                self.game.sorting_layer.add(self.game.reaper.group)
                
            self.game.reaper.x, self.game.reaper.y = REAPER_START_POS
            self.game.reaper.logic_pos = list(REAPER_START_POS)
            self.game.reaper.target_pos = list(REAPER_START_POS)
            self.game.reaper.update_visual_positions()
            
        self.create_npcs()
        self.create_enemies()
        self.create_stars()
        self.create_house_marks()
        
        self.restore_delivered_marks()
        self.refresh_darkness()
        self.game.request_keyboard_back()
