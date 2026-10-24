import unittest
from pathlib import Path


class RtsPluginContractTest(unittest.TestCase):
    def test_recent_unit_combat_tracks_unit_and_building_hits(self) -> None:
        self.assertIn("Events.on(UnitDamageEvent.class", self.source)
        self.assertIn("Events.on(BuildDamageEvent.class", self.source)
        self.assertIn('root.put("recent_unit_combat"', self.source)
        self.assertIn('"raw_damage"', self.source)

    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cls.source = (root / "plugin" / "src" / "main" / "java" / "dev" / "capstone" /
                      "mindustry" / "MindustryAgentPlugin.java").read_text(encoding="utf-8")

    def test_dead_units_are_destroyed_over_the_network(self) -> None:
        self.assertIn("deadUnits.each(unit -> Call.unitDestroy(unit.id))", self.source)
        self.assertNotIn("deadUnits.each(Unit::remove)", self.source)

    def test_upgrade_inputs_are_removed_over_the_network(self) -> None:
        self.assertIn("Call.unitDespawn(inputs.get(input))", self.source)
        self.assertNotIn("inputs.get(input).remove()", self.source)

    def test_control_points_provide_benefits_but_not_victory(self) -> None:
        self.assertIn("RTS_CONTROL_NORTH_DAMAGE_MULTIPLIER = 1.15f", self.source)
        self.assertIn("RTS_CONTROL_CENTER_SPEED_MULTIPLIER = 1.15f", self.source)
        self.assertIn("RTS_CONTROL_SOUTH_DEFENSE_MULTIPLIER = 1.15f", self.source)
        self.assertIn("RTS_CONTROL_NEUTRAL_LOCK_SECONDS = 5d", self.source)
        self.assertIn("applyRtsControlPointCombatBuffs", self.source)
        self.assertIn("unit.applyDynamicStatus()", self.source)
        self.assertIn("buff.damageMultiplier", self.source)
        self.assertIn("buff.speedMultiplier", self.source)
        self.assertIn("buff.healthMultiplier", self.source)
        self.assertIn("rtsTacticalIntelligenceState", self.source)
        self.assertIn("neutralized RTS control point", self.source)
        self.assertIn("activeRtsControlPointCount", self.source)
        self.assertIn("Math.min(1.5d", self.source)
        self.assertNotIn('gameEndReason = "all_three_control_points_', self.source)
        self.assertNotIn("income_items", self.source)

    def test_per_frame_global_scans_are_throttled(self) -> None:
        self.assertIn("RTS_CONTROL_UPDATE_INTERVAL_TICKS = 10d", self.source)
        self.assertIn("RTS_DEAD_UNIT_CLEANUP_INTERVAL_TICKS = 15d", self.source)
        self.assertIn("strength * elapsedTicks", self.source)
        self.assertIn("0.5d * elapsedTicks", self.source)
        self.assertIn("Vars.state.tick < nextDeadUnitCleanupTick", self.source)
        self.assertIn("RTS_QUEUE_UPDATE_INTERVAL_TICKS = 6d", self.source)
        self.assertIn("RTS_SQUAD_MAINTENANCE_INTERVAL_TICKS = 15d", self.source)
        self.assertIn("Vars.state.tick < nextRtsQueueUpdateTick", self.source)
        self.assertIn("Vars.state.tick < nextRtsSquadMaintenanceTick", self.source)

    def test_training_can_stage_units_in_persistent_squads(self) -> None:
        self.assertIn('"training_squad_requires_rally"', self.source)
        self.assertIn("order.squadId", self.source)
        self.assertIn("squad.unitIds.add(unit.id)", self.source)
        self.assertIn("RTS_EMPTY_SQUAD_RETENTION_TICKS", self.source)
        self.assertIn('row.put("operation_phase", operationPhase)', self.source)
        self.assertIn('row.put("ready_for_new_order", readyForNewOrder)', self.source)

    def test_pending_squad_can_receive_a_standing_order(self) -> None:
        self.assertIn("acceptsPendingStandingOrder", self.source)
        self.assertIn("useExistingMembership && requestedUnitIds.isEmpty()", self.source)
        self.assertIn('result.put("standing_order_registered_for_pending_units"', self.source)
        self.assertIn('row.put("standing_order_registered_without_live_members"', self.source)
        self.assertIn("pendingReinforcements", self.source)

    def test_core_defender_uses_visible_respawn_cooldown(self) -> None:
        self.assertIn("CORE_DEFENDER_RESPAWN_DELAY_TICKS = 12d * 60d", self.source)
        self.assertIn("Math.max(Player.deathDelay, CORE_DEFENDER_RESPAWN_DELAY_TICKS)", self.source)
        self.assertIn('value.put("respawn_seconds_remaining"', self.source)

    def test_game_thread_state_requests_allow_serial_snapshot_work(self) -> None:
        self.assertIn("GAME_THREAD_REQUEST_TIMEOUT_SECONDS = 20", self.source)
        self.assertIn("future.get(GAME_THREAD_REQUEST_TIMEOUT_SECONDS", self.source)

    def test_state_profiles_skip_heavy_repeated_analysis(self) -> None:
        self.assertIn('Set.of("full", "decision", "execution")', self.source)
        self.assertIn('boolean includeDecisionAnalysis = !"execution".equals(profile)', self.source)
        self.assertIn('boolean includeStaticCatalog = "full".equals(profile)', self.source)
        self.assertIn('if (includeDecisionAnalysis)', self.source)
        self.assertIn('if (includeStaticCatalog)', self.source)

    def test_rts_construction_uses_parallel_slots_and_marks_destroyed_history(self) -> None:
        self.assertIn("RTS_CONSTRUCTION_PARALLEL_SLOTS = 2", self.source)
        self.assertIn("double[] slotAvailableAt", self.source)
        self.assertIn('result.put("construction_slot"', self.source)
        self.assertIn('row.put("construction_slot", order.slot + 1)', self.source)
        self.assertIn('"completed_then_destroyed"', self.source)
        self.assertIn('row.put("current_building_exists"', self.source)
        self.assertIn('row.put("currently_usable"', self.source)

    def test_showcase_uses_tactical_terrain_v5(self) -> None:
        self.assertIn("symmetric_three_lane_tactical_showcase_v5", self.source)
        self.assertIn("three-region competitive arena", self.source)
        self.assertIn("paintControlPointPlaza", self.source)
        self.assertIn("paintMirroredFloorTexture", self.source)
        self.assertIn("Blocks.grass", self.source)
        self.assertIn("Blocks.basalt", self.source)
        self.assertIn("placeMirroredXTerrainRect", self.source)
        self.assertIn("long southern two-bend rear approach", self.source)
        self.assertIn("air-only shortcuts across the neutral ridge", self.source)

    def test_defense_samples_expose_forward_tactical_geometry(self) -> None:
        self.assertIn('placement.put("defensive_zone", defensiveZone(anchorSteps))', self.source)
        self.assertIn('placement.put("frontline_relation", "between_core_and_ground_entry")', self.source)
        self.assertIn('value.put("strategic_defense_zones"', self.source)
        self.assertIn('return "forward_choke"', self.source)
        self.assertIn("defenseApproachTargets(core)", self.source)
        self.assertIn('value.put("approach_lane", rtsApproachLane(spawn[1]))', self.source)
        self.assertIn('return "north_industry"', self.source)
        self.assertIn('return "south_advanced"', self.source)


if __name__ == "__main__":
    unittest.main()
