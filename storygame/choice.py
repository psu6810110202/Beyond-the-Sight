# storygame/choice.py
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle, Line
from settings import TILE_SIZE, GAME_FONT
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
        # ขยับไปข้างหน้า 1 บล็อค (TILE_SIZE)
        game.warning_dismissed = True # ปิดการแจ้งเตือนถาวรสำหรับครั้งนี้
        game.refresh_darkness() # ล้างหมอกสีดำทิ้งทันที
        px, py = game.player.logic_pos
        if game.player.direction == 'up': py += TILE_SIZE
        elif game.player.direction == 'down': py -= TILE_SIZE
        elif game.player.direction == 'left': px -= TILE_SIZE
        elif game.player.direction == 'right': px += TILE_SIZE
        
        # อัปเดตตำแหน่ง (โดยไม่เช็คการชนกำแพงตามคำสั่งให้ขยับทันที)
        game.player.logic_pos = [px, py]
        game.player.target_pos = [px, py]
        game.player.sync_graphics_pos() # อัปเดตตำแหน่งภาพทันที
        game.player.update_frame()

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
            
            # อัปเดตเควส
            game.quest_manager.update_quest_progress("doll_parts", 1)
            
            # เช็คว่าครบหรือยัง
            quest = game.quest_manager.active_quests.get("doll_parts")
            if quest and quest.current_count >= quest.target_count:
                game.show_vn_dialogue("Little girl", "I have enough parts now. I should return to The Sad Soul.")
                # อัปเดตชื่อเควสให้รู้ว่าต้องกลับไปส่ง
                quest.name = "Return to The Sad Soul"
                game.quest_manager.update_quest_list_ui()
            else:
                # เปลี่ยนจาก VN Dialogue เป็นการประกาศกลางจอ
                game.show_item_discovery("FOUND A PIECE OF THE DOLL")
            
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
