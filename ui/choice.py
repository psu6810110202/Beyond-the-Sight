# storygame/choice.py
import random
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle, Line
from data.settings import GAME_FONT, TILE_SIZE, STAR_ITEM_MAPPING, PLAYER_PORTRAIT_IMG, PLAYER_S_PORTRAIT_IMG
from data.chat import DIALOGUE_CONFIG

def handle_choice_selection(game, choice):
    """จัดการเมื่อผู้เล่นเลือก Choice"""
    print(f"Selected choice: {choice}")
    
    # ปิดกล่องข้อความ
    game.close_dialogue()
    
    if choice == "Ok":
        # หันกลับไปทางตรงข้าม
        opposite = {'up': 'down', 'down': 'up', 'left': 'right', 'right': 'left'}
        game.player.direction = opposite.get(game.player.direction, game.player.direction)
        game.player.update_frame()
        
    elif choice == "I'll go":
        # ขยับไปข้างหน้า 1 บล็อก โดยใช้ระบบการเดินของ Player ทอดๆ มา
        game.warning_dismissed = True
        game.refresh_darkness()
        game.world_manager.spawn_random_enemies()
        
        dir_map = {'up': (0, TILE_SIZE), 'down': (0, -TILE_SIZE), 'left': (-TILE_SIZE, 0), 'right': (TILE_SIZE, 0)}
        dx, dy = dir_map.get(game.player.direction, (0, 0))
        game.player.start_move(dx, dy)

    elif choice == "SEARCH":
        # พิเศษสำหรับแมพใต้ดิน (Soul Fragments)
        if hasattr(game, 'current_star_target') and game.current_star_target:
            star_pos = (game.current_star_target.x, game.current_star_target.y)
            if not hasattr(game, 'collected_stars'):
                game.collected_stars = []
            game.collected_stars.append(star_pos)

            # ลบดาวทิ้ง
            if game.current_star_target in game.stars:
                game.stars.remove(game.current_star_target)
            game.current_star_target.destroy()

            # เช็คผลลัพธ์จาก Mapping
            from data.settings import UNDERGROUND_FRAGMENT_MAPPING
            mapping = getattr(game, 'underground_fragments_mapping', UNDERGROUND_FRAGMENT_MAPPING)
            result = mapping.get(star_pos, {"type": "ghost"})

            rtype = result.get("type", "ghost")
            img   = result.get("img", None)
            portrait = result.get("portrait", PLAYER_PORTRAIT_IMG)

            if rtype == "true":
                # ของจริง — โชว์ item discovery + เพิ่มเควส
                game.quest_manager.update_quest_progress("soul_fragments", 1)
                if img:
                    game.show_item_discovery("SOUL FRAGMENT", img)
                    game.pending_post_discovery_dialogue = {
                        "name": "Little girl",
                        "text": "There's something here... a fragment of a soul.",
                        "portrait": portrait
                    }
                else:
                    game.show_vn_dialogue("Little girl", "There's something here... a fragment of a soul.", portrait=portrait)

            elif rtype == "fake":
                # ของปลอม — โชว์ item discovery แต่ set fail
                game.quest_item_fail = True
                game.quest_manager.update_quest_progress("soul_fragments", 1)
                if img:
                    game.show_item_discovery("SOUL FRAGMENT", img)
                    game.pending_post_discovery_dialogue = {
                        "name": "Little girl",
                        "text": "This doesn't feel right... something is wrong.",
                        "portrait": portrait
                    }
                else:
                    game.show_vn_dialogue("Little girl", "This doesn't feel right...", portrait=portrait)

            else:
                # ผีหลอก — knockback ทันที แล้วค่อยสปาวน์ผีหลังจาก 0.4 วิ
                from entities.characters.enemy import Enemy
                from kivy.clock import Clock

                # 1. knockback ผู้เล่นทันที (3 บล็อก step-by-step)
                back_map = {
                    'up':    (0, -TILE_SIZE),
                    'down':  (0,  TILE_SIZE),
                    'left':  ( TILE_SIZE, 0),
                    'right': (-TILE_SIZE, 0),
                }
                dx, dy = back_map.get(game.player.direction, (0, 0))
                px, py = game.player.logic_pos
                for _ in range(3):
                    nx, ny = px + dx, py + dy
                    if game.game_map.is_solid(nx, ny):
                        break
                    px, py = nx, ny
                game.player.logic_pos = [px, py]
                game.player.target_pos = [px, py]
                game.player.sync_graphics_pos()

                # 2. เล่นเสียงทันที
                if hasattr(game, 'shock_sound') and game.shock_sound:
                    game.shock_sound.play()

                # 3. หาตำแหน่งสปาวน์ผีที่ไม่ทับ hitbox
                gx, gy = star_pos
                offsets = [(0, 0), (16, 0), (-16, 0), (0, 16), (0, -16), (32, 0), (-32, 0)]
                spawn_x, spawn_y = gx, gy
                for ox, oy in offsets:
                    cx, cy = gx + ox, gy + oy
                    if not game.game_map.is_solid(cx, cy):
                        spawn_x, spawn_y = cx, cy
                        break

                # 4. delay 0.4 วิ แล้วค่อย spawn ผี (ผู้เล่นกระเด็นห่างแล้ว)
                ghost_type = random.choice([1, 2, 3])
                def spawn_ghost(dt, gtype=ghost_type, sx=spawn_x, sy=spawn_y):
                    ghost = Enemy(game.sorting_layer, sx, sy, enemy_id=9999, enemy_type=gtype)
                    # ใช้ stun() แทน is_chasing=False เพราะ update() จะ override is_chasing ทุก frame
                    ghost.stun(3.0)
                    game.enemies.append(ghost)

                    def release_ghost(dt2, g=ghost):
                        # stun หมดเองตามเวลา แต่ยกเลิก stun color เผื่อ
                        if g in game.enemies:
                            g.is_stunned = False
                            g.color_instr.rgb = (1, 1, 1)
                    Clock.schedule_once(release_ghost, 5.0)

                Clock.schedule_once(spawn_ghost, 0.4)


            game.current_star_target = None


    elif choice == "PICK UP":
        # ตรวจสอบว่ามีดาวที่กำลัง interact อยู่หรือไม่
        if hasattr(game, 'current_star_target') and game.current_star_target:
            # เก็บพิกัดดาวที่ถูกเก็บไปแล้ว
            star_pos = (game.current_star_target.x, game.current_star_target.y)
            if not hasattr(game, 'collected_stars'):
                game.collected_stars = []
            game.collected_stars.append(star_pos)
            
            # ลบดาวทิ้ง
            if game.current_star_target in game.stars:
                game.stars.remove(game.current_star_target)
            game.current_star_target.destroy()
            
            # ตรวจสอบผลลัพธ์จากข้อมูลส่วนกลางใน settings.py
            if game.current_day == 1:
                curr_map = STAR_ITEM_MAPPING
            elif game.current_day == 4:
                from data.settings import DAY4_KEY_MAPPING
                curr_map = DAY4_KEY_MAPPING
            else:
                curr_map = LETTER_ITEM_MAPPING
            
            if star_pos in curr_map:
                if not curr_map[star_pos].get("fail", False):
                    # ความสำเร็จของวันจะไปนับรวมทีเดียวตอนจบเควสใน story.py
                    pass
                else:
                    game.quest_item_fail = True
            
            if game.current_day == 1:
                game.quest_manager.update_quest_progress("doll_parts", 1)
            elif game.current_day == 2:
                game.letters_held += 1
            elif game.current_day == 4:
                # หยิบอันไหนก็ได้ เควสนับว่าสำรวจแล้วเพื่อให้กลับไปคุยได้
                if star_pos in curr_map:
                    game.quest_manager.update_quest_progress("find_key", 1)

                    # เล่นเสียงหยิบกุญแจ
                    if hasattr(game, 'key_pickup_sound') and game.key_pickup_sound:
                        game.key_pickup_sound.play()

                    # ถ้าเป็นกุญแจจริง (fail=False) ให้ reset fail flag กรณีเคยหยิบผิดมาก่อน
                    if not curr_map[star_pos].get("fail", False):
                        game.quest_item_fail = False
                    # ถ้าเป็นกุญแจหลอก และยังไม่เคยหยิบของจริง ให้ set fail
                    else:
                        game.quest_item_fail = True

                    # อัปเดตชื่อเควสให้รู้ว่าต้องกลับไปส่ง
                    quest = game.quest_manager.active_quests.get("find_key")
                    if quest:
                        quest.name = "Return to The Lady at the Window"
                        game.quest_manager.update_quest_list_ui()

                    # ลบดาวที่เหลือทั้งหมดออกจากแมพทันทีที่หยิบ
                    for remain_star in game.stars[:]:
                        remain_star.destroy()
                    game.stars.clear()

                    # ตั้งค่าแชทที่จะขึ้นต่อหลังจากผู้เล่นกดปิด "Banner ไอเทม"
                    game.pending_post_discovery_dialogue = {
                        "name": "Little girl",
                        "text": "I found a key. I should return it to the lady at the window.",
                        "portrait": PLAYER_PORTRAIT_IMG
                    }
            
            # ใช้ข้อมูลไอเทมและรูปหน้าตัวละครจาก settings.py เพื่อบอกว่าเป็นของจริงหรือปลอม
            found_special = False
            if star_pos in curr_map:
                item_info = curr_map[star_pos]
                found_special = True
                
                # เปลี่ยนมาโชว์แบบ Discovery แทน Chat ตามที่ USER ขอ
                if game.current_day == 1: discovery_text = "FOUND A PIECE"
                elif game.current_day == 2: discovery_text = "FOUND A LETTER"
                elif game.current_day == 4: 
                    # ถ้าเป็นกุญแจจริง (fail=False) ให้โชว์ชื่อไอเทมกุญแจ
                    discovery_text = "KEY" if not item_info.get("fail") else "FOUND SOMETHING"
                else: discovery_text = "FOUND SOMETHING"
                
                game.show_item_discovery(discovery_text, item_info["img"])

            else:
                discovery_text = "FOUND A PIECE" if game.current_day == 1 else "FOUND A LETTER"
                game.show_item_discovery(discovery_text)

            # เช็คว่าครบหรือยัง (Day 1 เท่านั้น Day 2 ใช้ระบบส่งหน้าบ้าน)
            if game.current_day == 1:
                quest = game.quest_manager.active_quests.get("doll_parts")
                if quest and quest.current_count >= quest.target_count:
                    # ถ้าเก็บครบแล้ว ให้ขึ้นข้อความบอกว่าควรกลับไปส่ง
                    if not (star_pos in curr_map and curr_map[star_pos].get("fail")):
                        game.show_vn_dialogue("Little girl", "I have enough parts now. I should return to The Sad Soul.")
                    
                    # อัปเดตชื่อเควสให้รู้ว่าต้องกลับไปส่ง
                    quest.name = "Return to The Sad Soul"
                    game.quest_manager.update_quest_list_ui()

                    # ลบดาวที่เหลือทั้งหมดออกจากแมพเพื่อกันสับสน
                    for remain_star in game.stars[:]:
                        remain_pos = (remain_star.x, remain_star.y)
                        if remain_pos not in game.collected_stars:
                            game.collected_stars.append(remain_pos)
                        remain_star.destroy()
                    game.stars.clear()

            elif game.current_day == 2:
                # แจ้งเตือนเมื่อเก็บจดหมายได้
                if game.letters_held == 1:
                     game.show_vn_dialogue("Little girl", "I should find the houses with blue lanterns to deliver this.")
            
            game.current_star_target = None

    elif choice == "Leave a letter":
        used_letters = []
        for entry in game.delivered_house_indices:
            img = entry.get('img', '')
            if 'circle_v.png' in img: used_letters.append('Circle Note')
            elif 'cross_v.png' in img: used_letters.append('Cross Note')
            elif 'square_v.png' in img: used_letters.append('Square Note')
            
        available_notes = [n for n in ["Circle Note", "Cross Note", "Square Note"] if n not in used_letters]
        
        game.show_vn_dialogue("Little girl", "Which letter should I use?", 
                             choices=["Let me think again"] + available_notes, portrait=None)

    elif choice in ["Circle Note", "Cross Note", "Square Note"]:
        game.pending_letter_type = choice
        img_map = {
            "Circle Note": "assets/Items/note/circle.png",
            "Cross Note":  "assets/Items/note/cross.png",
            "Square Note": "assets/Items/note/square.png"
        }
            
        game.show_vn_dialogue("Little girl", f"Are you sure you want to use the {choice}?", 
                             choices=["Drop it", "Let me think again"], portrait=img_map.get(choice))

    elif choice == "Drop it":
        if game.current_day == 2 and hasattr(game, 'pending_drop_spot') and game.pending_drop_spot:
            spot, spot_index = game.pending_drop_spot
            
            # ตรวจสอบว่าเคยส่งบ้านนี้ไปหรือยัง
            already_done = False
            for entry in game.delivered_house_indices:
                if isinstance(entry, dict) and entry.get("index") == spot_index:
                    already_done = True; break
            
            if game.letters_held > 0 and not already_done:
                from data.settings import HOUSE_MARKS_MAPPING
                # ตรวจสอบความถูกต้องโดยการจับคู่ "ชื่อรูป Mark" กับ "ชื่อ Note" (ไม่ใช้พิกัด)
                mark_path = HOUSE_MARKS_MAPPING.get(tuple(spot))
                if mark_path:
                    # ดึงชื่อจาก path (เช่น assets/mark/circle.png -> circle)
                    mark_filename = mark_path.split('/')[-1].split('.')[0].lower()
                    # ดึงชื่อจากไอเทม (เช่น Circle Note -> circle)
                    note_name = game.pending_letter_type.split(' ')[0].lower()
                    
                    if mark_filename != note_name:
                        game.quest_item_fail = True
                        print(f"DEBUG: Failure! House Mark '{mark_filename}' does not match Note '{note_name}'")
                else:
                    game.quest_item_fail = True # ไม่มี Mark แต่จะวาง = ผิด

                game.letters_held -= 1
                game.quest_manager.update_quest_progress("deliver_letters", 1)
                
                if hasattr(game, 'pickup_sound') and game.pickup_sound:
                    game.pickup_sound.play()
                
                # หาพิกัดวาง (ทางซ้ายของตัวละคร 16px) และรูป _v
                letter_map = {
                    "Circle Note": "assets/Items/note/circle_v.png",
                    "Cross Note":  "assets/Items/note/cross_v.png",
                    "Square Note": "assets/Items/note/square_v.png"
                }
                v_img_path = letter_map.get(game.pending_letter_type, "assets/Items/note/square_v.png")
                
                # ตัวละครหันซ้าย
                game.player.direction = 'left'
                game.player.update_frame()
                
                # คำนวณจุดวาง (ซ้ายตัวละคร)
                drop_x = game.player.logic_pos[0] - 16
                drop_y = game.player.logic_pos[1]
                
                # วาดรูปลงเลเยอร์ delivered_marks_group ทันที
                from kivy.core.image import Image as CoreImage
                from kivy.graphics import Rectangle, Color
                try:
                    tex = CoreImage(v_img_path).texture
                    tex.min_filter = 'nearest'
                    tex.mag_filter = 'nearest'
                    game.delivered_marks_group.add(Color(1, 1, 1, 1))
                    game.delivered_marks_group.add(Rectangle(texture=tex, pos=(drop_x, drop_y), size=(16, 16)))
                except Exception as e:
                    print(f"Error drawing drop mark: {e}")

                # เก็บข้อมูลไว้ใน delivered_house_indices
                mark_data = {
                    "index": spot_index,
                    "pos": (drop_x, drop_y),
                    "img": v_img_path
                }
                game.delivered_house_indices.append(mark_data)

                # เช็คว่าส่งครบหรือยัง
                quest = game.quest_manager.active_quests.get("deliver_letters")
                if quest and quest.current_count >= quest.target_count:
                    game.show_vn_dialogue("Little girl", "That's the last house. I should head back to The Postman.")
                    quest.name = "Return to The Postman"
                    game.quest_manager.update_quest_list_ui()
                
                if hasattr(game, 'pending_drop_spot'): del game.pending_drop_spot
                if hasattr(game, 'pending_letter_type'): del game.pending_letter_type
                
                game.close_dialogue()
                return
    elif choice == "Let me think":
        if hasattr(game, 'pending_drop_spot'): del game.pending_drop_spot
        if hasattr(game, 'pending_letter_type'): del game.pending_letter_type
        game.close_dialogue()

    elif choice == "Let me think again":
        # เปลี่ยนกลับให้ปิดบทสนทนาและยกเลิกเลยตามคำขอ
        if hasattr(game, 'pending_drop_spot'): del game.pending_drop_spot
        if hasattr(game, 'pending_letter_type'): del game.pending_letter_type
        game.close_dialogue()

    elif choice in ["RED", "BLUE", "YELLOW"]:
        game.set_candle_color(choice)

