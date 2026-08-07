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

    def test_due_transitions_wait_for_the_next_measure(self):
        self.assertEqual(p.next_measure_index(0.0), 1)
        self.assertEqual(p.next_measure_index(3.999), 1)
        self.assertEqual(p.next_measure_index(4.0), 2)
        self.assertEqual(p.next_measure_index(17.5), 5)

    def test_jump_movement_safety_rejects_cross_center_diagonals(self):
        for previous_panel, next_panel in p.FORBIDDEN_CENTER_DIAGONALS:
            self.assertFalse(
                p.is_safe_foot_movement(previous_panel, next_panel)
            )

    def test_middle_jumps_respect_foot_ownership(self):
        for position in p.CENTER_POSITIONS:
            for left_panel, right_panel in p.jumps_for_position[position]:
                self.assertIn(left_panel, p.CENTER_LEFT_FOOT_PANELS)
                self.assertIn(right_panel, p.CENTER_RIGHT_FOOT_PANELS)

    def test_middle_jumps_avoid_center_panel_leaps_at_transitions(self):
        # Position 1 borders P1, so the right foot must already have left P2
        # center. Position 2 borders P2 and mirrors that restriction.
        self.assertTrue(
            all(right_panel != 7 for _, right_panel in p.jumps_for_position[1])
        )
        self.assertTrue(
            all(left_panel != 2 for left_panel, _ in p.jumps_for_position[2])
        )

    def test_single_steps_avoid_center_panel_leaps_at_transitions(self):
        self.assertEqual(p.rate_step((7,), False, 1, False, 0), p.NEVER)
        self.assertEqual(p.rate_step((2,), True, 2, False, 0), p.NEVER)

    def test_middle_single_steps_reject_the_other_foots_panels(self):
        for panel in p.CENTER_RIGHT_FOOT_PANELS:
            self.assertEqual(
                p.rate_step((panel,), True, 1, False, 0),
                p.NEVER,
            )
        for panel in p.CENTER_LEFT_FOOT_PANELS:
            self.assertEqual(
                p.rate_step((panel,), False, 1, False, 0),
                p.NEVER,
            )

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
                (hold_panel, tap_panel) in p.allowed_lr_pairs
                or (tap_panel, hold_panel) in p.allowed_lr_pairs
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
