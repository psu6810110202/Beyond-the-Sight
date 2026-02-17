from kivy.config import Config
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, TITLE

Config.set('graphics', 'width', str(WINDOW_WIDTH))
Config.set('graphics', 'height', str(WINDOW_HEIGHT))
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'position', 'auto')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

from kivy.app import App 
from kivy.uix.widget import Widget 
from kivy.graphics import Rectangle 
from kivy.core.window import Window 
from kivy.clock import Clock 

class GameWidget(Widget): 
    def __init__(self, **kwargs): 
        super().__init__(**kwargs) 

        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self) 
        self._keyboard.bind(on_key_down=self._on_key_down) 
        self._keyboard.bind(on_key_up=self._on_key_up) 

        self.pressed_keys = set() 
        Clock.schedule_interval(self.move_step, 0) 
        
        with self.canvas: 
            self.player = Rectangle(pos=(100, 100), size=(75, 100))

    def _on_keyboard_closed(self): 
        self._keyboard.unbind(on_key_down=self._on_key_down)  
        self._keyboard.unbind(on_key_up=self._on_key_up) 
        self._keyboard = None 

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        if keycode[1] == 'f11':
            if Window.fullscreen:
                Window.fullscreen = False
            else:
                Window.fullscreen = 'auto'

        print('down', text)
        self.pressed_keys.add(text)
        
    def _on_key_up(self, keyboard, keycode): 
        text = keycode[1] 
        print('up', text) 

        if text in self.pressed_keys:
            self.pressed_keys.remove(text)

    def move_step(self, dt):
        cur_x = self.player.pos[0] 
        cur_y = self.player.pos[1] 

        step = 200 * dt

        if 'w' in self.pressed_keys: 
            cur_y += step
        elif 'd' in self.pressed_keys: 
            cur_x += step
        elif 's' in self.pressed_keys: 
            cur_y -= step
        elif 'a' in self.pressed_keys: 
            cur_x -= step 

        self.player.pos = (cur_x, cur_y) 

class MyApp(App): 
    def build(self): 
        self.title = TITLE
        return GameWidget() 

if __name__ == '__main__': 
    app = MyApp() 
    app.run()