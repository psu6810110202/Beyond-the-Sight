# storygame/world.py
from kivy.graphics import Color, Rectangle
from entities.characters.npc import NPC
from entities.characters.enemy import Enemy
from entities.characters.reaper import REAPER_START_POS
from entities.items.star import Star
from assets.Tiles.map_loader import KivyTiledMap
from kivy.core.image import Image as CoreImage
from data.settings import *
import random

class WorldManager:
    def __init__(self, game):
        self.game = game
        self.darkness_base_color = (0, 0, 0, 0.4) # RGBA
        
    def create_reapers(self):
        """จัดการการสร้าง Reaper หลักและ Extra Reapers ตามความก้าวหน้าของวัน"""
        from entities.characters.reaper import Reaper, REAPER_START_POS
        
        # 1. จัดการ Reaper หลัก (เฉพาะในแมพหลัก beyond.tmj)
        map_file = getattr(self.game.game_map, 'filename', '')
        is_village = 'beyond.tmj' in map_file.lower()
        print(f"DEBUG: create_reapers on map: {map_file}, is_village: {is_village}")

        if not hasattr(self.game, 'reaper') or self.game.reaper is None:
            self.game.reaper = Reaper(self.game.sorting_layer)
        
        if is_village:
            # เพิ่มคืนเข้า Sorting Layer หากถูกล้าง
            if self.game.reaper.group not in self.game.sorting_layer.children:
                self.game.sorting_layer.add(self.game.reaper.group)
            
            # ตั้งค่าเริ่มต้นสำหรับหมู่บ้าน
            self.game.reaper.x, self.game.reaper.y = REAPER_START_POS
            self.game.reaper.logic_pos = list(REAPER_START_POS)
            self.game.reaper.target_pos = list(REAPER_START_POS)
            self.game.reaper.alpha = 1.0
            self.game.reaper.is_fading = False
            self.game.reaper.fading_done = False
            if hasattr(self.game.reaper, 'sprite_color'): self.game.reaper.sprite_color.a = 1.0
            if hasattr(self.game.reaper, 'aura_color'): self.game.reaper.aura_color.a = 0.1
        else:
            # ย้ายไปไกลๆ และซ่อนหากไม่ใช่แมพหมู่บ้าน
            self.game.reaper.x, self.game.reaper.y = -5000, -5000
            self.game.reaper.logic_pos = [-5000, -5000]
            self.game.reaper.is_fading = False
            self.game.reaper.fading_done = False
            if hasattr(self.game.reaper, 'sprite_color'): self.game.reaper.sprite_color.a = 0.0
            if hasattr(self.game.reaper, 'aura_color'): self.game.reaper.aura_color.a = 0.0
            
        self.game.reaper.update_visual_positions()

        # 2. จัดการ Extra Reapers (ล้างของเก่าก่อน)
        if not hasattr(self.game, 'extra_reapers'):
            self.game.extra_reapers = []
        
        for er in self.game.extra_reapers:
            er.destroy() # เรียกใช้ method ใหม่ที่สร้างไว้
        self.game.extra_reapers = []

        # 3. สร้าง Extra Reapers ตามวัน (เฉพาะในแมพหลัก beyond.tmj)
        if is_village:
            day = getattr(self.game, 'current_day', 1)
            
            # User Request: Day 1 เป็นหลัก (0 Extra), 2-4 เพิ่มแบบสะสม
            # Day 2: เพิ่ม 1 ตัว (ใกล้ NPC1)
            if day >= 2:
                er1 = Reaper(self.game.sorting_layer, x=896, y=416)
                er1.direction = 'down'
                er1.update_frame()
                er1.update_visual_positions()
                self.game.extra_reapers.append(er1)
                
            # Day 3: เพิ่มตัวที่ 2 (ใกล้ NPC2)
            if day >= 3:
                er2 = Reaper(self.game.sorting_layer, x=304, y=288)
                er2.direction = 'right'
                er2.update_frame()
                er2.update_visual_positions()
                self.game.extra_reapers.append(er2)
                
            # Day 4: เพิ่มตัวที่ 3 (ตรอกลึก NPC3)
            if day >= 4:
                er3 = Reaper(self.game.sorting_layer, x=480, y=1312)
                er3.direction = 'down'
                er3.update_frame()
                er3.update_visual_positions()
                self.game.extra_reapers.append(er3)

            # หมายเหตุ: สำหรับ Day 5 จะไม่มีการเพิ่ม Extra ในหมู่บ้าน (เพราะไปอยู่ใต้ดิน)
                
        elif 'underground.tmj' in map_file.lower():
            # สร้าง Reapers ใน Underground ตามที่ระบุ
            from data.settings import REAPER_SPAWN_DATA_UNDERGROUND
            for pos in REAPER_SPAWN_DATA_UNDERGROUND:
                er = Reaper(self.game.sorting_layer, x=pos[0], y=pos[1])
                er.direction = 'down'
                er.update_frame()
                er.update_visual_positions()
                self.game.extra_reapers.append(er)

    def create_npcs(self):
        # ตรรกะการแสดง NPC ตามวัน (เฉพาะในแมพหลัก beyond.tmj หรือตามเงื่อนไขเนื้อเรื่อง)
        map_file = getattr(self.game.game_map, 'filename', '')
        
        if 'underground.tmj' in map_file.lower():
            # สร้าง The Soul (800, 320) ใน Underground
            the_soul = NPC(self.game.sorting_layer, 800, 320, 'assets/characters/NPC/NPC5.png')
            the_soul.npc_index = 5 # หรือ index ที่เหมาะสม
            the_soul.name = "The Soul"
            the_soul.direction = 'up'
            the_soul.update_frame()
            self.game.npcs.append(the_soul)
            return

        if 'beyond.tmj' not in map_file.lower():
            return

        for i in range(min(NPC_COUNT, len(NPC_IMAGE_LIST))):
            if not self.game.story_manager.is_npc_visible(i):
                continue
                
            img_path = NPC_IMAGE_LIST[i]
            npc = NPC(self.game.sorting_layer, image_path=img_path)
            self.game.npcs.append(npc)

    def create_enemies(self):
        """สร้างพิกัดและชนิดของศัตรู (เฉพาะในแมพหลัก beyond.tmj)"""
        map_file = getattr(self.game.game_map, 'filename', '')
        if 'beyond.tmj' not in map_file.lower():
            return

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

        if not has_saved_enemies:
            # 2. หากไม่มีข้อมูลในเซฟ (เริ่มวันใหม่) ให้ใช้ตรรกะปกติ
            enemy_list = []
            
            # รวมรายการศัตรูสะสมตามวัน
            current_day = self.game.current_day
            for d in range(1, current_day + 1):
                enemies_for_day = ENEMY_SPAWN_DATA.get(d, [])
                for idx, data in enumerate(enemies_for_day):
                    # สร้าง ID แบบคงที่ (Static ID) เพื่อไม่ให้ตำแหน่งพิกัดใน Destroyed ตีกันเมื่อเพิ่มศัตรูใหม่
                    # เช่น ศัตรู Day 1 ตัวที่ 0 จะมี ID 0, Day 2 ตัวที่ 0 จะมี ID 4 (ถ้า Day 1 มี 4 ตัว)
                    # หมายเหตุ: เรายังคงใช้เลขเรียงเพื่อความ Simple ในขั้นนี้ แต่ทำให้เห็นภาพรวมง่ายขึ้น
                    x, y = data['pos']
                    etype = data.get('type', 1)
                    
                    # คำนวณ Index รวม (เลียนแบบ enumerate(enemy_list) เดิมเพื่อไม่ให้เซฟเก่าพัง)
                    global_idx = 0
                    for prev_d in range(1, d):
                        global_idx += len(ENEMY_SPAWN_DATA.get(prev_d, []))
                    global_idx += idx
                    
                    if global_idx in self.game.destroyed_enemies:
                        continue
                        
                    enemy = Enemy(self.game.sorting_layer, x, y, enemy_id=global_idx, enemy_type=etype)
                    self.game.enemies.append(enemy)
            
            print(f"DEBUG: Created {len(self.game.enemies)} static enemies for Day {current_day} (No save data used)")

            # หากพิกัดอันตรายถูกเปิดแล้ว ให้สุ่มศัตรูเพิ่มเติม
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
        
        candidate_positions = []
        for day, spawns in ENEMY_SPAWN_DATA.items():
            if day <= self.game.current_day:
                candidate_positions.extend(spawns)
        candidates_xy = [(d['pos'][0], d['pos'][1]) for d in candidate_positions]
        
        while spawned < count and attempts < 2000:
            attempts += 1
            # 1. สุ่มโอกาสเกิดตามโซนต่างๆ ก่อน
            if r.random() < 0.5:
                # โซนบนขวา: x > 656 และ y > 464 (แก้ Y ให้เป็นด้านบน)
                x = r.randint(656, MAP_WIDTH - 64)
                y = r.randint(464, MAP_HEIGHT - 64)
            else:
                # โซนซ้าย: x < 656 หรือ โซนบน (y > 464)
                if r.random() < 0.7:  # 70% โอกาสไปซ้าย
                    x = r.randint(32, 656)
                    y = r.randint(32, MAP_HEIGHT - 64)
                else:  # 30% โอกาสกระจายไปด้านบนๆ ทั้งหมด
                    x = r.randint(32, MAP_WIDTH - 64)
                    y = r.randint(464, MAP_HEIGHT - 64)
            
            # บังคับให้เกิดเฉพาะใน 'เขตอันตราย'
            if self.game.current_day == 1:
                # สำหรับ Day 1: ห้ามเกิดในเขตปลอดภัย (ล่างขวา)
                if x >= 656 and y <= 464:
                    continue
            elif self.game.current_day == 3:
                # สำหรับ Day 3: "ครึ่งล่างกับซ้ายบนปลอดภัย" -> อันตรายแค่ "ขวาบน" (x >= 880 และ y >= 464)
                # ดังนั้นถ้าไม่ได้อยู่ในเขต ขวาบน ให้ข้ามการเกิดศัตรู
                if not (x >= 880 and y >= 464):
                    continue
            else:
                # สำหรับ Day 2, 4, 5: ห้ามเกิดในเขตปลอดภัย (แถบล่างทั้งหมด)
                if y <= 464:
                    continue
            
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
        """สร้างดาวตามพิกัดที่กำหนด (Day 1 และ Day 4)"""
        # ล้างของเดิมก่อนป้องกันการสร้างซ้อน
        for s in self.game.stars[:]:
            s.destroy()
        self.game.stars.clear()

        if self.game.current_day == 1:
            # ถ้าเควสจบไปแล้วไม่ต้องสร้างอีก
            quest = self.game.quest_manager.active_quests.get("doll_parts")
            if quest and not quest.is_active:
                return

            locations = STAR_SPAWN_LOCATIONS
            # 3 ดวงแรกเป็นของจริง ดวงที่เหลือเป็นของหลอก (Day 1 Logic)
            for i, (x, y) in enumerate(locations):
                if (x, y) in self.game.collected_stars: continue
                is_true = (i < 3)
                star = Star(self.game.sorting_layer, x, y, is_true=is_true)
                self.game.stars.append(star)
        elif self.game.current_day == 4:
            # ถ้าเควสจบไปแล้วไม่ต้องสร้างอีก
            quest = self.game.quest_manager.active_quests.get("find_key")
            if quest and not quest.is_active:
                return

            from data.settings import DAY4_STAR_LOCATIONS
            locations = DAY4_STAR_LOCATIONS
            for (x, y) in locations:
                if (x, y) in self.game.collected_stars: continue
                # สำหรับ Day 4, ดาวไหนที่เป็นกุญแจจริงจะถูกเช็คที่ interaction
                star = Star(self.game.sorting_layer, x, y, is_true=True) # ให้เก็บได้ทุกลูก
                self.game.stars.append(star)
        elif 'underground.tmj' in getattr(self.game.game_map, 'filename', '').lower():
            # สำหรับแมพใต้ดิน: ถ้ามีเควสมั้ย
            quest = self.game.quest_manager.active_quests.get("soul_fragments")
            if quest and not quest.is_active:
                return
            # สำหรับแมพใต้ดิน: ระบบเดียวกับ Day 1/4 (สุ่ม 3 จุดจริง, 5 จุดผีหลอก)
            layers = self.game.game_map.map_data.get('layers', [])
            objects_layer = next((l for l in layers if l.get('name') == "ของ"), None)
            if objects_layer:
                # รวบรวมตำแหน่งทั้งหมดที่มี "ของ"
                all_positions = []
                for obj in objects_layer.get('objects', []):
                    ox, oy = obj.get('x', 0), obj.get('y', 0)
                    obj_y_render = self.game.game_map.height * 16 - oy
                    all_positions.append((ox, obj_y_render))
                
                # ถ้ายังไม่มีการทำ mapping (กันพิกัดเปลี่ยนตอนโหลด)
                if not hasattr(self.game, 'underground_fragments_mapping'):
                    import random
                    r = random.Random(777)
                    
                    self.game.underground_fragments_mapping = {}
                    
                    # 1. กำหนดตำแหน่งจริง 3 จุด (กระจายกัน) จาก settings
                    from data.settings import UNDERGROUND_TRUE_POSITIONS
                    true_positions = UNDERGROUND_TRUE_POSITIONS
                    available_spots = [s for s in all_positions if s not in true_positions]
                    for pos in true_positions:
                        self.game.underground_fragments_mapping[pos] = {"type": "true"}
                    
                    # 2. สุ่มตำแหน่งอื่นๆ ที่เหลือ (ไม่ทับจุดจริง)
                    remaining_pos = [p for p in all_positions if p not in true_positions]
                    r.shuffle(remaining_pos)
                    
                    # เลือก 3 จุดเป็นของปลอม (ไม่เจออะไร)
                    for i in range(min(3, len(remaining_pos))):
                        self.game.underground_fragments_mapping[remaining_pos[i]] = {"type": "fake"}
                    
                    # เลือกอีก 3 จุดเป็นผี (Ghost Scare)
                    for i in range(3, min(6, len(remaining_pos))):
                        self.game.underground_fragments_mapping[remaining_pos[i]] = {"type": "ghost"}

                # สร้างดาวเฉพาะจุดที่มีความสำคัญ (ใน mapping)
                for pos, data in self.game.underground_fragments_mapping.items():
                    if pos in self.game.collected_stars: continue
                    
                    # สร้างดาว ( Sparks)
                    star = Star(self.game.sorting_layer, pos[0], pos[1], is_true=(data["type"] == "true"))
                    self.game.stars.append(star)

    def create_candles(self):
        """สร้างเทียนที่พิกัดต่างๆ สำหรับเควส Day 3"""
        from entities.items.candle import Candle
        from data.settings import CANDLE_SPAWN_LOCATIONS
        
        # ล้างของเก่าป้องกันการสร้างซ้อน
        if hasattr(self.game, 'candles'):
            for c in self.game.candles[:]:
                if hasattr(c, 'destroy'): c.destroy()
        self.game.candles = []
            
        initial_data = getattr(self.game, 'initial_data', None)
        lit_data = {}
        if initial_data and 'lit_candle_positions' in initial_data:
            # สร้าง dict ของพิกัด -> สี เพื่อให้เช็คได้เร็ว
            for ldata in initial_data['lit_candle_positions']:
                pos_tuple = tuple(ldata['pos'])
                lit_data[pos_tuple] = ldata['color']

        for x, y in CANDLE_SPAWN_LOCATIONS:
            # เช็คว่ามีเทียนที่พิกัดนี้แลิวหรือชัง (กันการสร้างซ้ำ)
            exists = False
            for c in self.game.candles:
                if c.logic_pos == [x, y]:
                    exists = True
                    break
            if not exists:
                candle = Candle(self.game.sorting_layer, x, y)
                self.game.candles.append(candle)
                
                # ฟื้นฟูสถานะการจุดถ้ามีในเซฟ
                if (x, y) in lit_data:
                    candle.set_color(lit_data[(x, y)])

    def create_house_marks(self):
        """สร้างรูปสัญลักษณ์ต่างๆ บนผนังหน้าบ้านใน Day 2"""
        self.game.house_marks_group.clear()
        if self.game.current_day != 2:
            return
            
        from kivy.core.image import Image as CoreImage
        from data.settings import HOUSE_MARKS_MAPPING
        
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
        
        # ปิดหมอกเมื่อกดยอมรับไปแล้วในวันอื่น หรือเปลี่ยนไปแมพในบ้าน
        if self.game.warning_dismissed or self.game.game_map.filename != MAP_FILE:
            return
            
        r, g, b, base_alpha = self.darkness_base_color
        fade_range = 160
        
        if self.game.current_day == 1:
            # Day 1: x=656 (Safe area is bottom-right)
            dark_x_start = 656 - fade_range
            dark_y_start = 464 + fade_range
            
            # ส่วนทึบ
            self.game.darkness_group.add(Color(r, g, b, base_alpha))
            # แถบซ้ายทั้งหมด
            self.game.darkness_group.add(Rectangle(pos=(0, 0), size=(dark_x_start, MAP_HEIGHT)))
            # แถบบน (ในส่วนที่เหลือทางขวา)
            self.game.darkness_group.add(Rectangle(pos=(dark_x_start, dark_y_start), size=(MAP_WIDTH - dark_x_start, MAP_HEIGHT - dark_y_start)))
            
            # ส่วนไล่สี (Gradient)
            fade_steps = 40
            step_size = fade_range / fade_steps
            for i in range(fade_steps):
                alpha = base_alpha * (1 - (i / fade_steps))
                self.game.darkness_group.add(Color(r, g, b, alpha))
                
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
        elif self.game.current_day == 3:
            # Day 3: หมอกอยู่เฉพาะ ขวาบน (x >= 880 และ y >= 464)
            # ครึ่งล่าง (y < 464) และ ซ้ายบน (x < 880) ปลอดภัย
            dark_x_start = 880 + fade_range
            dark_y_start = 464 + fade_range
            
            # ส่วนทึบ (ขวาบน ทึบสนิท)
            self.game.darkness_group.add(Color(r, g, b, base_alpha))
            self.game.darkness_group.add(Rectangle(
                pos=(dark_x_start, dark_y_start), 
                size=(MAP_WIDTH - dark_x_start, MAP_HEIGHT - dark_y_start)
            ))
            
            # ส่วนไล่สี (Gradient) - จางไปเข้ม
            fade_steps = 40
            step_size = fade_range / fade_steps
            for i in range(fade_steps):
                alpha = base_alpha * (i / fade_steps)
                self.game.darkness_group.add(Color(r, g, b, alpha))
                
                # เส้นแนวตั้ง (ไล่จาก 880 ไปทางขวาเฉพาะส่วนบน)
                self.game.darkness_group.add(Rectangle(
                    pos=(880 + (i * step_size), 464), 
                    size=(step_size + 0.5, MAP_HEIGHT - 464)
                ))
                
                # เส้นแนวนอน (ไล่จาก 464 ขึ้นไปข้างบนเฉพาะส่วนขวา)
                self.game.darkness_group.add(Rectangle(
                    pos=(880, 464 + (i * step_size)), 
                    size=(MAP_WIDTH - 880, step_size + 0.5)
                ))
        elif self.game.current_day == 2:
            # สำหรับ Day 2: ใช้เฉพาะพิกัด Y (Safe area คือแถบล่างทั้งหมด)
            dark_y_start = 464 + fade_range
            
            # ส่วนทึบ (ครอบคลุมพื้นที่ด้านบนทั้งหมด)
            self.game.darkness_group.add(Color(r, g, b, base_alpha))
            self.game.darkness_group.add(Rectangle(pos=(0, dark_y_start), size=(MAP_WIDTH, MAP_HEIGHT - dark_y_start)))
            
            # ส่วนไล่สี (Gradient) แนวนอนอย่างเดียว
            fade_steps = 40
            step_size = fade_range / fade_steps
            for i in range(fade_steps):
                alpha = base_alpha * (1 - (i / fade_steps))
                self.game.darkness_group.add(Color(r, g, b, alpha))
                
                self.game.darkness_group.add(Rectangle(
                    pos=(0, dark_y_start - ((i+1) * step_size)), 
                    size=(MAP_WIDTH, step_size + 0.5)
                ))

        self.game.darkness_group.add(Color(1, 1, 1, 1))

    def update_darkness_color(self, r, g, b, a):
        """อัปเดตสีของหมอก/ความมืด"""
        self.darkness_base_color = (r, g, b, a)
        self.refresh_darkness()

    def recreate_world(self):
        """รีโหลดโลกทั้งหมดเมื่อข้ามวัน"""
        # 1. Cleanup
        for e_list in [self.game.npcs, self.game.enemies, self.game.stars]:
            for entity in e_list:
                if hasattr(entity, 'destroy'):
                    entity.destroy()
        self.game.npcs, self.game.enemies, self.game.stars = [], [], []
        
        # 1.1 Remove blue overlay if any
        if hasattr(self.game, 'blue_overlay') and self.game.blue_overlay:
            if self.game.blue_overlay.parent:
                self.game.blue_overlay.parent.remove_widget(self.game.blue_overlay)
            self.game.blue_overlay = None
        
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
        
        self.create_reapers()
        self.create_npcs()
        self.create_enemies()
        self.create_stars()
        self.create_house_marks()
        
        self.restore_delivered_marks()
        self.refresh_darkness()
        self.game.request_keyboard_back()
