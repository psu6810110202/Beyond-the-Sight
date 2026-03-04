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

# Stamina
MAX_STAMINA = 100
STAMINA_DRAIN = MAX_STAMINA / (4 * FPS)  # ใช้เวลา 4 วินาทีจนกว่า Stamina จะหมด
STAMINA_REGEN = MAX_STAMINA / (5 * FPS)  # ใช้เวลา 5 วินาทีในการฟื้นฟูจนเต็ม

MAP_FILE = 'assets/Tiles/beyond.tmj'
SPLASH_COVER_IMG = 'assets/Covers/ปกเกม.png'
GAME_FONT = 'assets/Fonts/edit-undo.brk.ttf'

# กรอบภาพตัวละครดั้งเดิมเป็น 1:1 (จตุรัส) แก้ขนาดให้ใหญ่ขึ้นเป็น 64x64 
# ภาพจะไม่ยืด และเมื่อวางกึ่งกลาง จะทำให้ตัวละครจริงๆ มีขนาดเหมาะสมกับพื้น 32พอดี
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 32

PLAYER_IDLE_IMG = 'characters/assets/player/player_idle.png'
PLAYER_WALK_IMG = 'characters/assets/player/player_walk.png'

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
ENEMY_SPEED = RUN_SPEED - 0.5
ENEMY_DETECTION_RADIUS = 200

# ข้อมูลศัตรูแต่ละประเภท (ระบุภาพและขนาด spritesheet)
ENEMY_TYPES = {
    1: {
        'idle': {'path': 'characters/assets/Enemy/Enemy1_idle.png', 'cols': 1, 'rows': 4},
        'walk': {'path': 'characters/assets/Enemy/Enemy1_walk.png', 'cols': 3, 'rows': 4}
    },
    2: {
        'idle': {'path': 'characters/assets/Enemy/Enemy2_idle.png', 'cols': 1, 'rows': 4},
        'walk': {'path': 'characters/assets/Enemy/Enemy2_idle.png', 'cols': 1, 'rows': 4}
    }
}

# ตำแหน่งเกิดและประเภทของศัตรู
ENEMY_SPAWN_DATA = [
    {'pos': (1280, 240), 'type': 1},
    {'pos': (1584, 112), 'type': 2}
]