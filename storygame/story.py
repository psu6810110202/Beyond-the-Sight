# storygame/story.py
from storygame.chat import WARNING_DIALOGUE, WARNING_CHOICES

# ข้อมูลการตั้งค่าของแต่ละวัน
STORY_CONFIG = {
    1: {
        "name": "Day 1",
        "visible_npcs": [0],  # เฉพาะ NPC1 (Index 0)
        "warning_triggers": [
            {
                "type": "coordinate",
                "x": 656,
                "y": None,
                "buffer": 16,
                "dialogue": WARNING_DIALOGUE,
                "choices": WARNING_CHOICES
            },
            {
                "type": "coordinate",
                "x": None,
                "y": 464,
                "buffer": 16,
                "dialogue": WARNING_DIALOGUE,
                "choices": WARNING_CHOICES
            }
        ]
    },
    # สามารถเพิ่ม Day 2, Day 3 ต่อได้ที่นี่
}

def get_day_config(day):
    """ดึงข้อมูลการตั้งค่าของวันที่ระบุ"""
    return STORY_CONFIG.get(day, {})

def check_story_triggers(game):
    """ตรวจสอบ Trigger เนื้อเรื่องตามวันปัจจุบัน"""
    config = get_day_config(game.current_day)
    if not config:
        return

    # 1. ตรวจสอบ Warning Triggers (พิกัดอันตราย)
    if not game.warning_dismissed:
        px, py = game.player.logic_pos
        triggers = config.get("warning_triggers", [])
        
        for trigger in triggers:
            if trigger["type"] == "coordinate":
                target_x = trigger.get("x")
                target_y = trigger.get("y")
                buffer = trigger.get("buffer", 16)
                
                match_x = (target_x is None or abs(px - target_x) < buffer)
                match_y = (target_y is None or abs(py - target_y) < buffer)
                
                if match_x and match_y:
                    if not game.warning_triggered:
                        # หยุดเดิน
                        game.pressed_keys.clear()
                        game.player.is_moving = False
                        
                        # Snap to Grid: ปรับตำแหน่งให้ลงล็อคช่องพอดี
                        from settings import TILE_SIZE
                        snapped_x = round(game.player.logic_pos[0] / TILE_SIZE) * TILE_SIZE
                        snapped_y = round(game.player.logic_pos[1] / TILE_SIZE) * TILE_SIZE
                        game.player.logic_pos = [snapped_x, snapped_y]
                        game.player.target_pos = [snapped_x, snapped_y]
                        
                        # อัปเดตตำแหน่งภาพให้ตรงกับ Logic ทันที
                        game.player.sync_graphics_pos()
                        
                        game.player.state = 'idle'
                        game.player.update_animation_speed()
                        game.player.update_frame()
                        
                        # แสดงบทสนทนา
                        game.show_dialogue_above_reaper(
                            trigger["dialogue"], 
                            choices=trigger.get("choices")
                        )
                        game.warning_triggered = True
                        return True
        
        # ถ้าไม่มี Trigger ไหนทำงานในเฟรมนี้ ให้รีเซ็ต warning_triggered
        # แต่ต้องระวังไม่ให้รีเซ็ตตอนที่กำลังคุยอยู่
        if not any_trigger_hit(game, triggers):
            game.warning_triggered = False
            
    return False

def any_trigger_hit(game, triggers):
    px, py = game.player.logic_pos
    for trigger in triggers:
        if trigger["type"] == "coordinate":
            target_x = trigger.get("x")
            target_y = trigger.get("y")
            buffer = trigger.get("buffer", 16)
            if (target_x is None or abs(px - target_x) < buffer) and (target_y is None or abs(py - target_y) < buffer):
                return True
    return False

def is_npc_visible(game, npc_index):
    """ตรวจสอบว่า NPC ตัวนั้นควรแสดงผลในวันนี้หรือไม่"""
    config = get_day_config(game.current_day)
    visible_npcs = config.get("visible_npcs")
    
    # ถ้าไม่ได้ระบุไว้ ให้ถือว่าเห็นทั้งหมด
    if visible_npcs is None:
        return True
        
    return npc_index in visible_npcs