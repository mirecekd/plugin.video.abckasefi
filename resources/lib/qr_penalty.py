# resources/lib/qr_penalty.py
"""Mask patterns and the penalty score used to choose between them (ISO/IEC 18004 section 7.8)."""
from __future__ import annotations

_FINDER_LIKE_A = (True, False, True, True, True, False, True, False, False, False, False)
_FINDER_LIKE_B = tuple(reversed(_FINDER_LIKE_A))


def mask_bit(mask: int, row: int, col: int) -> bool:
    """True when pattern `mask` (0-7) inverts the module at (row, col)."""
    if mask == 0:
        return (row + col) % 2 == 0
    if mask == 1:
        return row % 2 == 0
    if mask == 2:
        return col % 3 == 0
    if mask == 3:
        return (row + col) % 3 == 0
    if mask == 4:
        return (row // 2 + col // 3) % 2 == 0
    if mask == 5:
        return (row * col) % 2 + (row * col) % 3 == 0
    if mask == 6:
        return ((row * col) % 2 + (row * col) % 3) % 2 == 0
    return ((row + col) % 2 + (row * col) % 3) % 2 == 0


def _run_penalty(line: list[bool]) -> int:
    score = 0
    run = 1
    for i in range(1, len(line)):
        if line[i] == line[i - 1]:
            run += 1
        else:
            if run >= 5:
                score += run - 2
            run = 1
    if run >= 5:
        score += run - 2
    return score


def _pattern_penalty(line: list[bool]) -> int:
    score = 0
    size = len(line)
    for i in range(size - 10):
        window = tuple(line[i:i + 11])
        if window in (_FINDER_LIKE_A, _FINDER_LIKE_B):
            score += 40
    return score


def penalty(matrix: list[list[bool]]) -> int:
    """Total penalty of rules 1-4 for a complete matrix."""
    size = len(matrix)
    score = 0
    columns = [[matrix[r][c] for r in range(size)] for c in range(size)]
    for line in matrix + columns:
        score += _run_penalty(line) + _pattern_penalty(line)
    for r in range(size - 1):
        for c in range(size - 1):
            if matrix[r][c] == matrix[r][c + 1] == matrix[r + 1][c] == matrix[r + 1][c + 1]:
                score += 3
    dark = sum(sum(1 for m in row if m) for row in matrix)
    total = size * size
    return score + abs(dark * 100 - total * 50) // (total * 5) * 10
