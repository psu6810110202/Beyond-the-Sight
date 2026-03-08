import unittest
import sys
from unittest.mock import MagicMock
from tests.helper import setup_test_env

setup_test_env()

from managers.game_logic import GameplayManager

class MockEnemy:
    def __init__(self, _id, px, py):
        self.id = _id
        self.logic_pos = (px, py)
        self.is_stunned = False
    def stun(self, duration=3.0):
        self.is_stunned = True

class TestGameplayManager(unittest.TestCase):

    def setUp(self):
        self.mock_game = MagicMock()
        self.mock_game.death_count = 0
        self.mock_game.player.logic_pos = (50, 50)
        self.mock_game.enemies = []
        self.manager = GameplayManager(self.mock_game)

    def test_respawn_increments_death_count(self):
        self.manager.respawn_at_reaper()
        self.assertEqual(self.mock_game.death_count, 1)

    def test_use_stun_item(self):
        enemy1 = MockEnemy("E1", 60, 60) # In range
        self.mock_game.enemies = [enemy1]
        self.manager.use_stun_item()
        self.assertTrue(enemy1.is_stunned)

if __name__ == '__main__':
    unittest.main()
