# storygame/choice.py
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle, Line
from settings import GAME_FONT, TILE_SIZE, STAR_ITEM_MAPPING
from storygame.chat import DIALOGUE_CONFIG

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
        
        dir_map = {'up': (0, TILE_SIZE), 'down': (0, -TILE_SIZE), 'left': (-TILE_SIZE, 0), 'right': (TILE_SIZE, 0)}
        dx, dy = dir_map.get(game.player.direction, (0, 0))
        game.player.start_move(dx, dy)

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
            if star_pos in STAR_ITEM_MAPPING:
                if not STAR_ITEM_MAPPING[star_pos].get("fail", False):
                    game.quest_success_count += 1
                else:
                    game.quest_item_fail = True
            
            game.quest_manager.update_quest_progress("doll_parts", 1)
            
            # ใช้ข้อมูลไอเทมและรูปหน้าตัวละครจาก settings.py เพื่อบอกว่าเป็นของจริงหรือปลอม
            found_special = False
            if star_pos in STAR_ITEM_MAPPING:
                item_info = STAR_ITEM_MAPPING[star_pos]
                found_special = True
                
                # เปลี่ยนมาโชว์แบบ Discovery แทน Chat ตามที่ USER ขอ
                # ใช้ข้อความที่มีคำว่า FOUND ตามคำขอ แต่ไม่บอกชนิดไอเทม
                game.show_item_discovery("FOUND A PIECE", item_info["img"])

            else:
                game.show_item_discovery("FOUND A PIECE OF THE DOLL")

            # เช็คว่าครบหรือยัง
            quest = game.quest_manager.active_quests.get("doll_parts")
            if quest and quest.current_count >= quest.target_count:
                # ถ้าเก็บครบแล้ว ให้ขึ้นข้อความบอกว่าควรกลับไปส่ง (อันนี้ยังใช้ Chat เพื่อให้รู้ว่าเป็นคนพูด)
                # แต่ถ้า USER อยากให้เป็น Discovery ทั้งหมด ก็สามารถเปลี่ยนได้
                if not (star_pos in STAR_ITEM_MAPPING and STAR_ITEM_MAPPING[star_pos].get("fail")):
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
            
            game.current_star_target = None

    elif choice == "LEAVE IT":
        game.current_star_target = None

def draw_choice_buttons(game, choices):
    """วาดปุ่มทางเลือก (UI Logic)"""
    root = game.dialogue_root if game.dialogue_root else game
    
    # ลบของเก่าออกก่อนป้องกันการซ้อน
    clear_choices(game)
    
    game.choice_index = 0
    game.choice_buttons = []
        
    # ใช้ BoxLayout แนวตั้งที่ขนาดขยายตามหน้าจอ (Relative Scaling)
    game.choice_layout = BoxLayout(
        orientation='vertical',
        size_hint=(0.5, 0.25), # กว้าง 50% สูง 25% ของหน้าจอ
        pos_hint={'center_x': 0.5, 'center_y': 0.6}, 
        spacing=15
    )
    
    bg_opacity = DIALOGUE_CONFIG.get("bg_opacity", 0.85)
    
    for i, choice_text in enumerate(choices):
        btn = Button(
            text=choice_text.upper(),
            font_name=GAME_FONT,
            font_size=28,
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
            # ปรับขนาดตัวอักษรตามความสูงของปุ่ม (Responsive Font)
            instance.font_size = instance.height * 0.35
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
