import unittest

import pumpdoublify as p


class PumpDoublifyTests(unittest.TestCase):
    def assert_valid_holds(self, output, maximum_active=2):
        active_panels = set()
        observed_maximum = 0
        for raw_row in output.splitlines():
            row = raw_row.strip()
            if not row or row == b',':
                continue
            self.assertEqual(len(row), 10)
            for panel, kind in enumerate(row):
                if kind in b'24':
                    self.assertNotIn(panel, active_panels)
                    active_panels.add(panel)
                elif kind == ord('3'):
                    self.assertIn(panel, active_panels)
                    active_panels.remove(panel)
            observed_maximum = max(observed_maximum, len(active_panels))

        self.assertEqual(active_panels, set())
        self.assertLessEqual(observed_maximum, maximum_active)

    def test_cross_center_diagonals_are_forbidden(self):
        cases = [
            ((3, 7, 5), True, 3),
            ((5, 2, 3), False, 0),
            ((4, 7, 6), True, 3),
            ((6, 2, 4), False, 0),
        ]
        for notes, is_left_foot, position_index in cases:
            self.assertEqual(
                p.rate_step(notes, is_left_foot, position_index, False, 0),
                p.NEVER,
            )

    def test_stacked_stances_and_crossovers_are_forbidden(self):
        self.assertFalse(p.is_safe_stance(0, 1))
        self.assertFalse(p.is_safe_stance(1, 0))
        self.assertFalse(p.is_safe_stance(3, 4))
        self.assertFalse(p.is_safe_stance(4, 3))
        self.assertFalse(p.is_safe_stance(5, 6))
        self.assertFalse(p.is_safe_stance(6, 5))
        self.assertTrue(p.is_safe_stance(2, 7))
        self.assertFalse(p.is_safe_stance(5, 4))
        self.assertFalse(p.is_safe_stance(0, 5))
        self.assertFalse(p.is_safe_stance(1, 6))
        self.assertFalse(p.is_safe_stance(4, 9))

    def test_slide_stances_do_not_trap_either_foot(self):
        self.assertFalse(p.stance_keeps_both_feet_mobile(0, 1))
        self.assertFalse(p.stance_keeps_both_feet_mobile(1, 0))
        self.assertFalse(p.stance_keeps_both_feet_mobile(8, 9))
        self.assertFalse(p.stance_keeps_both_feet_mobile(9, 8))
        self.assertFalse(p.stance_keeps_both_feet_mobile(3, 4))
        self.assertFalse(p.stance_keeps_both_feet_mobile(4, 3))
        self.assertTrue(p.stance_keeps_both_feet_mobile(2, 7))

    def test_all_nonstacked_noncrossing_center_stretches_are_legal(self):
        for left_panel in p.CENTER_PANELS:
            for right_panel in p.CENTER_PANELS:
                left_x = p.PANEL_COORDINATES[left_panel][0]
                right_x = p.PANEL_COORDINATES[right_panel][0]
                self.assertEqual(
                    p.is_safe_stance(left_panel, right_panel),
                    left_x < right_x,
                    (left_panel, right_panel),
                )

    def test_due_transitions_wait_for_the_next_measure(self):
        self.assertEqual(p.next_measure_index(0.0), 1)
        self.assertEqual(p.next_measure_index(3.999), 1)
        self.assertEqual(p.next_measure_index(4.0), 2)
        self.assertEqual(p.next_measure_index(17.5), 5)
        self.assertFalse(p.position_transition_is_due(2, 3, 0))
        self.assertTrue(p.position_transition_is_due(2, 4, 0))
        self.assertFalse(p.position_transition_is_due(7, 6, 0))
        self.assertFalse(p.position_transition_is_due(None, 8, 0))

    def test_transitions_do_not_split_source_anchors_or_measures(self):
        self.assertTrue(
            p.can_apply_position_transition(p.SLIDE, p.SLIDE, 8.0, False)
        )
        self.assertFalse(
            p.can_apply_position_transition(p.STEP, p.SLIDE, 8.0, False)
        )
        self.assertFalse(
            p.can_apply_position_transition(p.JACK, p.SLIDE, 8.0, False)
        )
        self.assertFalse(
            p.can_apply_position_transition(p.SLIDE, p.STEP, 8.0, False)
        )
        self.assertFalse(
            p.can_apply_position_transition(p.SLIDE, p.SLIDE, 8.25, False)
        )
        self.assertFalse(
            p.can_apply_position_transition(p.SLIDE, p.SLIDE, 8.0, True)
        )

    def test_jump_movement_safety_rejects_cross_center_diagonals(self):
        for previous_panel, next_panel in p.FORBIDDEN_CENTER_DIAGONALS:
            self.assertFalse(
                p.is_safe_foot_movement(previous_panel, next_panel)
            )

    def test_middle_jumps_are_reachable_and_non_crossing(self):
        for position in p.CENTER_POSITIONS:
            for left_panel, right_panel in p.jumps_for_position[position]:
                self.assertIn(left_panel, p.CENTER_LEFT_FOOT_PANELS)
                self.assertIn(right_panel, p.CENTER_RIGHT_FOOT_PANELS)
                self.assertTrue(p.is_safe_stance(left_panel, right_panel))

    def test_all_six_center_panels_are_available_outside_transition_prep(self):
        for position_index in (1, 2, 4, 5):
            jumps = p.get_jumps_for_position(position_index, False)
            self.assertEqual(
                {left_panel for left_panel, _ in jumps},
                p.CENTER_LEFT_FOOT_PANELS,
            )
            self.assertEqual(
                {right_panel for _, right_panel in jumps},
                p.CENTER_RIGHT_FOOT_PANELS,
            )

    def test_center_foot_allows_the_other_foot_anywhere_on_its_side(self):
        self.assertIn((2, 7), p.allowed_lr_pairs)
        self.assertTrue(p.is_safe_stance(2, 7))
        for position_index in (1, 2, 4, 5):
            self.assertIn(
                (2, 7),
                p.get_jumps_for_position(position_index, False),
            )
        self.assertNotEqual(
            p.rate_step((7, 2, 7), False, 1, True, 0),
            p.NEVER,
        )
        self.assertNotEqual(
            p.rate_step((2, 7, 2), True, 1, True, 0),
            p.NEVER,
        )

    def test_middle_jumps_avoid_center_panel_leaps_at_transitions(self):
        # position_index 5 exits toward P1; position_index 2 exits toward P2.
        toward_p1 = p.get_jumps_for_position(5, True)
        toward_p2 = p.get_jumps_for_position(2, True)
        self.assertTrue(
            all(right_panel != 7 for _, right_panel in toward_p1)
        )
        self.assertTrue(
            all(left_panel != 2 for left_panel, _ in toward_p2)
        )

    def test_transition_prep_is_directional_without_limiting_normal_center(self):
        self.assertIn(6, p.get_allowed_panels_for_position(5, True, False))
        self.assertNotIn(6, p.get_allowed_panels_for_position(5, True, True))
        self.assertIn(3, p.get_allowed_panels_for_position(5, False, False))
        self.assertNotIn(3, p.get_allowed_panels_for_position(5, False, True))
        self.assertIn(5, p.get_allowed_panels_for_position(2, True, False))
        self.assertNotIn(5, p.get_allowed_panels_for_position(2, True, True))

    def test_single_steps_avoid_center_panel_leaps_at_transitions(self):
        toward_p1 = ((7, 4, 7), False, 5)
        toward_p2 = ((2, 5, 2), True, 2)
        for notes, is_left_foot, position_index in (toward_p1, toward_p2):
            self.assertNotEqual(
                p.rate_step(notes, is_left_foot, position_index, True, 0),
                p.NEVER,
            )
            self.assertEqual(
                p.rate_step(
                    notes,
                    is_left_foot,
                    position_index,
                    True,
                    0,
                    True,
                ),
                p.NEVER,
            )

    def test_middle_feet_can_cross_the_pad_boundary_but_not_the_center_six(self):
        # Left foot can enter P2; right foot can enter P1.
        self.assertNotEqual(
            p.rate_step((4, 7, 5), True, 1, False, 0),
            p.NEVER,
        )
        self.assertNotEqual(
            p.rate_step((5, 2, 4), False, 1, False, 0),
            p.NEVER,
        )

        # Neither foot may swing all the way to the far edge of the center six.
        self.assertEqual(p.rate_step((7,), True, 1, False, 0), p.NEVER)
        self.assertEqual(p.rate_step((2,), False, 1, False, 0), p.NEVER)

    def test_source_slide_moves_the_same_foot(self):
        self.assertLess(
            p.rate_step((3, 5, 3), True, 1, False, 0),
            p.rate_step((3, 5, 4), True, 1, False, 0),
        )

        rows = [b'1000', b'0100', b'0010'] * 12
        output = p.doublify_notes_data(b'\n'.join(rows), [(0.0, 140.0)])
        output_rows = [row.strip() for row in output.splitlines() if row.strip()]
        panels = [
            next(panel for panel, kind in enumerate(row) if kind == ord('1'))
            for row in output_rows
        ]
        for index in range(2, len(panels)):
            self.assertNotEqual(panels[index], panels[index - 2])

    def test_source_drill_returns_are_preserved_without_a_length_cap(self):
        rows = [b'1000', b'0100'] * 16
        output = p.doublify_notes_data(b'\n'.join(rows), [(0.0, 140.0)])
        output_rows = [row.strip() for row in output.splitlines() if row.strip()]
        panels = [
            next(panel for panel, kind in enumerate(row) if kind == ord('1'))
            for row in output_rows
        ]

        for index in range(2, len(panels)):
            self.assertEqual(panels[index], panels[index - 2])

    def test_source_jack_is_preserved_without_a_length_cap(self):
        rows = [b'1000'] * 32
        output = p.doublify_notes_data(b'\n'.join(rows), [(0.0, 140.0)])
        output_rows = [row.strip() for row in output.splitlines() if row.strip()]
        panels = [
            next(panel for panel, kind in enumerate(row) if kind == ord('1'))
            for row in output_rows
        ]

        self.assertEqual(len(set(panels)), 1)

    def test_holds_and_rolls_resolve_on_their_start_panels(self):
        notes = b'''2000
0100
0000
3000
0044
0011
0033
1000
0200
0001
0300
0000'''
        output = p.doublify_notes_data(notes, [(0.0, 140.0)])
        self.assert_valid_holds(output)

    def test_taps_during_a_hold_stay_on_one_reachable_free_foot(self):
        rows = [b'0000'] * 32
        rows[0] = b'2000'
        rows[8] = b'0100'
        rows[12] = b'0010'
        rows[16] = b'0001'
        rows[24] = b'3000'
        output = p.doublify_notes_data(b'\n'.join(rows), [(0.0, 140.0)])
        output_rows = [row.strip() for row in output.splitlines() if row.strip()]

        hold_panel = next(
            panel for panel, kind in enumerate(output_rows[0]) if kind == ord('2')
        )
        tap_panels = [
            next(panel for panel, kind in enumerate(output_rows[row]) if kind == ord('1'))
            for row in (8, 12, 16)
        ]
        for previous, current in zip(tap_panels, tap_panels[1:]):
            self.assertTrue(p.is_safe_foot_movement(previous, current))
        for tap_panel in tap_panels:
            self.assertTrue(
                p.is_safe_stance(hold_panel, tap_panel)
                or p.is_safe_stance(tap_panel, hold_panel)
            )

    def test_foot_alternation_resumes_cleanly_after_a_hold(self):
        rows = [b'0000'] * 32
        rows[0] = b'2000'
        rows[8] = b'0100'
        rows[12] = b'0010'
        rows[16] = b'0001'
        rows[20] = b'3100'
        rows[24] = b'0010'
        output = p.doublify_notes_data(b'\n'.join(rows), [(0.0, 140.0)])
        output_rows = [row.strip() for row in output.splitlines() if row.strip()]

        hold_panel = next(
            panel for panel, kind in enumerate(output_rows[0]) if kind == ord('2')
        )
        last_free_panel = next(
            panel for panel, kind in enumerate(output_rows[16]) if kind == ord('1')
        )
        released_foot_panel = next(
            panel for panel, kind in enumerate(output_rows[20]) if kind == ord('1')
        )
        resumed_free_panel = next(
            panel for panel, kind in enumerate(output_rows[24]) if kind == ord('1')
        )

        self.assertTrue(
            p.is_safe_foot_movement(hold_panel, released_foot_panel)
        )
        self.assertTrue(
            p.is_safe_foot_movement(last_free_panel, resumed_free_panel)
        )

    def test_overlapping_hold_pairs_are_limited_to_two_feet(self):
        # The final section of We Luv Lama uses this staggered structure: a new
        # hold pair starts shortly before the preceding pair releases.
        rows = [b'0000'] * 192
        rows[0] = b'0022'
        rows[48] = b'2200'
        rows[60] = b'0033'
        rows[100] = b'3300'
        output = p.doublify_notes_data(b'\n'.join(rows), [(0.0, 140.0)])
        self.assert_valid_holds(output, maximum_active=2)

        output_rows = [row.strip() for row in output.splitlines() if row.strip()]
        first_stance = {
            panel for panel, kind in enumerate(output_rows[0]) if kind in b'24'
        }
        handoff_stance = {
            panel for panel, kind in enumerate(output_rows[48]) if kind in b'24'
        }
        self.assertEqual(handoff_stance, first_stance)

    def test_sub_quarter_beat_holds_become_taps(self):
        rows = [b'0000'] * 32
        rows[0] = b'2000'
        rows[1] = b'3000'
        output = p.doublify_notes_data(b'\n'.join(rows), [(0.0, 140.0)])
        output_rows = [row.strip() for row in output.splitlines() if row.strip()]
        self.assertEqual(sum(kind == ord('1') for kind in output_rows[0]), 1)
        self.assertNotIn(ord('2'), output_rows[0])
        self.assertNotIn(ord('3'), output_rows[1])


if __name__ == '__main__':
    unittest.main()
