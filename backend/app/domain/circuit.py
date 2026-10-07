"""Public module geometry and reciprocal-port graph proof, without answer arrays."""
SIDES = ('N', 'E', 'S', 'W')
DELTAS = ((-1, 0), (0, 1), (1, 0), (0, -1))
SHAPES = ('I', 'I', 'L', 'L', 'I', 'I', 'L', 'I', 'L')
INITIAL_ROTATIONS = (0,) * 9
SOURCE = {'module_id': 'c00', 'side': 'W'}
SINK = {'module_id': 'c10', 'side': 'W'}
MODULE_IDS = tuple(f'c{row}{column}' for row in range(3) for column in range(3))


def ports(index, rotation):
    base = (0, 2) if SHAPES[index] == 'I' else (0, 1)
    return {(side + rotation) % 4 for side in base}


def connected(rotations):
    """Traverse only adjacent modules with a port on both sides of each edge."""
    if 3 not in ports(0, rotations[0]) or 3 not in ports(3, rotations[3]):
        return False
    seen, pending = {0}, [0]
    while pending:
        index = pending.pop()
        if index == 3:
            return True
        row, column = divmod(index, 3)
        for side in ports(index, rotations[index]):
            dr, dc = DELTAS[side]
            nr, nc = row + dr, column + dc
            if not (0 <= nr < 3 and 0 <= nc < 3):
                continue
            neighbor = nr * 3 + nc
            if neighbor not in seen and (side + 2) % 4 in ports(neighbor, rotations[neighbor]):
                seen.add(neighbor)
                pending.append(neighbor)
    return False


def board(rotations, completed):
    return {'target_id': 'r2_powerbox', 'rows': 3, 'columns': 3,
            'source': dict(SOURCE), 'sink': dict(SINK),
            'modules': [{'module_id': module_id, 'row': index // 3, 'column': index % 3,
                         'shape': SHAPES[index], 'rotation': rotations[index]}
                        for index, module_id in enumerate(MODULE_IDS)],
            'status': 'completed' if completed else 'editing'}
