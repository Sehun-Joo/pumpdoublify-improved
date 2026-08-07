import random
import sys
import os
import logging

log = logging.getLogger(__name__)

def parse_sm(sm):
    pairs = []
    i = 0
    while True:
        hash_idx = sm.find(b'#', i)
        if hash_idx == -1:
            break

        colon_idx = sm.find(b':', hash_idx)

        if colon_idx == -1:
            break

        semicolon_idx = sm.find(b';', colon_idx)

        if semicolon_idx == -1:
            break

        if hash_idx > i:
            pairs.append((None, sm[i:hash_idx]))

        key = sm[hash_idx+1:colon_idx]

        value = sm[colon_idx+1:semicolon_idx]
        
        pairs.append((key, value))
        
        i = semicolon_idx+1

    # Append remainder.
    if i < len(sm):
        pairs.append((None, sm[i:]))

    return pairs


def encode_sm(pairs):
    chunks = []
    for key, value in pairs:
        if key is None:
            chunks.append(value)
        else:
            chunks.append(b'#' + key + b':' + value + b';')

    return b''.join(chunks)


allowed_lr_pairs = set([
    (0,2), (0,3), (0,4),
    (1,2), (1,3), (1,4),
    (2,3), (2,4), (2,5), (2,6),
    (3,4), (3,5), (3,6), (3,7),
    (4,3), (4,5), (4,6), (4,7),
    (5,6), (5,7), (5,8), (5,9),
    (6,5), (6,7), (6,8), (6,9),
    (7,8), (7,9),
])

allowed_foot_movements = set([
    (0,0), (0,1), (0,2),
    (1,0), (1,1), (1,2),
    (2,0), (2,1), (2,2), (2,3), (2,4),
    (3,2), (3,3), (3,4), (3,5), (3,6), 
    (4,2), (4,3), (4,4), (4,5), (4,6),
    (5,3), (5,4), (5,5), (5,6), (5,7),
    (6,3), (6,4), (6,5), (6,6), (6,7),
    (7,5), (7,6), (7,7), (7,8), (7,9),
    (8,7), (8,8), (8,9),
    (9,7), (9,8), (9,9),
])

# Never let one foot cut diagonally across the gap between pads. These are the
# two X-shaped movements through the center of a doubles setup:
# P1 upper-right <-> P2 lower-left and P1 lower-right <-> P2 upper-left.
FORBIDDEN_CENTER_DIAGONALS = {
    (3, 5), (5, 3),
    (4, 6), (6, 4),
}

def is_safe_foot_movement(previous_panel, next_panel):
    movement = (next_panel, previous_panel)
    return (
        movement in allowed_foot_movements
        and movement not in FORBIDDEN_CENTER_DIAGONALS
    )

PANEL_COORDINATES = [
    (0, 0), (0, 2), (1, 1), (2, 2), (2, 0),
    (3, 0), (3, 2), (4, 1), (5, 2), (5, 0),
]

def panel_distance(a, b):
    ax, ay = PANEL_COORDINATES[a]
    bx, by = PANEL_COORDINATES[b]
    return abs(ax - bx) + abs(ay - by)

def get_step_feet(step_pattern, final_left_foot):
    """Reconstruct the foot attached to every generated output step."""
    toggle_count = 0
    for note_kind, _, _ in step_pattern:
        if note_kind in (STEP, SLIDE):
            toggle_count += 1

    initial_left_foot = (
        final_left_foot if toggle_count % 2 == 0 else not final_left_foot
    )
    last_left_foot = initial_left_foot
    feet = []
    for note_kind, _, _ in step_pattern:
        if note_kind == JACK:
            feet.append(last_left_foot)
        elif note_kind in (JUMP, JUMP_JACK):
            feet.extend((not last_left_foot, last_left_foot))
        else:
            last_left_foot = not last_left_foot
            feet.append(last_left_foot)
    return feet

#positions: left half, middle 6 x2, right half
#originally tested two different middle positions, but ended up leaving them identical
left_foot_distances = [
    [0, 0, -.05, 1, 1, 2, 2, 3, 4, 4],
    [2, 2, 0, 0, 0, 0, 0, 1, 2, 2],
    [2, 2, 0, 0, 0, 0, 0, 1, 2, 2],
    [3, 3, 2, 1, 1, 0, 0, .05, 1, 1],
]

