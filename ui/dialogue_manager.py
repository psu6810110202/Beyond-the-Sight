from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.clock import Clock
from data.settings import GAME_FONT, WINDOW_HEIGHT
from data.chat import DIALOGUE_CONFIG
from ui.choice import draw_choice_buttons, clear_choices
from kivy.core.image import Image as CoreImage
import math

class DialogueManager:
    def __init__(self, game):
        self.game = game
        self.dialogue_bg = None
        self.dialogue_text = None
        self.name_label = None
        self.portrait_widget = None
        self.left_portrait_widget = None
        self.is_item_notif_active = False
        self.item_notif_widget = None
        self.last_notif_text = ""
        self.last_notif_image = None
        
        self.chat_tri_event = None
        self.item_tri_event = None
        self.portrait_anim_event = None
        self.current_anim_character = None

    def _get_scaled_font_size(self):
        """Scale font size (Single point of control)"""
        # Assuming self.game.height is the relevant height for scaling
        return 70 * (self.game.height / WINDOW_HEIGHT if self.game.height > 0 else 1.0)

    def get_ui_scale(self):
        # WINDOW_HEIGHT is now imported at the top
        return self.game.height / WINDOW_HEIGHT

    def create_pixel_triangle(self, scale, pos_y_ratio=0.1):
        p_px = 5 * scale
        tri_widget = Widget(size_hint=(None, None), size=(5 * p_px, 3 * p_px), 
                           pos_hint={'center_x': 0.5, 'center_y': pos_y_ratio})
        
        with tri_widget.canvas:
            tri_color = Color(1, 1, 1, 1)
            tri_rect1 = Rectangle(size=(5 * p_px, p_px))
            tri_rect2 = Rectangle(size=(3 * p_px, p_px))
            tri_rect3 = Rectangle(size=(1 * p_px, p_px))
            
        def update_tri_pos(instance, value=None):
            cx, cy = instance.center
            y_off = getattr(instance, 'y_offset', 0)
            tri_rect1.pos = (cx - 2.5 * p_px, cy + 0.5 * p_px + y_off)
            tri_rect2.pos = (cx - 1.5 * p_px, cy - 0.5 * p_px + y_off)
            tri_rect3.pos = (cx - 0.5 * p_px, cy - 1.5 * p_px + y_off)
            
        tri_widget.bind(pos=update_tri_pos, size=update_tri_pos)
        tri_widget.update_now = update_tri_pos
        tri_widget.y_offset = 0
        tri_widget.tri_color = tri_color
        return tri_widget

    def animate_pixel_triangle(self, tri_widget):
        def _animate(dt):
            t = Clock.get_time()
            tri_widget.y_offset = math.sin(t * 8) * 5
            tri_widget.tri_color.a = 0.4 + abs(math.sin(t * 5)) * 0.6
            if hasattr(tri_widget, 'update_now'):
                tri_widget.update_now(tri_widget)
        return Clock.schedule_interval(_animate, 0.03)

    def show_vn_dialogue(self, character_name, dialogue, choices=None, portrait=None, left_portrait=None):
        dialogue = str(dialogue) if dialogue is not None else ""  # safety cast
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        cfg = DIALOGUE_CONFIG
        scale = self.get_ui_scale()
        self.game.current_choices = choices if choices else []
        if hasattr(self.game, 'clear_interaction_hints'):
            self.game.clear_interaction_hints()

        self.stop_portrait_animation()
        if self.dialogue_bg:
            if self.dialogue_bg.parent: self.dialogue_bg.parent.remove_widget(self.dialogue_bg)
            self.dialogue_bg = None
        if self.chat_tri_event: Clock.unschedule(self.chat_tri_event); self.chat_tri_event = None

        box_h = cfg["box_height"] * scale
        bg_widget = FloatLayout(size_hint=(1, None), height=box_h, pos_hint={'x': 0, 'y': 0})
        with bg_widget.canvas.before:
            Color(0, 0, 0, 0.8)
            self.bg_rect = Rectangle(size=bg_widget.size, pos=bg_widget.pos)
        def update_bg_rect(instance, value):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size
        bg_widget.bind(size=update_bg_rect, pos=update_bg_rect)
        root.add_widget(bg_widget)
        self.dialogue_bg = bg_widget

        if character_name:
            top_pad = cfg["top_padding"] * scale
            name_h = cfg["name_height"] * scale
            self.name_label = Label(
                text=character_name, font_name=GAME_FONT,
                font_size=cfg["name_font_size"] * scale, color=cfg["name_color"],
                size_hint=(1, None), height=name_h,
                pos_hint={'center_x': 0.5, 'top': 1 - (top_pad / box_h)},
                halign='center', valign='middle'
            )
            self.name_label.bind(size=self.name_label.setter('text_size'))
            bg_widget.add_widget(self.name_label)

        msg_margin = cfg["msg_margin_top"] * scale
        text_top_ratio = ( (cfg["top_padding"] * scale) + (cfg["name_height"] * scale) + msg_margin) / box_h
        self.dialogue_text = Label(
            text=dialogue, font_name=GAME_FONT,
            font_size=cfg["msg_font_size"] * scale, color=cfg["msg_color"],
            size_hint=(1, None), height=box_h * (1 - text_top_ratio) - (10 * scale),
            pos_hint={'center_x': 0.5, 'top': 1 - text_top_ratio},
            halign='center', valign='top'
        )
        def update_msg_text_size(instance, value):
            instance.text_size = (instance.width - (cfg["side_padding"] * 2 * scale), instance.height)
        self.dialogue_text.bind(size=update_msg_text_size)
        bg_widget.add_widget(self.dialogue_text)

        if not choices:
            tri = self.create_pixel_triangle(scale, pos_y_ratio=0.1)
            bg_widget.add_widget(tri)
            self.chat_tri_event = self.animate_pixel_triangle(tri)

        # รายชื่อตัวละครปกติที่มีรูป Portrait ประจำตัว
        portrait_characters = ["Little girl", "Angel", "Devil", "Father", "Mother", "Reaper"]
        
        # ถ้ามีการระบุรูป Portrait มา (เช่น รูปบ้าน หรือรูปไอเทม) หรือเป็นตัวละครที่มีรูปประจำตัว
        if portrait or character_name in portrait_characters:
            from data.settings import PLAYER_PORTRAIT_IMG, ANGEL_PORTRAIT_IMG, DEVIL_PORTRAIT_IMG, FATHER_PORTRAIT_IMG, MOTHER_PORTRAIT_IMG, REAPER_PORTRAIT_IMG
            
            # 1. แสดงรูปตามที่ส่งมาสำรองไว้ก่อน
            p_source = portrait
            
            # 2. ถ้าไม่ได้ส่งรูปมา แต่ชื่ออยู่ในลิสต์ ให้ดึงรูปประจำตัวมาใช้
            if not p_source and character_name in portrait_characters:
                from data.settings import PLAYER_S_PORTRAIT_IMG as PS_IMG
                # พิเศษสำหรับฉากบ้านใน Day 3 ให้ใช้รูปหน้าเศร้าเป็นค่าเริ่มต้นเสมอตามคำขอ
                p_default = PLAYER_PORTRAIT_IMG
                if getattr(self.game, 'current_day', 1) == 3 and getattr(self.game.player, 'is_in_home', False):
                    p_default = PS_IMG

                portrait_map = {
                    "Angel": ANGEL_PORTRAIT_IMG,
                    "Devil": DEVIL_PORTRAIT_IMG,
                    "Father": FATHER_PORTRAIT_IMG,
                    "Mother": MOTHER_PORTRAIT_IMG,
                    "Reaper": REAPER_PORTRAIT_IMG
                }
                p_source = portrait_map.get(character_name, p_default)
            
            # ถ้าสุดท้ายมีรูปให้โชว์ (p_source ไม่เป็น None)
            if p_source:
                # ทุกรูป (ไม่ว่าจะตัวละครหรือไอเทม) ให้ใช้สเกลมาตรฐานเดียวกับ Little girl
                char_scale_mult = 1.0
                if "Items" in p_source or "mark" in p_source or "note" in p_source:
                    char_scale_mult = 0.7 # ปรับให้ใหญ่ขึ้น เพื่อความชัดเจน
            p_size = 280 * scale * char_scale_mult
            
            # ให้ขอบล่างของภาพ (Y) วางอยู่บนขอบบนของกล่องข้อความพอดี (box_h)
            # ไม่ต้องมี y_offset ติดลบ เพื่อไม่ให้จมลงไปในกล่อง
            y_base = box_h
            # วางชิดขวาของจอ
            x_pos = self.game.width - p_size - (20 * scale)

            if not self.portrait_widget:
                self.portrait_widget = Widget(size_hint=(None, None), size=(p_size, p_size))
                with self.portrait_widget.canvas:
                    Color(1, 1, 1, 1)
                    try:
                        tex = CoreImage(p_source).texture
                        tex.mag_filter = 'nearest'
                        tex.min_filter = 'nearest'
                        self.portrait_rect = Rectangle(texture=tex, size=self.portrait_widget.size,
                                                    pos=(x_pos, y_base))
                    except Exception:
                        self.portrait_rect = Rectangle(source=p_source, size=self.portrait_widget.size,
                                                    pos=(x_pos, y_base))
                root.add_widget(self.portrait_widget)
                
                if not hasattr(self, '_portrait_update_bound'):
                    def _p_upd(instance, value):
                        if self.portrait_widget and self.portrait_rect:
                            sc = self.get_ui_scale()
                            cur_box_h = DIALOGUE_CONFIG["box_height"] * sc
                            
                            # ดึงสเกลที่เก็บไว้ในตัวแปรคลาสถ้ามีการเก็บไว้
                            mult = getattr(self.portrait_widget, 'char_scale_mult', 1.0)
                            new_p_size = 280 * sc * mult
                            new_x_pos = self.game.width - new_p_size - (20 * sc)
                            new_y_base = cur_box_h
                            
                            self.portrait_widget.size = (new_p_size, new_p_size)
                            self.portrait_rect.size = self.portrait_widget.size
                            self.portrait_rect.pos = (new_x_pos, new_y_base)
                    self.game.bind(size=_p_upd)
                    self._portrait_update_bound = True
                
                # เก็บค่าสเกลไว้ใน widget เพื่อให้ update bound ใช้ได้
                self.portrait_widget.char_scale_mult = char_scale_mult
            else:
                # ถ้ามีลูปอยู่แล้ว แต่อยากเปลี่ยนรูปหน้า (เช่น สลับจาก n เป็น s หรือสลับตัวละครคุยกัน)
                if hasattr(self, 'portrait_rect'):
                    try:
                        tex = CoreImage(p_source).texture
                        tex.mag_filter = 'nearest'
                        tex.min_filter = 'nearest'
                        self.portrait_rect.texture = tex
                    except Exception:
                        self.portrait_rect.source = p_source
                    self.portrait_widget.char_scale_mult = char_scale_mult
                    
                    # บังคับอัปเดตขนาดและตำแหน่งใหม่ทันทีที่มีการสลับตัวละคร
                    self.portrait_widget.size = (p_size, p_size)
                    self.portrait_rect.size = self.portrait_widget.size
                    self.portrait_rect.pos = (x_pos, y_base)
                    print(f"DEBUG: Updated portrait source to {p_source} with scale {char_scale_mult}")

        # --- Handle Left Portrait ---
        if left_portrait:
            l_char_scale_mult = 1.0
            if "Items" in left_portrait or "mark" in left_portrait or "note" in left_portrait:
                l_char_scale_mult = 0.6
            l_p_size = 280 * scale * l_char_scale_mult
            l_x_pos = 20 * scale
            l_y_base = box_h
            
            if not self.left_portrait_widget:
                self.left_portrait_widget = Widget(size_hint=(None, None), size=(l_p_size, l_p_size))
                with self.left_portrait_widget.canvas:
                    Color(1, 1, 1, 1)
                    try:
                        tex = CoreImage(left_portrait).texture
                        tex.mag_filter = 'nearest'
                        tex.min_filter = 'nearest'
                        self.left_portrait_rect = Rectangle(texture=tex, size=self.left_portrait_widget.size, pos=(l_x_pos, l_y_base))
                    except Exception:
                        self.left_portrait_rect = Rectangle(source=left_portrait, size=self.left_portrait_widget.size, pos=(l_x_pos, l_y_base))
                root.add_widget(self.left_portrait_widget)
                
                if not hasattr(self, '_left_portrait_update_bound'):
                    def _l_p_upd(instance, value):
                        if self.left_portrait_widget and self.left_portrait_rect:
                            sc = self.get_ui_scale()
                            cur_box_h = DIALOGUE_CONFIG["box_height"] * sc
                            mult = getattr(self.left_portrait_widget, 'char_scale_mult', 1.0)
                            new_p_size = 280 * sc * mult
                            new_x_pos = 20 * sc
                            new_y_base = cur_box_h
                            self.left_portrait_widget.size = (new_p_size, new_p_size)
                            self.left_portrait_rect.size = self.left_portrait_widget.size
                            self.left_portrait_rect.pos = (new_x_pos, new_y_base)
                    self.game.bind(size=_l_p_upd)
                    self._left_portrait_update_bound = True
                
                self.left_portrait_widget.char_scale_mult = l_char_scale_mult
            else:
                if hasattr(self, 'left_portrait_rect'):
                    try:
                        tex = CoreImage(left_portrait).texture
                        tex.mag_filter = 'nearest'
                        tex.min_filter = 'nearest'
                        self.left_portrait_rect.texture = tex
                    except Exception:
                        self.left_portrait_rect.source = left_portrait
                    self.left_portrait_rect.pos = (l_x_pos, l_y_base)
                    self.left_portrait_rect.size = (l_p_size, l_p_size)

        if choices:
            draw_choice_buttons(self.game, choices)

        # เริ่มอนิเมชั่นถ้าเป็นตัวละครที่เหมาะสม
        if character_name in ["Father", "Mother"]:
            self.start_portrait_animation(character_name)

        self.game.is_dialogue_active = True
        
        # ตั้งธงรอรับไอเทม ถ้าประโยคที่กำลังจะโชว์ระบุว่ามีการให้ของ
        if ("Here, take this [Blue Stone] with you" in dialogue and not getattr(self.game, 'has_received_blue_stone', False)) or \
           ("Take this lantern. You'll need it to light the candles" in dialogue and not getattr(self.game, 'has_received_lantern', False)):
            self.game.awaiting_item_receipt = True

    def update_left_portrait(self, p_source):
        """อัปเดตหรือซ่อนภาพ Portrait ฝั่งซ้ายกลางคันระหว่างคุย"""
        if not p_source:
            if self.left_portrait_widget:
                self.left_portrait_widget.opacity = 0
            return
            
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        scale = self.get_ui_scale()
        box_h = DIALOGUE_CONFIG["box_height"] * scale
        char_scale_mult = 1.0
        if "Items" in p_source or "mark" in p_source:
            char_scale_mult = 0.6
        p_size = 280 * scale * char_scale_mult
        y_base = box_h
        x_pos = 20 * scale

        if not self.left_portrait_widget:
            self.left_portrait_widget = Widget(size_hint=(None, None), size=(p_size, p_size))
            with self.left_portrait_widget.canvas:
                Color(1, 1, 1, 1)
                try:
                    tex = CoreImage(p_source).texture
                    tex.mag_filter = 'nearest'
                    tex.min_filter = 'nearest'
                    self.left_portrait_rect = Rectangle(texture=tex, size=self.left_portrait_widget.size, pos=(x_pos, y_base))
                except Exception:
                    self.left_portrait_rect = Rectangle(source=p_source, size=self.left_portrait_widget.size, pos=(x_pos, y_base))
            root.add_widget(self.left_portrait_widget)
            
            if not hasattr(self, '_left_portrait_update_bound'):
                def _l_p_upd(instance, value):
                    if self.left_portrait_widget and self.left_portrait_rect:
                        sc = self.get_ui_scale()
                        cur_box_h = DIALOGUE_CONFIG["box_height"] * sc
                        mult = getattr(self.left_portrait_widget, 'char_scale_mult', 1.0)
                        new_p_size = 280 * sc * mult
                        new_x_pos = 20 * sc
                        new_y_base = cur_box_h
                        self.left_portrait_widget.size = (new_p_size, new_p_size)
                        self.left_portrait_rect.size = self.left_portrait_widget.size
                        self.left_portrait_rect.pos = (new_x_pos, new_y_base)
                self.game.bind(size=_l_p_upd)
                self._left_portrait_update_bound = True
        
        self.left_portrait_widget.opacity = 1
        self.left_portrait_widget.char_scale_mult = char_scale_mult
        self.left_portrait_widget.size = (p_size, p_size)
        
        if hasattr(self, 'left_portrait_rect'):
            try:
                tex = CoreImage(p_source).texture
                tex.mag_filter = 'nearest'
                tex.min_filter = 'nearest'
                self.left_portrait_rect.texture = tex
            except Exception:
                self.left_portrait_rect.source = p_source
            self.left_portrait_rect.size = self.left_portrait_widget.size
            self.left_portrait_rect.pos = (x_pos, y_base)

    def update_right_portrait(self, p_source):
        """อัปเดตหรือซ่อนภาพ Portrait ฝั่งขวากลางคันระหว่างคุย"""
        if not p_source:
            if self.portrait_widget:
                self.portrait_widget.opacity = 0
            return
            
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        scale = self.get_ui_scale()
        box_h = DIALOGUE_CONFIG["box_height"] * scale
        char_scale_mult = 1.0
        if "Items" in p_source or "mark" in p_source:
            char_scale_mult = 0.6
        p_size = 280 * scale * char_scale_mult
        y_base = box_h
        x_pos = self.game.width - p_size - (20 * scale)

        if not self.portrait_widget:
            self.portrait_widget = Widget(size_hint=(None, None), size=(p_size, p_size))
            with self.portrait_widget.canvas:
                Color(1, 1, 1, 1)
                try:
                    tex = CoreImage(p_source).texture
                    tex.mag_filter = 'nearest'
                    tex.min_filter = 'nearest'
                    self.portrait_rect = Rectangle(texture=tex, size=self.portrait_widget.size, pos=(x_pos, y_base))
                except Exception:
                    self.portrait_rect = Rectangle(source=p_source, size=self.portrait_widget.size, pos=(x_pos, y_base))
            root.add_widget(self.portrait_widget)
            
            if not hasattr(self, '_portrait_update_bound'):
                def _p_upd(instance, value):
                    if self.portrait_widget and self.portrait_rect:
                        sc = self.get_ui_scale()
                        cur_box_h = DIALOGUE_CONFIG["box_height"] * sc
                        mult = getattr(self.portrait_widget, 'char_scale_mult', 1.0)
                        new_p_size = 280 * sc * mult
                        new_x_pos = self.game.width - new_p_size - (20 * sc)
                        new_y_base = cur_box_h
                        self.portrait_widget.size = (new_p_size, new_p_size)
                        self.portrait_rect.size = self.portrait_widget.size
                        self.portrait_rect.pos = (new_x_pos, new_y_base)
                self.game.bind(size=_p_upd)
                self._portrait_update_bound = True
        
        self.portrait_widget.opacity = 1
        self.portrait_widget.char_scale_mult = char_scale_mult
        self.portrait_widget.size = (p_size, p_size)
        
        if hasattr(self, 'portrait_rect'):
            try:
                tex = CoreImage(p_source).texture
                tex.mag_filter = 'nearest'
                tex.min_filter = 'nearest'
                self.portrait_rect.texture = tex
            except Exception:
                self.portrait_rect.source = p_source
            self.portrait_rect.size = self.portrait_widget.size
            self.portrait_rect.pos = (x_pos, y_base)

    def start_portrait_animation(self, character_name):
        self.stop_portrait_animation()
        self.current_anim_character = character_name
        
        from data.settings import FATHER_PORTRAIT_IMG, FATHER_S_PORTRAIT_IMG, MOTHER_PORTRAIT_IMG, MOTHER_S_PORTRAIT_IMG
        
        paths = {
            "Father": [FATHER_PORTRAIT_IMG, FATHER_S_PORTRAIT_IMG],
            "Mother": [MOTHER_PORTRAIT_IMG, MOTHER_S_PORTRAIT_IMG]
        }
        
        if character_name not in paths: return
        
        anim_paths = paths[character_name]
        self._anim_idx = 0
        
        def _swap(dt):
            self._anim_idx = 1 - self._anim_idx # สลับ 0 กับ 1
            self.update_right_portrait(anim_paths[self._anim_idx])
            
        # สลับทุกๆ 0.25 วินาที
        self.portrait_anim_event = Clock.schedule_interval(_swap, 0.25)

    def stop_portrait_animation(self):
        if self.portrait_anim_event:
            Clock.unschedule(self.portrait_anim_event)
            self.portrait_anim_event = None
        self.current_anim_character = None

    def update_ui_scaling(self):
        if self.game.is_dialogue_active and self.dialogue_bg:
            char_name = getattr(self.name_label, 'text', "") if self.name_label else ""
            msg_text = self.dialogue_text.text if self.dialogue_text else ""
            self.show_vn_dialogue(char_name, msg_text, choices=self.game.current_choices)
        
        if self.is_item_notif_active and self.item_notif_widget:
            text = self.last_notif_text
            img = self.last_notif_image
            self.close_item_discovery()
            self.show_item_discovery(text, img)

    def close_dialogue(self):
        """ปิดกล่องข้อความคุยและคืนสถานะเกม"""
        # จำสถานะก่อนรีเซ็ต
        last_char = getattr(self.game, 'current_character_name', None)
        has_choices = len(getattr(self.game, 'current_choices', [])) > 0
        
        self.stop_portrait_animation()
        if self.chat_tri_event: Clock.unschedule(self.chat_tri_event); self.chat_tri_event = None
        if self.dialogue_bg:
            if self.dialogue_bg.parent: self.dialogue_bg.parent.remove_widget(self.dialogue_bg)
            self.dialogue_bg = None
        if self.portrait_widget:
            if self.portrait_widget.parent: self.portrait_widget.parent.remove_widget(self.portrait_widget)
            self.portrait_widget = None
        if self.left_portrait_widget:
            if self.left_portrait_widget.parent: self.left_portrait_widget.parent.remove_widget(self.left_portrait_widget)
            self.left_portrait_widget = None
        self.dialogue_text = None
        self.name_label = None
        clear_choices(self.game)

        # คืนสถานะการคุย
        self.game.is_dialogue_active = False
        self.game.awaiting_item_receipt = False # ล้างธงเผื่อไว้
        self._on_close_dialogue_reset()
        
        # ปลดล็อกกล้องถ้าไม่ได้ติดคัทซีนตัวเมือง/เนื้อเรื่องหลัก
        if not self.game.is_cutscene_active:
            self.game.camera.locked = False
        
        # ตรวจสอบว่าเป็นการจบคัทซีนเนื้อเรื่องเสริมหรือไม่
        if self.game.is_cutscene_active and getattr(self.game, 'cutscene_step', 0) == 11:
            self.game.cutscene_manager.end_side_story_cutscene()
            self.game.camera.locked = False
        
        # ส่งต่อ Logic เนื้อเรื่อง
        self.game.story_manager.handle_dialogue_end(last_char, has_choices)
        
        # ตรวจสอบ Save Prompt ที่คิวไว้ (ถ้ามี และแชทจบจริงๆ ไม่ได้กำลังพักเพื่อโชว์ไอเทม)
        if getattr(self.game, 'pending_save_prompt', False) and \
           not self.is_item_notif_active and \
           not getattr(self.game, 'preserved_dialogue_data', None):
            self.game.pending_save_prompt = False
            self.game.show_save_screen()

        self.game.is_reaper_save_prompt = False
        self.game.tutorial_mode = False

    def _on_close_dialogue_reset(self):
        """รีเซ็ตค่าพื้นฐานหลังปิดบทสนทนา"""
        self.game.dialogue_timer = 0
        self.game.current_dialogue_queue = []
        self.game.current_dialogue_index = 0
        self.game.current_character_name = ""
        self.game.current_choices = []
        if hasattr(self.game, 'temp_dialogue_chars'):
            self.game.temp_dialogue_chars = []

    def next_dialogue(self):
        """ไปยังข้อความถัดไปในคิว"""
        if self.game.current_choices and self.game.current_dialogue_index == len(self.game.current_dialogue_queue) - 1:
            return

        # 1. ถ้ามีธง "รอรับไอเทม" (หมายถึงผู้เล่นกดอ่านประโยคให้ของแล้ว)
        if getattr(self.game, 'awaiting_item_receipt', False):
            self.game.awaiting_item_receipt = False
            current_text = self.game.current_dialogue_queue[self.game.current_dialogue_index]
            
            # เก็บสถานะแชทสำรองไว้เพื่อมาเปิดต่อหลังโชว์ไอเทมจบ
            self.game.preserved_dialogue_data = {
                "name": self.game.current_character_name,
                "queue": list(self.game.current_dialogue_queue),
                "index": self.game.current_dialogue_index,
                "portrait": self.game.current_portrait,
                "temp_chars": getattr(self.game, 'temp_dialogue_chars', [])
            }
            
            # โชว์ Banner ไอเทมก่อน (เพื่อให้ story_manager รู้ว่าจะต้อง Queue save ไว้)
            if "Blue Stone" in current_text:
                self.show_item_discovery("Received [Blue Stone]", "assets/items/blue stone.png")
                self.game.has_received_blue_stone = True
            elif "Lantern" in current_text:
                self.show_item_discovery("Received [Lantern]", "assets/Items/Lantern.png")
                self.game.has_received_lantern = True
                
            # ปิดกล่องแชทตาม User Request (Chat ควรจะหายไปก่อน)
            self.close_dialogue()
            return

        # 2. ขยับไปยังข้อความถัดไป
        self.game.current_dialogue_index += 1
        
        if self.game.current_dialogue_index < len(self.game.current_dialogue_queue):
            next_text = self.game.current_dialogue_queue[self.game.current_dialogue_index]
            is_last = (self.game.current_dialogue_index == len(self.game.current_dialogue_queue) - 1)
            
            if hasattr(self.game, 'temp_dialogue_chars') and self.game.temp_dialogue_chars:
                if self.game.current_dialogue_index < len(self.game.temp_dialogue_chars):
                    self.game.current_character_name = self.game.temp_dialogue_chars[self.game.current_dialogue_index]
            
            self.show_vn_dialogue(
                self.game.current_character_name, next_text, 
                choices=(self.game.current_choices if is_last else None),
                portrait=self.game.current_portrait
            )
        else:
            # ตรวจสอบลำดับการตรวจบ้าน Day 2
            if getattr(self.game, 'house_inspection_step', False) and hasattr(self.game, 'pending_drop_spot'):
                from data.settings import HOUSE_MARKS_MAPPING
                self.game.house_inspection_step = False
                spot = self.game.pending_drop_spot[0]
                mark_path = HOUSE_MARKS_MAPPING.get(tuple(spot))
                self.game.show_vn_dialogue("Little girl", "Should I leave a letter?", 
                                     choices=["Leave a letter", "Let me think"], portrait=mark_path)
                return

            self.close_dialogue()

    def on_choice_selected(self, choice):
        """จัดการเมื่อผู้เล่นเลือก Choice"""
        if getattr(self.game, 'click_sound', None):
            self.game.click_sound.play()
        from ui.choice import handle_choice_selection
        handle_choice_selection(self.game, choice)

    def show_item_discovery(self, text, image_path=None, choices=None):
        if self.item_notif_widget: 
             self.close_item_discovery()
             
        self.last_notif_text = text
        self.last_notif_image = image_path
        self.last_notif_choices = choices
        
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        scale = self.get_ui_scale()
        self.item_notif_widget = FloatLayout(size_hint=(1, 0.35), pos_hint={'center_x': 0.5, 'center_y': 0.55})
        with self.item_notif_widget.canvas.before:
            Color(0, 0, 0, 0.75)
            self.notif_banner_rect = Rectangle()
            Color(1, 1, 1, 0.1)
            self.notif_line_top = Line(width=1)
            self.notif_line_bottom = Line(width=1)
        def u_b(i, v):
            self.notif_banner_rect.pos = i.pos; self.notif_banner_rect.size = i.size
            self.notif_line_top.points = [i.x, i.top, i.right, i.top]
            self.notif_line_bottom.points = [i.x, i.y, i.right, i.y]
        self.item_notif_widget.bind(size=u_b, pos=u_b)
        
        text_label = Label(text=text, font_name=GAME_FONT, font_size=36 * scale, color=(1, 1, 1, 1),
                          size_hint=(1, None), height=40 * scale, pos_hint={'center_x': 0.5, 'center_y': 0.8}, bold=True)
        self.item_notif_widget.add_widget(text_label)

        if image_path:
            from kivy.uix.boxlayout import BoxLayout
            # ถ้าเป็น tuple spritesheet spec (path, cols, rows, col, row) ให้ wrap เป็น list 1 element
            # ถ้าเป็น str ธรรมดา ก็ wrap เป็น list เช่นกัน
            # ถ้าเป็น list ของ path หลายภาพ ใช้ตรงๆ
            if isinstance(image_path, str):
                images = [image_path]
            elif isinstance(image_path, tuple) and len(image_path) >= 5 and isinstance(image_path[0], str):
                images = [image_path]  # spritesheet frame spec
            else:
                images = list(image_path)  # list ของหลาย path
            
            i_sz = 90 * scale
            spacing = 20 * scale
            total_w = (len(images) * i_sz) + ((len(images) - 1) * spacing if len(images) > 1 else 0)
            
            icon_layout = BoxLayout(
                orientation='horizontal', 
                size_hint=(None, None), 
                size=(total_w, i_sz),
                pos_hint={'center_x': 0.5, 'center_y': 0.35},
                spacing=spacing
            )
            
            for img in images:
                box = Widget(size_hint=(None, None), size=(i_sz, i_sz))
                with box.canvas:
                    Color(1, 1, 1, 1)
                    try:
                        # รองรับ tuple (path, cols, rows, col_idx, row_idx) สำหรับ spritesheet
                        if isinstance(img, (tuple, list)) and len(img) >= 5:
                            img_path, s_cols, s_rows, s_col, s_row = img[0], img[1], img[2], img[3], img[4]
                            full_tex = CoreImage(img_path).texture
                            full_tex.mag_filter = 'nearest'
                            full_tex.min_filter = 'nearest'
                            frame_w = full_tex.width // s_cols
                            frame_h = full_tex.height // s_rows
                            # Kivy y-up: row 0 = บน = inv_y = height - frame_h
                            inv_y = full_tex.height - (s_row + 1) * frame_h
                            tex = full_tex.get_region(s_col * frame_w, inv_y, frame_w, frame_h)
                        else:
                            tex = CoreImage(img).texture
                            tex.mag_filter = 'nearest'
                            tex.min_filter = 'nearest'
                        box.rect = Rectangle(texture=tex, size=(i_sz, i_sz))
                    except Exception:
                        img_src = img[0] if isinstance(img, (tuple, list)) else img
                        box.rect = Rectangle(source=img_src, size=(i_sz, i_sz))
                def u_i_r(i, v):
                    i.rect.pos = i.pos
                box.bind(pos=u_i_r, size=u_i_r)
                icon_layout.add_widget(box)
                
            self.item_notif_widget.add_widget(icon_layout)

        if choices:
            draw_choice_buttons(self.game, choices)
        else:
            tri = self.create_pixel_triangle(scale, pos_y_ratio=0.08)
            self.item_notif_widget.add_widget(tri)
            self.item_tri_event = self.animate_pixel_triangle(tri)
            
        root.add_widget(self.item_notif_widget)
        self.is_item_notif_active = True

    def close_item_discovery(self):
        if self.item_tri_event: Clock.unschedule(self.item_tri_event); self.item_tri_event = None
        if self.item_notif_widget and self.item_notif_widget.parent:
            self.item_notif_widget.parent.remove_widget(self.item_notif_widget)
        self.item_notif_widget = None
        self.is_item_notif_active = False
        clear_choices(self.game)
        
        # ตรวจสอบว่ามีบทสนทนาที่ถูกพักไว้ (Paused) เพื่อโชว์ไอเทมหรือไม่
        if getattr(self.game, 'preserved_dialogue_data', None):
            data = self.game.preserved_dialogue_data
            del self.game.preserved_dialogue_data
            
            # คืนค่าสถานะแชท
            self.game.current_character_name = data["name"]
            self.game.current_dialogue_queue = data["queue"]
            self.game.current_dialogue_index = data["index"]
            self.game.current_portrait = data["portrait"]
            self.game.temp_dialogue_chars = data["temp_chars"]
            self.game.is_dialogue_active = True
            
            # ขยับไปยังประโยคถัดไปทันทีเพื่อให้คุยต่อ
            self.next_dialogue()
            return

        # ตรวจสอบว่ามีหน้าจอเซฟที่รอคิวอยู่หรือไม่ (และต้องไม่อยู่ระหว่างคุยต่อ)
        if getattr(self.game, 'pending_save_prompt', False) and not self.game.is_dialogue_active:
            self.game.pending_save_prompt = False
            self.game.show_save_screen()

        # Trigger logic ต่อเนื่องสำหรับไอเทมบางชิ้นเช่น LETTERS
        if hasattr(self, 'last_notif_text') and self.last_notif_text:
            self.game.story_manager.handle_dialogue_end(self.last_notif_text, False)
            self.last_notif_text = None
