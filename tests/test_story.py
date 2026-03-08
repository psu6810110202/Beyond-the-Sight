import unittest
import sys
from unittest.mock import MagicMock
from tests.helper import setup_test_env

setup_test_env()

from managers.story import StoryManager

class TestStoryManager(unittest.TestCase):

    def setUp(self):
        self.mock_game = MagicMock()
        self.mock_game.current_day = 1
        self.mock_game.warning_triggered = False
        self.mock_game.warning_dismissed = False
        self.manager = StoryManager(self.mock_game)

    def test_get_config(self):
        config = self.manager.get_config()
        self.assertEqual(config["name"], "Day 1")

    def test_update_checks_warning_triggers(self):
        self.mock_game.player.logic_pos = (656, 100)
        self.manager.update(0.1)
        self.assertTrue(self.mock_game.warning_triggered)

if __name__ == '__main__':
    unittest.main()
