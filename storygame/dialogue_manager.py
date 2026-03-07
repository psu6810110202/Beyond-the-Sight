from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.clock import Clock
from settings import GAME_FONT, WINDOW_HEIGHT
from storygame.chat import DIALOGUE_CONFIG
from storygame.choice import draw_choice_buttons, clear_choices
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
        root = self.game.dialogue_root if self.game.dialogue_root else self.game
        cfg = DIALOGUE_CONFIG
        scale = self.get_ui_scale()
        self.game.current_choices = choices if choices else []
        if hasattr(self.game, 'clear_interaction_hints'):
            self.game.clear_interaction_hints()

        # self.close_dialogue() # เอาออกชั่วคราวเพื่อให้ Widget เก่ายังอยู่ขณะอัปเดต
        # เราจะจัดการเคลียร์เฉพาะส่วนที่จำเป็นแทน
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

        if choices:
            draw_choice_buttons(self.game, choices)

        # รายชื่อตัวละครปกติที่มีรูป Portrait ประจำตัว
        portrait_characters = ["Little girl", "Angel", "Devil", "Father", "Mother"]
        
        # ถ้ามีการระบุรูป Portrait มา (เช่น รูปบ้าน หรือรูปไอเทม) หรือเป็นตัวละครที่มีรูปประจำตัว
        if portrait or character_name in portrait_characters:
            from settings import PLAYER_PORTRAIT_IMG, ANGEL_PORTRAIT_IMG, DEVIL_PORTRAIT_IMG, FATHER_PORTRAIT_IMG, MOTHER_PORTRAIT_IMG
            
            # 1. แสดงรูปตามที่ส่งมาสำรองไว้ก่อน
            p_source = portrait
            
            # 2. ถ้าไม่ได้ส่งรูปมา แต่ชื่ออยู่ในลิสต์ ให้ดึงรูปประจำตัวมาใช้
            if not p_source and character_name in portrait_characters:
                portrait_map = {
                    "Angel": ANGEL_PORTRAIT_IMG,
                    "Devil": DEVIL_PORTRAIT_IMG,
                    "Father": FATHER_PORTRAIT_IMG,
                    "Mother": MOTHER_PORTRAIT_IMG
                }
                p_source = portrait_map.get(character_name, PLAYER_PORTRAIT_IMG)
            
            # ถ้าสุดท้ายมีรูปให้โชว์ (p_source ไม่เป็น None)
            if p_source:
                # ทุกรูป (ไม่ว่าจะตัวละครหรือไอเทม) ให้ใช้สเกลมาตรฐานเดียวกับ Little girl
                char_scale_mult = 1.0
                if "Items" in p_source or "mark" in p_source:
                    char_scale_mult = 0.6 # ปรับให้ใหญ่ขึ้นตามคำขอ แต่ไม่ถึง 1.0 เพื่อกันภาพแตกมากเกินไป
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
            if "Items" in left_portrait or "mark" in left_portrait:
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
                    self.left_portrait_widget.char_scale_mult = l_char_scale_mult
                    self.left_portrait_widget.size = (l_p_size, l_p_size)
                    self.left_portrait_rect.size = self.left_portrait_widget.size
                    self.left_portrait_rect.pos = (l_x_pos, l_y_base)

        self.game.is_dialogue_active = True

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

    def show_item_discovery(self, text, image_path=None, choices=None):
        if self.item_notif_widget: # ไม่ใช้ is_item_notif_active เช็คเพื่อรองรับการ refresh
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

        # จัดการรูปภาพ (รองรับทั้ง path เดียว และ list ของหลาย path)
        if image_path:
            from kivy.uix.boxlayout import BoxLayout
            images = [image_path] if isinstance(image_path, str) else image_path
            
            i_sz = 90 * scale
            spacing = 20 * scale
            total_w = (len(images) * i_sz) + ((len(images) - 1) * spacing if len(images) > 1 else 0)
            
            # Container สำหรับวางไอเทมหลายชิ้นเรียงกัน
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
                        tex = CoreImage(img).texture
                        tex.mag_filter = 'nearest'
                        tex.min_filter = 'nearest'
                        box.rect = Rectangle(texture=tex, size=(i_sz, i_sz))
                    except Exception:
                        box.rect = Rectangle(source=img, size=(i_sz, i_sz))
                def u_i_r(i, v):
                    i.rect.pos = i.pos
                box.bind(pos=u_i_r, size=u_i_r)
                icon_layout.add_widget(box)
                
            self.item_notif_widget.add_widget(icon_layout)

        if choices:
            draw_choice_buttons(self.game, choices)
        else:
            # ปรับ pos_y_ratio ให้ต่ำลงเพื่อไม่ให้สามเหลี่ยมซ้อนภาพไอเทม
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
        clear_choices(self.game) # ลบปุ่ม Choice เสมอเมื่อปิด
