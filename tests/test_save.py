import unittest
import sys
import json
import os
from unittest.mock import MagicMock, mock_open, patch
from tests.helper import setup_test_env

setup_test_env()

from managers.save import SaveManager

class TestSaveManager(unittest.TestCase):

    def setUp(self):
        self.mock_game = MagicMock()
        self.mock_game.current_day = 1
        self.mock_game.game_map.filename = "map.tmj"
        self.mock_game.player.logic_pos = (100, 100)
        self.mock_game.heart_ui.current_health = 3
        self.mock_game.play_time = 0.0
        self.mock_game.quest_success_count = 0
        self.mock_game.quest_item_fail = False
        self.mock_game.death_count = 0
        self.mock_game.warning_dismissed = False
        self.mock_game.has_received_blue_stone = False
        self.mock_game.has_received_lantern = False
        self.mock_game.tutorial_triggered = False
        self.mock_game.destroyed_enemies = []
        self.mock_game.enemies = []
        self.mock_game.collected_stars = []
        # Mock quest manager return
        self.mock_game.quest_manager.to_dict.return_value = {}
        self.manager = SaveManager(self.mock_game)

    @patch('os.path.exists', return_value=True)
    def test_save_confirmed(self, mock_exists):
        with patch('builtins.open', mock_open()) as m:
            self.manager.on_save_confirmed(1)
            m.assert_called()

if __name__ == '__main__':
    unittest.main()
