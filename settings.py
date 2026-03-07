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
REAPER_PORTRAIT_IMG = 'characters/assets/Reaper/Reaper_n.png'

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
ENEMY_SPAWN_DATA = {
    1: [
        {'pos': (1168, 240), 'type': 1},
        {'pos': (848, 400), 'type': 2},
        {'pos': (768, 96), 'type': 2},
        {'pos': (1536, 112), 'type': 1}
    ],
    2: [
        {'pos': (32, 96), 'type': 1},
        {'pos': (144, 336), 'type': 2},
        {'pos': (464, 208), 'type': 3},
        {'pos': (496, 416), 'type': 1}
    ],
    3: [
        {'pos': (752, 784), 'type': 2},
        {'pos': (416, 1120), 'type': 3},
        {'pos': (528, 720), 'type': 1},
        {'pos': (432, 1456), 'type': 2}
    ],
    4: [
        {'pos': (1232, 1248), 'type': 3},
        {'pos': (1120, 704), 'type': 3},
        {'pos': (1008, 1296), 'type': 1},
        {'pos': (1552, 608), 'type': 2}
    ]
}

# ตำแหน่งยมทูตในแมพ Underground (Day 5)
REAPER_SPAWN_DATA_UNDERGROUND = [
    (1024, 160), (240, 464), (784, 656), (480, 992), (256, 656)
]

# ตำแหน่งจุดค้นหาในบ้าน (Home Map)
SEARCHABLE_SPOTS_HOME = [
    (16, 0), (80, 176), (96, 176), (112, 176), (160, 176), (176, 176), 
    (256, 176), (272, 176), (288, 160), (304, 128)
]
EMPTY_SPOT_HOME = (240, 112)

# ตำแหน่งจุดค้นหาใน Underground (จะถูกสร้างดวงดาวตามเลเยอร์ 'ของ')
SEARCHABLE_SPOTS_UNDERGROUND = []
UNDERGROUND_TRUE_POSITIONS = [(928, 48), (288, 112), (736, 1264)]
HOME_EAT_POS = (16, 176)

# ตำแหน่งเทียนใน Day 3
CANDLE_IMG = 'assets/Items/candle/candle.png'
CANDLE_SPAWN_LOCATIONS = [
    (688, 1312), (528, 960), (462, 560)
]

# การจับคู่สีที่ถูกต้องสำหรับแต่ละจุด (User Request)
CANDLE_COLOR_MAPPING = {
    (688, 1312): "RED",
    (528, 960):  "BLUE",
    (462, 560):  "YELLOW"
}

# Underground Portal
UNDERGROUND_PORTAL_POS = (1488, 16)

# ข้อมูลเควส Day 4: ตามหากุญแจ
DAY4_STAR_LOCATIONS = [
    (1536, 1184), (1232, 1072), (912, 1376), (880, 928), (1248, 752)
]

# เฉพาะจุด (1536, 1184) ที่เป็นกุญแจจริง นอกนั้นเป็นขยะ/ของเสีย (fail=True)
DAY4_KEY_MAPPING = {
    (1536, 1184): {"img": "assets/Items/key.png",      "portrait": PLAYER_PORTRAIT_IMG,   "fail": False, "is_key": True},
    (1232, 1072): {"img": "assets/Items/key_w.png", "portrait": PLAYER_S_PORTRAIT_IMG, "fail": True},
    (912, 1376):  {"img": "assets/Items/key_w.png", "portrait": PLAYER_S_PORTRAIT_IMG, "fail": True},
    (880, 928):   {"img": "assets/Items/key_w.png", "portrait": PLAYER_S_PORTRAIT_IMG, "fail": True},
    (1248, 752):  {"img": "assets/Items/key_w.png", "portrait": PLAYER_S_PORTRAIT_IMG, "fail": True},
}