right_foot_distances = [
    [1, 1, .05, 0, 0, 1, 1, 2, 3, 3],
    [2, 2, 1, 0, 0, 0, 0, 0, 1, 1],
    [2, 2, 1, 0, 0, 0, 0, 0, 1, 1],
    [4, 4, 3, 2, 2, 1, 1, -.05, 0, 0],
]

positions = [0,1,2,3,2,1]

# In either of the two middle positions, keep each foot on its own half of the
# center six panels.  These are hard constraints; the distance tables below
# are still used to score the remaining legal choices.
CENTER_POSITIONS = {1, 2}
CENTER_LEFT_FOOT_PANELS = {2, 3, 4}
CENTER_RIGHT_FOOT_PANELS = {5, 6, 7}

# The middle position next to P1 (position 1) keeps the right foot off P2
# center.  The middle position next to P2 (position 2) mirrors that rule for
# the left foot.  This turns the two middle positions into transition zones
# instead of allowing a center-panel-to-opposite-pad leap at the boundary.
CENTER_PANELS_BY_POSITION_AND_FOOT = {
    1: {
        True: {2, 3, 4},
        False: {5, 6},
    },
    2: {
        True: {3, 4},
        False: {5, 6, 7},
    },
}

jumps_for_position = [
    [(0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4), (2, 3), (2, 4)],
    [(2, 5), (2, 6), (3, 5), (3, 6), (4, 5), (4, 6)],
    [(3, 5), (3, 6), (3, 7), (4, 5), (4, 6), (4, 7)],
    [(5, 7), (5, 8), (5, 9), (6, 7), (6, 8), (6, 9), (7, 8), (7, 9)],
]

NEVER = float('-inf')
STATE_STEP_COUNT = 7

FORWARDNESS = [0, 2, 1, 2, 0, 0, 2, 1, 2, 0] #How far up each panel is

#this is the step generation logic, a lot of this is kinda arbitrary but I've arrived here after a lot of experimenting
def rate_step(notes, is_left_foot, position_index, is_single_step, og_note):
    # Check position
    position = positions[position_index]
    if position in CENTER_POSITIONS:
        allowed_panels = CENTER_PANELS_BY_POSITION_AND_FOOT[position][is_left_foot]
        if notes[-1] not in allowed_panels:
            return NEVER

    if is_left_foot:
        dist = left_foot_distances[position][notes[-1]]
    else:
        dist = right_foot_distances[position][notes[-1]]
    if dist >= 1:
        return NEVER

    # Start on middle blues for simplicity
    if len(notes) == 1:
        if is_left_foot:
            if notes[0] != 4: return NEVER
        else:
            if notes[0] != 5: return NEVER
            
    if len(notes) == 2:
        if notes != (4,5) and notes != (5,4):
            return NEVER

    # Check stretch / crossover
    if len(notes) >= 2:
        a, b = notes[-2:]
        if is_left_foot:
            a, b = b, a
        if not (a, b) in allowed_lr_pairs:
            return NEVER

    # Check shmoove
    if len(notes) >= 3:
        a = notes[-1]
        b = notes[-3]
        if (a, b) in FORBIDDEN_CENTER_DIAGONALS:
            return NEVER
        if not (a, b) in allowed_foot_movements:
            return NEVER

    # Check fast transition
    if len(notes) >= 5:
        a = notes[-1]
        b = notes[-5]
        if not (a, b) in allowed_foot_movements:
            return NEVER

    score = 0
    
    #using distance to weight for/against certain arrows in certain positions
    #for singles positions the center panel slightly prefers the outer foot
    if dist < 1:
        score -= dist
    
    #avoids stretches in half double positions
    if len(notes) >= 2 and position in [1,2]:
        a = notes[-1]
        b = notes[-2]
        if (a, b) in [(2,5),(2,6),(3,7),(4,7),(5,2),(6,2),(7,3),(7,4)]: #checks for center panel and further away corner
            score -= 0.25

    # Avoid medium-fast transition in singles, in half doubles it's ok
    if len(notes) >= 7 and position in [0,3]:
        a = notes[-1]
        b = notes[-7]
        if not (a, b) in allowed_foot_movements:
            score -= 0.15
    

    if len(notes) >= 3 and position in [1,2]:
        a = notes[-1]
        b = notes[-3]
        #transitions across middle of pads disfavors reds
        if (a,b) in [(3,6),(6,3)]:
            score -= 0.2

    if len(notes) >= 3:
        is_step = notes[-1] == notes[-3]
        was_step = len(notes) >= 5 and notes[-3] == notes[-5]
        was_was_step = len(notes) >= 7 and notes[-5] == notes[-7]
        step_matches = is_step == is_single_step

        #takes into account is_single_step, but prefers steps
        if is_step:
            score += 0.1
            if step_matches:
                score += 0.9
        #drill prevention
            if was_step:
                score -= 0.1
                if was_step == was_was_step:
                    score -= 0.1
                    
        if not is_step:
            if step_matches:
                score += 0.5
        

    if len(notes) >= 7:
        a = notes[-1]
        b = notes[-3]
        c = notes[-5]
        d = notes[-7]
        e = notes[-2]
        f = notes[-4]
        g = notes[-6]
        
        #avoids repeated back and forth movement
        if a == c and b == d:
            score -= 0.15
            
        if position in [1,2]:
        # Avoid crossing the middle a lot
            if all(n in (4,5) for n in (a,b,c,d)) or all(n in (3,6) for n in (a,b,c,d)):
                if a != b and b != c and c != d:
                    score -= 0.8
                    
        #avoids diagonal movement in half doubles
            if (a,b) in [(5,3),(4,6),(3,5),(6,4)]:
                score -= 0.3
            
        #encourages not staying in the same place in half doubles
            if all(n in (3,4,5,6) for n in (a,b,c,d,e,f,g)):
                score -= 0.05
            if all(n in (2,3,4) for n in (a,b,c,d,e,f,g)) or all(n in (5,6,7) for n in (a,b,c,d,e,f,g)):
                score -= 0.10
                    
        #avoids foot being on reds for too long in half doubles, helps make patterns good
            if FORWARDNESS[a] == FORWARDNESS[b] == FORWARDNESS[c] == 2 and not all(n in (3,4,5,6) for n in (a,b,c,d,e,f,g)):
                score -= 0.15
                if FORWARDNESS[d] == 2:
                    score -= 0.1
                
        #prefers 4-note sections to start and end with same note, helps create comfier patterns in half double
            if a == f:
                score += 0.1

    return score