def draw_choice_buttons(game, choices):
    """วาดปุ่มทางเลือก (UI Logic)"""
    root = game.dialogue_root if game.dialogue_root else game
    
    # ลบของเก่าออกก่อนป้องกันการซ้อน
    clear_choices(game)
    
    game.choice_index = 0
    game.choice_buttons = []
        
    num_choices = len(choices)
    # คำนวณความสูงของ Layout ตามจำนวนตัวเลือก เพื่อให้ปุ่มไม่เตี้ยเกินไปเมื่อมีหลายตัวเลือก
    # (แต่ละปุ่มควรสูงประมาณ 7% ของความสูงจอ)
    dynamic_height = min(0.45, num_choices * 0.075) 
    
    # ใช้ BoxLayout แนวตั้งที่ขนาดขยายตามหน้าจอ (Relative Scaling)
    game.choice_layout = BoxLayout(
        orientation='vertical',
        size_hint=(0.4, dynamic_height), 
        pos_hint={'center_x': 0.5, 'center_y': 0.6}, 
        spacing=10
    )
    
    bg_opacity = DIALOGUE_CONFIG.get("bg_opacity", 0.85)
    
    for i, choice_text in enumerate(choices):
        btn = Button(
            text=choice_text.upper(),
            font_name=GAME_FONT,
            font_size=22,
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            bold=True,
            size_hint=(1, 1)
        )
        
        with btn.canvas.before:
            # พื้นหลังสีเดียวกับ Chat
            btn.bg_color = Color(0, 0, 0, bg_opacity)
            btn.bg_rect = RoundedRectangle(size=btn.size, pos=btn.pos, radius=[5,])
            # เส้นขอบ (ใช้ Line เพื่อให้เป็นแค่เส้นรอบนอก ไม่ใช่สี่เหลี่ยมทึบคะ)
            btn.line_color = Color(1, 1, 1, 0.2)
            btn.line_obj = Line(rounded_rectangle=(btn.x, btn.y, btn.width, btn.height, 5), width=1.5)
            
        def update_btn_graphics(instance, value):
            instance.bg_rect.pos = instance.pos
            instance.bg_rect.size = instance.size
            instance.line_obj.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 5)
            # ปรับขนาดตัวอักษรให้ขยายตามขนาดปุ่ม (ซึ่งขยายตามจอ) โดยไม่มีเพดานกั้น
            instance.font_size = max(14, instance.height * 0.5)
        btn.bind(pos=update_btn_graphics, size=update_btn_graphics)
        
        btn.bind(on_release=lambda x, t=choice_text: game.on_choice_selected(t))
        game.choice_layout.add_widget(btn)
        game.choice_buttons.append(btn)
        
    root.add_widget(game.choice_layout)
    update_choice_visuals(game)

