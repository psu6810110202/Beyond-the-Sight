# Window Settings
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
FPS = 60
TITLE = "Beyond the Sight"

SAFE_ZONE_RADIUS = 80

# Map Settings
MAP_WIDTH = 1600
MAP_HEIGHT = 1600

# Camera Settings
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240

# Tile Settings
TILE_SIZE = 16
WALK_SPEED = 2   # ความเร็วเดินปกติ
RUN_SPEED = 4    # ความเร็วตอนวิ่ง (ต้องหาร TILE_SIZE ลงตัวจะดีที่สุด)
PLAYER_START_X = 1152
PLAYER_START_Y = 80

# Stamina
MAX_STAMINA = 100
STAMINA_DRAIN = MAX_STAMINA / (3 * FPS)  # ใช้เวลา 3 วินาทีจนกว่า Stamina จะหมด
STAMINA_REGEN = MAX_STAMINA / (6 * FPS)  # ใช้เวลา 6 วินาทีในการฟื้นฟูจนเต็ม

MAP_FILE = 'assets/Tiles/beyond.tmj'
SPLASH_COVER_IMG = 'assets/Covers/ปกเกม.png'
GAME_FONT = 'assets/Fonts/edit-undo.brk.ttf'
STAR_IMG = 'assets/Items/Star.png'

# ตำแหน่งการเกิดของดาวใน Day 1
STAR_SPAWN_LOCATIONS = [
    (1056, 112), (928, 32), (1344, 80), 
    (1216, 256), (960, 384), (1152, 416)
]

# กรอบภาพตัวละครดั้งเดิมเป็น 1:1 (จตุรัส) แก้ขนาดให้ใหญ่ขึ้นเป็น 64x64 
# ภาพจะไม่ยืด และเมื่อวางกึ่งกลาง จะทำให้ตัวละครจริงๆ มีขนาดเหมาะสมกับพื้น 32พอดี
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 32

PLAYER_IDLE_IMG = 'characters/assets/player/player_idle.png'
PLAYER_WALK_IMG = 'characters/assets/player/player_walk.png'
PLAYER_PORTRAIT_IMG = 'characters/assets/player/player_n.png'
PLAYER_S_PORTRAIT_IMG = 'characters/assets/player/player_s.png'
ANGEL_PORTRAIT_IMG = 'characters/assets/pic/Angle_n.png'
DEVIL_PORTRAIT_IMG = 'characters/assets/pic/Devil_n.png'
FATHER_PORTRAIT_IMG = 'characters/assets/pic/Father_n.png'
FATHER_S_PORTRAIT_IMG = 'characters/assets/pic/Father_s.png'
MOTHER_PORTRAIT_IMG = 'characters/assets/pic/Mother_n.png'
MOTHER_S_PORTRAIT_IMG = 'characters/assets/pic/Mother_s.png'

# แผนที่ไอเทมและรูปหน้าตัวละครตามพิกัดดาวใน Day 1
STAR_ITEM_MAPPING = {
    (960, 384):  {"img": "assets/items/doll/head.png",       "portrait": PLAYER_PORTRAIT_IMG,   "fail": False},
    (1344, 80):  {"img": "assets/items/doll/body.png",       "portrait": PLAYER_PORTRAIT_IMG,   "fail": False},
    (1216, 256): {"img": "assets/items/doll/armsnlegs.png",  "portrait": PLAYER_PORTRAIT_IMG,   "fail": False},
    (1056, 112): {"img": "assets/Items/metal/metal1.png",    "portrait": PLAYER_S_PORTRAIT_IMG, "fail": True},
    (928, 32):   {"img": "assets/Items/metal/metal2.png",    "portrait": PLAYER_S_PORTRAIT_IMG, "fail": True},
    (1152, 416): {"img": "assets/Items/metal/metal3.png",    "portrait": PLAYER_S_PORTRAIT_IMG, "fail": True},
}

