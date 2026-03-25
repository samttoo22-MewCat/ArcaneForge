"""V-04: Combat turn order validation."""
import pytest
from server.engine.combat import Combatant, tick_to_ready, check_double_action, calculate_damage, apply_damage


def make_combatant(id: str, spd: int, hp: int = 100, atk: int = 10, def_: int = 5) -> Combatant:
    return Combatant(id=id, spd=spd, hp=hp, hp_max=hp, atk=atk, def_=def_)


def test_faster_combatant_acts_first():
    fast = make_combatant("fast", spd=30)
    slow = make_combatant("slow", spd=10)
    ready = tick_to_ready([fast, slow])
    assert ready[0].id == "fast"


def test_action_bar_charges_accumulate():
    c = make_combatant("c", spd=20)
    initial_charge = c.charge
    c.tick()
    assert c.charge > initial_charge


def test_tick_to_ready_returns_at_least_one():
    c1 = make_combatant("c1", spd=10)
    c2 = make_combatant("c2", spd=8)
    ready = tick_to_ready([c1, c2])
    assert len(ready) >= 1


def test_dead_combatants_not_in_ready_list():
    alive = make_combatant("alive", spd=10)
    dead = make_combatant("dead", spd=20, hp=0)
    dead.is_alive = False
    ready = tick_to_ready([alive, dead])
    ids = [c.id for c in ready]
    assert "dead" not in ids
    assert "alive" in ids


class TestDoubleAction:
    def test_no_double_action_under_threshold(self):
        # 10 vs 9: 11% difference, not > 30%
        actor = make_combatant("actor", spd=10)
        opponent = make_combatant("opp", spd=9)
        assert check_double_action(actor, [opponent]) is False

    def test_double_action_above_threshold(self):
        # 100 vs 70: 43% difference, > 30%
        actor = make_combatant("actor", spd=100)
        opponent = make_combatant("opp", spd=70)
        assert check_double_action(actor, [opponent]) is True

    def test_double_action_exact_threshold(self):
        # actor=130, opponent=100: exactly 30% → NOT triggered (must be > 30%)
        actor = make_combatant("actor", spd=130)
        opponent = make_combatant("opp", spd=100)
        # 130 > 100 * 1.3 = 130 is False (not strictly greater)
        assert check_double_action(actor, [opponent]) is False

    def test_double_action_just_over_threshold(self):
        # actor=131, opponent=100: 31% difference
        actor = make_combatant("actor", spd=131)
        opponent = make_combatant("opp", spd=100)
        assert check_double_action(actor, [opponent]) is True

    def test_no_double_action_no_alive_opponents(self):
        actor = make_combatant("actor", spd=100)
        dead_opp = make_combatant("dead", spd=10)
        dead_opp.is_alive = False
        assert check_double_action(actor, [dead_opp]) is False


class TestDamageFormula:
    def test_minimum_damage_is_one(self):
        # ATK=1, DEF=100 should still deal 1 damage
        damage = calculate_damage(atk=1, def_=100, dm_modifier=1.0)
        assert damage >= 1

    def test_modifier_capped_in_combat(self):
        # With is_combat=True, modifier cap is 3.0.
        # Average over many runs: modifier=10.0 should produce same result as modifier=3.0
        avg_capped = sum(calculate_damage(atk=20, def_=0, dm_modifier=3.0) for _ in range(200)) / 200
        avg_over = sum(calculate_damage(atk=20, def_=0, dm_modifier=10.0) for _ in range(200)) / 200
        assert abs(avg_capped - avg_over) < 2.0  # within noise tolerance

    def test_higher_atk_deals_more_damage_on_average(self):
        # Run many times to average out random variance
        samples_high = [calculate_damage(atk=30, def_=5, dm_modifier=1.0) for _ in range(100)]
        samples_low = [calculate_damage(atk=10, def_=5, dm_modifier=1.0) for _ in range(100)]
        assert sum(samples_high) / 100 > sum(samples_low) / 100

    def test_apply_damage_kills_target(self):
        c = make_combatant("c", spd=10, hp=10)
        apply_damage(c, 100)
        assert c.hp == 0
        assert c.is_alive is False

    def test_apply_damage_floor_zero(self):
        c = make_combatant("c", spd=10, hp=5)
        apply_damage(c, 3)
        assert c.hp == 2
        assert c.is_alive is True
