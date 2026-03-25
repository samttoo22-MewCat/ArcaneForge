"""Shared pytest fixtures."""
import pytest
import pytest_asyncio


@pytest.fixture
def sample_player():
    return {
        "id": "player_test_01",
        "name": "測試玩家",
        "current_place_id": "room_town_square",
        "hp": 100,
        "hp_max": 100,
        "mp": 50,
        "mp_max": 50,
        "atk": 10,
        "def_": 5,
        "spd": 12,
        "luk": 8,
        "status_effects": [],
        "is_in_combat": False,
        "combat_room_id": None,
        "inventory_item_instance_ids": [],
        "equipped_slots": {},
    }


@pytest.fixture
def sample_npc():
    return {
        "id": "npc_goblin_01",
        "name": "哥布林",
        "current_place_id": "room_town_square",
        "hp": 15,
        "hp_max": 15,
        "atk": 5,
        "def_": 3,
        "spd": 10,
        "luk": 4,
        "is_hibernating": False,
        "behavior_state": "idle",
        "status_effects": [],
    }


@pytest.fixture
def sample_place():
    return {
        "id": "room_town_square",
        "name": "廣場",
        "description_base": "測試廣場",
        "light": "明亮",
        "weather": "晴天",
        "is_safe_zone": False,
        "player_ids": [],
        "npc_ids": [],
        "item_instance_ids": [],
        "parent_middle_id": "town_stonbridge",
    }


@pytest.fixture
def sample_item_instance():
    return {
        "instance_id": "item_sword_01",
        "item_id": "sword_iron",
        "durability": 100,
        "quantity": 1,
        "location_type": "room",
        "location_id": "room_town_square",
    }
