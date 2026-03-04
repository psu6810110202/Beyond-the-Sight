class Story:
    """
    คลาสสำหรับเก็บข้อมูลเนื้อเรื่อง (Day 1, Day 2, etc.)
    """
    def __init__(self):
        self.story_log = []
        
    def day_1(self):
        self.story_log.append("Day 1: The First Morning")
        # สามารถเพิ่มข้อความเนื้อเรื่องอื่นๆ ได้ที่นี่