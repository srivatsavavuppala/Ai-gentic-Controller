"""Track representation: a closed-loop centerline with constant width.

Pure math, no rendering -- this is what makes the training simulator fast
(thousands of steps/sec on CPU) compared to running a real racing game.
"""

import numpy as np


class Track:
    def __init__(self, centerline, width: float):
        """centerline: (N, 2) array of waypoints forming a closed loop.
        The last point connects back to the first automatically -- don't
        duplicate the start point at the end."""
        self.centerline = np.asarray(centerline, dtype=np.float64)
        self.width = width
        self.n_points = len(self.centerline)

        segment_vecs = np.roll(self.centerline, -1, axis=0) - self.centerline
        self.segment_lengths = np.linalg.norm(segment_vecs, axis=1)
        self.segment_dirs = segment_vecs / self.segment_lengths[:, None]
        self.segment_headings = np.arctan2(self.segment_dirs[:, 1], self.segment_dirs[:, 0])
        self.cumulative_length = np.concatenate([[0.0], np.cumsum(self.segment_lengths)[:-1]])
        self.total_length = float(np.sum(self.segment_lengths))

    def locate(self, position):
        """Returns (progress, lateral_offset, heading, segment_index) for (x, y).

        progress: arc length along the centerline to the nearest point.
        lateral_offset: signed distance from centerline (positive = left of
        the direction of travel, negative = right).
        heading: the track's direction of travel at the nearest segment.
        """
        p = np.asarray(position, dtype=np.float64)
        rel = p - self.centerline
        t = np.einsum("ij,ij->i", rel, self.segment_dirs)
        t = np.clip(t, 0.0, self.segment_lengths)
        closest = self.centerline + self.segment_dirs * t[:, None]
        dists = np.linalg.norm(p - closest, axis=1)
        seg = int(np.argmin(dists))

        direction = self.segment_dirs[seg]
        rel_seg = p - self.centerline[seg]
        lateral = direction[0] * rel_seg[1] - direction[1] * rel_seg[0]
        progress = self.cumulative_length[seg] + t[seg]
        heading = self.segment_headings[seg]
        return progress, float(lateral), float(heading), seg


def generate_oval_track(
    straight_length: float = 200.0,
    radius: float = 60.0,
    width: float = 12.0,
    points_per_curve: int = 24,
) -> Track:
    """A simple closed-loop oval: two straights joined by two semicircles.

    Good enough as the one track Phase 2 needs to prove the training loop
    works -- generating varied track shapes/scenarios is Simulation
    Manager's job in Phase 6.
    """
    half_straight = straight_length / 2.0
    points = [(-half_straight, -radius), (half_straight, -radius)]

    right_center = np.array([half_straight, 0.0])
    for a in np.linspace(-np.pi / 2, np.pi / 2, points_per_curve)[1:]:
        points.append((right_center[0] + radius * np.cos(a), right_center[1] + radius * np.sin(a)))

    points.append((-half_straight, radius))

    left_center = np.array([-half_straight, 0.0])
    for a in np.linspace(np.pi / 2, 3 * np.pi / 2, points_per_curve)[1:-1]:
        points.append((left_center[0] + radius * np.cos(a), left_center[1] + radius * np.sin(a)))

    return Track(np.array(points), width)