# ตำแหน่งหน้าบ้านที่ต้องเอาไปวาง (Day 2)
HOUSE_DOOR_SPOTS = [
    (240, 128), (64, 128), (560, 432), (784, 432), (992, 272)
]

# แมปพิกัดประตูกับรูปสัญลักษณ์ (Day 2)
HOUSE_MARKS_MAPPING = {
    (240, 128): "assets/mark/Hippo.png",
    (64, 128):  "assets/mark/bird.png",
    (560, 432): "assets/mark/circle.png",
    (784, 432): "assets/mark/cross.png",
    (992, 272): "assets/mark/square.png"
}

# NPC Settings
NPC_WIDTH = 16  # Hitbox width
NPC_HEIGHT = 4  # Hitbox height (feet only)
NPC_VISUAL_WIDTH = 32  # Visual sprite size
NPC_VISUAL_HEIGHT = 32  # Visual sprite size
NPC_SPEED = 1
# NPC Sprite Settings
NPC_SPRITE_WIDTH = 32
NPC_SPRITE_HEIGHT = 48
NPC_ANIMATION_SPEED = 0.2

NPC_IMAGE_LIST = [
    'characters/assets/NPC/NPC1.png',
    'characters/assets/NPC/NPC2.png',
    'characters/assets/NPC/NPC3.png',
    'characters/assets/NPC/NPC4.png',
    'characters/assets/NPC/NPC5.png'
]
NPC_COUNT = len(NPC_IMAGE_LIST)

# Reaper Settings
REAPER_WIDTH = 16  # Hitbox width
REAPER_HEIGHT = 4  # Hitbox height (feet only)
REAPER_VISUAL_WIDTH = 64  # Visual sprite size
REAPER_VISUAL_HEIGHT = 64  # Visual sprite size
REAPER_SPEED = 1.5

REAPER_IMG = 'characters/assets/Reaper/Reaper.png'

# Enemy Settings
ENEMY_WIDTH = 32
ENEMY_HEIGHT = 32
ENEMY_SPEED = WALK_SPEED + 1.5
ENEMY_DETECTION_RADIUS = 200

# ข้อมูลศัตรูแต่ละประเภท (ระบุภาพและขนาด spritesheet)
ENEMY_TYPES = {
    1: {
        'idle': {'path': 'characters/assets/Enemy/Enemy1_idle.png', 'cols': 1, 'rows': 4},
        'walk': {'path': 'characters/assets/Enemy/Enemy1_walk.png', 'cols': 3, 'rows': 4}
    },
    2: {
        'idle': {'path': 'characters/assets/Enemy/Enemy2_idle.png', 'cols': 1, 'rows': 4},
        'walk': {'path': 'characters/assets/Enemy/Enemy2_walk.png', 'cols': 8, 'rows': 4}
    },
    3: {
        'idle': {'path': 'characters/assets/Enemy/Enemy3_idle.png', 'cols': 1, 'rows': 4},
        'walk': {'path': 'characters/assets/Enemy/Enemy3_walk.png', 'cols': 8, 'rows': 4}
    }
}

# ตำแหน่งเกิดและประเภทของศัตรู
ENEMY_SPAWN_DATA = [
    {'pos': (1168, 240), 'type': 1},
    {'pos': (848, 400), 'type': 2},
    {'pos': (768, 96), 'type': 2},
    {'pos': (1536, 112), 'type': 1},
    {'pos': (1280, 320), 'type': 3},
    {'pos': (992, 224), 'type': 1},
    {'pos': (640, 160), 'type': 2},
    {'pos': (1408, 64), 'type': 3},
    {'pos': (576, 320), 'type': 1},
    {'pos': (1600, 288), 'type': 2}
]

# ตำแหน่งจุดค้นหาในบ้าน (Home Map)
SEARCHABLE_SPOTS_HOME = [
    (16, 0), (80, 176), (96, 176), (112, 176), (160, 176), (176, 176), 
    (256, 176), (272, 176), (288, 160), (304, 128)
]
EMPTY_SPOT_HOME = (240, 112)
HOME_EAT_POS = (16, 176)