JACK = 1
STEP = 2
SLIDE = 3
JUMP = 4
JUMP_JACK = 5

def get_step_pattern(measures):
    step_pattern = []

    prev_notes = [None, None]

    for measure_index, measure in enumerate(measures):
        for notes_index, notes in enumerate(measure):
            note_count = sum(n in b'124' for n in notes)
            step_kind = None
            og_note = None
            if note_count >= 2:
                if notes == prev_notes[-1]:
                    step_kind = JUMP_JACK
                else:
                    step_kind = JUMP
            elif note_count == 1:
                og_note = max(notes.find(n) for n in b'124')
                if notes == prev_notes[-1]:
                    step_kind = JACK
                elif notes == prev_notes[-2]:
                    step_kind = STEP
                else:
                    step_kind = SLIDE

            if step_kind is not None:
                note_beat = 4*measure_index + 4*notes_index/len(measure)
                step_pattern.append((step_kind, og_note, note_beat))
                prev_notes = [prev_notes[-1], notes]

    return step_pattern

def beats_to_times(bpm_changes, beats):
    bpm_change_index = 0
    prev_beat = 0
    time = 0
    times = []
    for beat in beats:
        # Process bpm changes between prev_beat and beat.
        while True:
            if bpm_change_index + 1 == len(bpm_changes):
                break
            if bpm_changes[bpm_change_index + 1][0] > beat:
                break
            change_beat = bpm_changes[bpm_change_index + 1][0]
            time += (change_beat - prev_beat) * 60 / bpm_changes[bpm_change_index][1]
            prev_beat = change_beat
            bpm_change_index += 1
        # Advance time to beat
        time += (beat - prev_beat) * 60 / bpm_changes[bpm_change_index][1]
        times.append(time)
        prev_beat = beat

    return times

def transition_step_bounds(bpm):
    # Don't worry.
    #i'm worried
    lo_bpm = 100
    mid_bpm = 190
    hi_bpm = 240

    lo_min = 8
    lo_max = 12

    mid_min = 16
    mid_max = 32

    hi_min = 24
    hi_max = 32

    if bpm <= lo_bpm:
        return (lo_min, lo_max)
    if bpm <= mid_bpm:
        t = (bpm - lo_bpm) / (mid_bpm - lo_bpm)
        return (lo_min + (mid_min-lo_min)*t, lo_max + (mid_max-lo_max)*t)
    if bpm <= hi_bpm:
        t = (bpm - mid_bpm) / (hi_bpm - mid_bpm)
        return (mid_min + (hi_min-mid_min)*t, mid_max + (hi_max-mid_max)*t)

    return (hi_min, hi_max)