def update_choice_visuals(game):
    """อัปเดตสีปุ่มเมื่อมีการเลื่อนขึ้นลง"""
    if not game.choice_buttons:
        return
        
    bg_opacity = DIALOGUE_CONFIG.get("bg_opacity", 0.85)

    # กรณีเลือกจดหมาย ให้รูปภาพทางขวาเปลี่ยนตามตัวเลือกที่ไฮไลท์อยู่
    if hasattr(game, 'pending_drop_spot') and not hasattr(game, 'pending_letter_type'):
        selected_text = game.choice_buttons[game.choice_index].text
        img_map = {
            "CIRCLE NOTE": "assets/Items/note/circle.png",
            "CROSS NOTE":  "assets/Items/note/cross.png",
            "SQUARE NOTE": "assets/Items/note/square.png"
        }
        if selected_text in img_map:
            if hasattr(game, 'dialogue_manager'):
                game.dialogue_manager.update_right_portrait(img_map[selected_text])
        else:
            if hasattr(game, 'dialogue_manager'):
                game.dialogue_manager.update_right_portrait(None)
    
    for i, btn in enumerate(game.choice_buttons):
        if i == game.choice_index:
            btn.bg_color.rgba = (0, 0, 0, bg_opacity) # พื้นหลังเท่าเดิม
            btn.line_color.rgba = (1, 1, 1, 1)        # ขอบขาวสว่าง (Highlight เฉพาะขอบ)
            btn.line_obj.width = 2.5                  # เส้นขอบหนาขึ้นเพื่อให้ชัดเจน
            btn.color = (1, 1, 1, 1)                  # ตัวอักษรสว่าง
        else:
            btn.bg_color.rgba = (0, 0, 0, bg_opacity)
            btn.line_color.rgba = (1, 1, 1, 0.2)      # ขอบจาง
            btn.line_obj.width = 1.5
            btn.color = (1, 1, 1, 0.5)                # ตัวอักษรสีเทาจาง

def clear_choices(game):
    """ลบวิดเจ็ตทางเลือก"""
    if game.choice_layout:
        if game.choice_layout.parent:
            game.choice_layout.parent.remove_widget(game.choice_layout)
        game.choice_layout = None
    game.choice_buttons = []
    game.choice_index = 0