def next_measure_index(beat):
    """Return the measure on which a newly due transition may begin."""
    return int(beat // 4) + 1

BEAM_SIZE = 50
MIN_HOLD_BEATS = 0.25
HOLD_TRANSITION_BUFFER_BEATS = 0.25

def doublify_measures(measures, bpm_changes):
    double_stream = []

    step_pattern = get_step_pattern(measures)

    beats = [p[2] for p in step_pattern]
    times = beats_to_times(bpm_changes, beats)

    times.append(times[-1] + 1)

    durations = [times[i+1] - times[i] for i in range(len(times)-1)]
    bpms = [60/4/d for d in durations]

    # We want to find the chart that maximizes total score according to rate_step.
    # But there's exponentially many possible charts to score.
    # So I'm using beam search to trim the possibilities (https://en.wikipedia.org/wiki/Beam_search)

    # States:
    # notes, is_left_foot -> score, full steps
    # full steps is a linked list (step, tail) of steps in reverse order.
    # This makes it possible to discard equivalent states with lower score.
    states = {
        ((), bool(random.randint(0, 1))): (0, None),
    }

    position_rate = 0 # 0 - 1, how fast the position changes.
    position_progress = 0 # 0 - 1, progress until next transition.
    pending_transition_measure = None
    # Always start in middle
    position_index = random.choice([1,4])
    was_jump = False

    for note_index in range(len(step_pattern)):
        note_kind, og_note, note_beat = step_pattern[note_index]
        bpm = bpms[note_index]
        if note_kind in [STEP, SLIDE] and not was_jump:
            current_measure = int(note_beat // 4)
            if (
                pending_transition_measure is not None
                and current_measure >= pending_transition_measure
            ):
                position_index = (position_index + 1) % len(positions)
                position_progress = 0
                position_rate = random.random()
                pending_transition_measure = None
                log.debug(
                    'Position transition at beat %.3f (measure %d, position %d)',
                    note_beat,
                    current_measure,
                    positions[position_index],
                )

        pos_steps_lo, pos_steps_hi = transition_step_bounds(bpm)
        pos_steps = pos_steps_lo + position_rate*(pos_steps_hi - pos_steps_lo)
        position_progress += 1 / pos_steps
        if position_progress >= 1 and pending_transition_measure is None:
            pending_transition_measure = next_measure_index(note_beat)

        new_state_pairs = []
        for old_state_key, old_state_value in states.items():
            old_steps, old_left_foot = old_state_key
            old_score, old_full_steps = old_state_value

            if note_kind == JACK:
                new_state_pairs.append((
                    (old_steps, old_left_foot),
                    (old_score, (old_full_steps[0], old_full_steps)),
                ))
            elif note_kind == JUMP and was_jump:
                old1 = old_full_steps[0]
                old0 = old_full_steps[1][0]

                if old_left_foot:
                    old_left_panel, old_right_panel = old1, old0
                else:
                    old_left_panel, old_right_panel = old0, old1

                candidates = [
                    j for j in jumps_for_position[positions[position_index]]
                    if min(*j) != min(old0, old1) or max(*j) != max(old0, old1)
                    if is_safe_foot_movement(old_left_panel, j[0])
                    and is_safe_foot_movement(old_right_panel, j[1])
                ]
                if candidates:
                    note0, note1 = random.choice(candidates)
                else:
                    # Repeating a stance is preferable to forcing either foot
                    # through an illegal transition when no new jump is safe.
                    note0, note1 = old_left_panel, old_right_panel
                if old_left_foot:
                    note0, note1 = note1, note0

                new_state_pairs.append((
                    ((note0, note1), old_left_foot),
                    (old_score, (note1, (note0, old_full_steps))),
                ))
            elif note_kind == JUMP:
                if old_full_steps is None:
                    if old_left_foot:
                        note0 = random.choice([5,6])
                        note1 = random.choice([3,4])
                    else:
                        note0 = random.choice([3,4])
                        note1 = random.choice([5,6])
                else:
                    note1 = old_full_steps[0]
                    previous_other_panel = old_full_steps[1][0]
                    
                    if old_left_foot:
                        candidates = [
                            b for a, b in jumps_for_position[positions[position_index]]
                            if a == note1
                            and is_safe_foot_movement(previous_other_panel, b)
                        ]
                    else:
                        candidates = [
                            a for a, b in jumps_for_position[positions[position_index]]
                            if b == note1
                            and is_safe_foot_movement(previous_other_panel, a)
                        ]

                    if candidates:
                        note0 = random.choice(candidates)
                    else:
                        # Keep the other foot planted if that existing stance
                        # is the only safe way to express the jump.
                        note0 = previous_other_panel

                new_state_pairs.append((
                    ((note0, note1), old_left_foot),
                    (old_score, (note1, (note0, old_full_steps))),
                ))
            elif note_kind == JUMP_JACK:
                note1 = old_full_steps[0]
                note0 = old_full_steps[1][0]

                new_state_pairs.append((
                    ((note0, note1), old_left_foot),
                    (old_score, (note1, (note0, old_full_steps))),
                ))
            elif was_jump:
                assert note_kind in [SLIDE, STEP], f'wtf? {note_kind}'
                old1 = old_full_steps[0]
                old0 = old_full_steps[1][0]
                new_state_pairs.append((
                    ((old0, old1, old0), not old_left_foot),
                    (old_score, (old0, old_full_steps)),
                ))
            else:
                assert note_kind in [STEP, SLIDE], 'wtf2?'
                for new_step in range(10):
                    new_steps = (old_steps + (new_step,))[-STATE_STEP_COUNT:]
                    new_left_foot = not old_left_foot
                    new_full_steps = (new_step, old_full_steps)
                    new_score = old_score + rate_step(
                        new_steps,
                        new_left_foot,
                        position_index,
                        note_kind == STEP,
                        og_note,
                    )
                    if new_score != NEVER:
                        new_state_pairs.append((
                            (new_steps, new_left_foot),
                            (new_score, new_full_steps),
                        ))

        was_jump = note_kind in [JUMP, JUMP_JACK]
        if was_jump:
            # Don't transition immediately after a jump.
            position_progress = min(0.999, position_progress)

        # Sort by score decreasing, breaking ties randomly.
        random.shuffle(new_state_pairs)
        new_state_pairs.sort(key=lambda pair: -pair[1][0])

        # Select the top BEAM_SIZE states.
        new_state_pairs = new_state_pairs[:BEAM_SIZE]

        states = {}
        for key, value in new_state_pairs:
            score, _ = value
            if key in states:
                existing_score = states[key][0]
                if existing_score >= score:
                    continue

            states[key] = value

        if len(states) == 0:
            log.warning(
                'Pattern search exhausted at event %d/%d (beat %.3f, position %d)',
                note_index + 1,
                len(step_pattern),
                step_pattern[note_index][2],
                positions[position_index],
            )
            return None

    if len(states) == 0:
        return None


    best_key, best_value = max(states.items(), key=lambda item: item[1][0])
    score, full_steps = best_value
    double_steps = []
    while full_steps is not None:
        double_steps.append(full_steps[0])
        full_steps = full_steps[1]
    double_steps = double_steps[::-1]
    double_feet = get_step_feet(step_pattern, best_key[1])
    assert len(double_feet) == len(double_steps)
    
    double_step_index = 0
    # Holds must retain their input-lane identity.  The old implementation
    # stored only a set of output panels, so a release could end a different
    # hold from the one that began on that input lane.
    source_holds = {}
    source_hold_feet = {}
    source_hold_start_indices = {}
    source_hold_start_beats = {}
    cancelled_source_holds = set()
    last_panel_by_foot = {}
    double_notes = []
    double_note_beats = []

    def convert_hold_start_to_tap(output_panel, start_index):
        row = double_notes[start_index]
        if row[output_panel] in b'24':
            double_notes[start_index] = (
                row[:output_panel] + b'1' + row[output_panel + 1:]
            )

    def place_early_release(output_panel, start_index, current_beat):
        """Trim a hold with a playable gap, or turn it into a tap."""
        start_beat = double_note_beats[start_index]
        latest_release_beat = current_beat - HOLD_TRANSITION_BUFFER_BEATS
        if latest_release_beat - start_beat < MIN_HOLD_BEATS:
            convert_hold_start_to_tap(output_panel, start_index)
            return

        for row_index in range(len(double_notes) - 1, start_index, -1):
            if double_note_beats[row_index] > latest_release_beat:
                continue
            row = double_notes[row_index]
            if row[output_panel] == ord('0'):
                double_notes[row_index] = (
                    row[:output_panel] + b'3' + row[output_panel + 1:]
                )
                return

        convert_hold_start_to_tap(output_panel, start_index)

    def cancel_output_hold(output_panel):
        """End a conflicting hold before output_panel is stepped again."""
        source_lane = next(
            (lane for lane, panel in source_holds.items()
             if panel == output_panel),
            None,
        )
        if source_lane is None:
            return

        start_index = source_hold_start_indices[source_lane]
        place_early_release(output_panel, start_index, current_beat)
        del source_holds[source_lane]
        del source_hold_feet[source_lane]
        del source_hold_start_indices[source_lane]
        del source_hold_start_beats[source_lane]
        cancelled_source_holds.add(source_lane)

    def choose_panel_for_free_foot(generated_panel, foot):
        """Keep a note on the unheld foot and in a playable stance."""
        previous_panel = last_panel_by_foot.get(foot)
        held = [
            (source_holds[lane], source_hold_feet[lane])
            for lane in source_holds
        ]
        candidates = []
        for panel in range(10):
            if chars[panel] != b'0' or panel in source_holds.values():
                continue
            if previous_panel is not None and not is_safe_foot_movement(previous_panel, panel):
                continue
            if held:
                held_panel, held_foot = held[0]
                if held_foot == foot:
                    continue
                stance = (panel, held_panel) if foot else (held_panel, panel)
                if stance not in allowed_lr_pairs:
                    continue
            score = panel_distance(panel, generated_panel)
            if previous_panel is not None:
                score += panel_distance(previous_panel, panel)
            candidates.append((score, panel))

        if not candidates:
            return None
        best_score = min(score for score, _ in candidates)
        return random.choice([
            panel for score, panel in candidates if score == best_score
        ])

    for measure_index, measure in enumerate(measures):
        for notes_index, notes in enumerate(measure):
            current_beat = 4*measure_index + 4*notes_index/len(measure)
            chars = [b'0']*10
            released_hold_start_indices = {}

            # Preserve the converter's existing preference when a source row
            # has more than two starts: taps are discarded first, followed by
            # holds, then rolls.  Unlike the old count-based code, retain the
            # input lane for every accepted hold.
            starts = [
                (source_lane, bytes([kind]))
                for source_lane, kind in enumerate(notes)
                if kind in b'124'
            ]
            while len(starts) > 2:
                discard_index = next(
                    (i for i, (_, kind) in enumerate(starts) if kind == b'1'),
                    None,
                )
                if discard_index is None:
                    discard_index = next(
                        (i for i, (_, kind) in enumerate(starts) if kind == b'2'),
                        None,
                    )
                if discard_index is None:
                    discard_index = 0
                source_lane, kind = starts.pop(discard_index)
                if kind in b'24':
                    cancelled_source_holds.add(source_lane)

            # Releases happen before starts on a row. This also handles a hold
            # ending while another begins without assigning the release to an
            # unrelated panel.
            for source_lane, kind in enumerate(notes):
                if kind != ord('3'):
                    continue
                if source_lane in cancelled_source_holds:
                    cancelled_source_holds.remove(source_lane)
                elif source_lane in source_holds:
                    output_panel = source_holds.pop(source_lane)
                    source_hold_feet.pop(source_lane)
                    start_index = source_hold_start_indices.pop(source_lane)
                    start_beat = source_hold_start_beats.pop(source_lane)
                    if current_beat - start_beat < MIN_HOLD_BEATS:
                        convert_hold_start_to_tap(output_panel, start_index)
                    else:
                        chars[output_panel] = b'3'
                        released_hold_start_indices[output_panel] = start_index
                else:
                    log.warning(
                        'Hold release on source lane %d has no matching start',
                        source_lane,
                    )

            # A two-foot chart cannot sustain more than two holds/steps at
            # once. Source charts sometimes overlap one pair of short holds
            # with the next pair; end the oldest output holds immediately
            # before the new row rather than producing a four-panel hold.
            reused_output_panels = []
            if len(source_holds) == 2 and len(starts) == 2:
                # Preserve the existing stance for a pair-to-pair handoff.
                # Choosing two newly generated panels here can demand a full
                # two-foot reposition in a single 192nd-note subdivision.
                reused_output_panels = [
                    (source_holds[lane], source_hold_feet[lane])
                    for lane in source_holds
                ]
                for output_panel, _ in reused_output_panels:
                    cancel_output_hold(output_panel)

            while len(source_holds) + len(starts) > 2:
                oldest_source_lane = next(iter(source_holds))
                cancel_output_hold(source_holds[oldest_source_lane])

            for source_lane, kind in starts:
                generated_output_panel = double_steps[double_step_index]
                generated_foot = double_feet[double_step_index]
                double_step_index += 1
                if reused_output_panels:
                    output_panel, foot = reused_output_panels.pop(0)
                else:
                    output_panel = generated_output_panel
                    foot = generated_foot

                    held_feet = set(source_hold_feet.values())
                    if foot in held_feet and len(held_feet) == 1:
                        foot = not foot
                    if source_holds:
                        free_foot_panel = choose_panel_for_free_foot(
                            generated_output_panel,
                            foot,
                        )
                        if free_foot_panel is not None:
                            output_panel = free_foot_panel

                if output_panel in source_holds.values():
                    cancel_output_hold(output_panel)

                # A release and a new start cannot share an output column on
                # one row. If generation selected that column, end the old hold
                # on the prior row and use this row for the new note.
                if chars[output_panel] == b'3':
                    place_early_release(
                        output_panel,
                        released_hold_start_indices[output_panel],
                        current_beat,
                    )
                    chars[output_panel] = b'0'

                chars[output_panel] = kind
                last_panel_by_foot[foot] = output_panel
                if kind in b'24':
                    source_holds[source_lane] = output_panel
                    source_hold_feet[source_lane] = foot
                    source_hold_start_indices[source_lane] = len(double_notes)
                    source_hold_start_beats[source_lane] = current_beat

            double_notes.append(b''.join(chars))
            double_note_beats.append(current_beat)

    assert double_step_index == len(double_steps)

    double_measures = []
    double_notes_index = 0
    for measure in measures:
        double_measures.append([])
        for _ in measure:
            double_measures[-1].append(double_notes[double_notes_index])
            double_notes_index += 1

    for measure_index in range(len(measures)):
        single_measure = measures[measure_index]
        double_measure = double_measures[measure_index]

        for notes_index in range(len(single_measure)):
            mine_count = sum(k in b'M' for k in single_measure[notes_index])

            if mine_count == 0:
                continue

            candidates = set(range(10))
            
            for measure_offset in range(-1, 2):
                i = measure_index + measure_offset
                if i < 0:
                    continue
                if i >= len(measures):
                    continue
                for notes in double_measures[i]:
                    for n, k in enumerate(notes):
                        if k in b'1234':
                            candidates.discard(n)

            mine_count = min(mine_count, len(candidates))
            for n in random.sample(list(candidates), mine_count):
                double_measure[notes_index] = double_measure[notes_index][:n] + b'M' + double_measure[notes_index][n+1:]

    return double_measures


def normalize_notes(notes):
    if b'//' in notes:
        notes = notes[:notes.index(b'//')]

    return notes.strip()

def doublify_notes_data(notes_data, bpm_changes):
    # Seed RNG with notes data for consistent charts.
    random.seed(notes_data)

    measures = [
        [normalize_notes(notes) for notes in measure.split(b'\n')]
        for measure in notes_data.split(b',')
    ]

    measures = [
        [notes for notes in measure if notes]
        for measure in measures
    ]

    double_measures = None
    retry_count = 10
    for i in range(retry_count):
        if i != 0:
            log.warning(f'Failed attempt to doublify. Retry #{i}.')
        double_measures = doublify_measures(measures, bpm_changes)
        if double_measures is not None:
            break
    if double_measures is None:
        raise Exception('Failed to doublify after 10 tries!')

    double_measures = b'\r\n,\r\n'.join(
        b'\r\n'.join(measure)
        for measure in double_measures
    ) + b'\r\n'

    return double_measures

def has_non_autogen_double_sm(pairs):
    for key, value in pairs:
        if key != b'NOTES': continue
        lines = value.split(b'\n')
        if len(lines) >= 3 and lines[1].strip() == b'pump-double:' and not lines[2].startswith(b'     AUTO '):
            return True

def is_double_chart_sm(key, value):
    if key != b'NOTES': return False
    lines = value.split(b'\n')
    return len(lines) >= 3 and lines[1].strip() == b'pump-double:'

def parse_bpms(raw_bpms):
    if len(raw_bpms) == 0:
        log.warning('No bpms???')
        return

    bpm_changes = [
        tuple(float(x.strip()) for x in part.split(b'='))
        for part in raw_bpms.split(b',')
    ]
    
    return bpm_changes

def doublify_sm(data):
    sm = parse_sm(data)

    # Skip files which have non-autogen double charts.
    if has_non_autogen_double_sm(sm):
        log.info('SKIPPED')
        return None

    # Remove double charts.
    sm = [
        pair for pair in sm
        if not is_double_chart_sm(*pair)
    ]

    for key, value in sm:
        if key == b'BPMS':
            bpm_changes = parse_bpms(value)
            break

    for key, value in sm[:]:
        if key != b'NOTES': continue
        try:
            lines = value.split(b'\n')
            header = lines[:6]
            notes_data = b'\n'.join(lines[6:])

            if b'dance-single:' not in header[1]:
                continue

            header[1] = b'     pump-double:\r'
            difficulty = header[3]
            log.info(f'  - {difficulty}')

            header[2] = b'     AUTO ' + header[2].strip()

            notes_data = doublify_notes_data(notes_data, bpm_changes)

            value = b'\n'.join(header) + b'\n' + notes_data
            sm.append((b'NOTES', value))
        except Exception:
            log.exception(f'Failed to doublify {difficulty}')

    return encode_sm(sm)

SSC_DESCRIPTION_KEYS = [b'CHARTNAME', b'DESCRIPTION', b'CREDIT']

def has_non_autogen_double_ssc(charts):
    chart_values = {}

    for chart in charts:
        chart_values = {key: value for key, value in chart if key is not None}
        is_double = chart_values.get(b'STEPSTYPE') == b'pump-double'
        is_auto = all(
            chart_values.get(key, b'').startswith(b'AUTO')
            for key in SSC_DESCRIPTION_KEYS
        )
        if is_double and not is_auto:
            return True

def split_ssc(ssc):
    song = []
    charts = []

    cur_chart = None
    for key, value in ssc:
        if key == b'NOTEDATA':
            cur_chart = []
            charts.append(cur_chart)

        if cur_chart is None:
            song.append((key, value))
        else:
            cur_chart.append((key, value))

    return song, charts

def doublify_ssc(data):
    ssc = parse_sm(data)

    song, charts = split_ssc(ssc)

    # Skip files which have non-autogen double charts.
    if has_non_autogen_double_ssc(charts):
        log.info('SKIPPED')
        return

    # Remove double charts.
    charts = [
        chart for chart in charts
        if (b'STEPSTYPE', b'pump-double') not in chart
    ]

    song_bpms = None
    for key, value in song:
        if key == b'BPMS':
            song_bpms = value
            break

    for chart in charts[:]:
        try:
            difficulty = None
            chart_values = {key: value for key, value in chart if key is not None}
            if chart_values.get(b'STEPSTYPE') != b'dance-single':
                continue

            notes_data = chart_values.get(b'NOTES')
            if notes_data is None:
                continue

            for key in SSC_DESCRIPTION_KEYS:
                chart_values[key] = b'AUTOv1.0 ' + chart_values.get(key, b'')

            chart_values[b'STEPSTYPE'] = b'pump-double'

            difficulty = chart_values.get(b'DIFFICULTY', b'???')
            log.info(f'  - {difficulty}')

            bpm_changes = parse_bpms(chart_values.get(b'BPMS', song_bpms))

            notes_data = doublify_notes_data(notes_data, bpm_changes)

            chart_values[b'NOTES'] = b'\n' + notes_data

            double_chart = []
            for key, value in chart:
                if key is None:
                    double_chart.append((key, value))
                else:
                    double_chart.append((key, chart_values[key]))
            charts.append(double_chart)
        except Exception:
            log.exception(f'Failed to doublify {difficulty}')

    ssc = song[:]
    for chart in charts:
        ssc += chart

    return encode_sm(ssc)

def doublify_path(path):
    if os.path.isdir(path):
        for filename in os.listdir(path):
            doublify_path(os.path.join(path, filename))
    else:
        lower_path = path.lower()
        is_sm = lower_path.endswith('.sm')
        is_ssc = lower_path.endswith('.ssc')
        if is_sm or is_ssc:
            log.info(f'Doublifying {path}')
            with open(path, 'rb') as file:
                data = file.read()
            try:
                if is_ssc:
                    data = doublify_ssc(data)
                else:
                    data = doublify_sm(data)
            except Exception:
                log.exception(f'Something went wrong doublifying {path}')
                return
            if data is None:
                return
            with open(path, 'wb') as file:
                file.write(data)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        log.error('Please supply a path to a folder or .sm file.')
        sys.exit(1)

    for path in sys.argv[1:]:
        doublify_path(path)
