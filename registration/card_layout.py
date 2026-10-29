"""Photo movement limits that keep the fixed card mask completely covered."""
from math import floor


PHOTO_WIDTH = 638.76
PHOTO_HEIGHT = 829.64
MIN_PHOTO_SCALE = 1
MAX_PHOTO_SCALE = 3


def photo_movement_limits(scale):
    # Round inward to the editor's 0.1-unit step, avoiding gaps at the edges.
    return {
        'x': floor(PHOTO_WIDTH * (scale - 1) / 2 * 10 + 1e-9) / 10,
        'y': floor(PHOTO_HEIGHT * (scale - 1) / 2 * 10 + 1e-9) / 10,
    }


def constrain_photo_position(x, y, scale):
    scale = min(MAX_PHOTO_SCALE, max(MIN_PHOTO_SCALE, scale))
    limits = photo_movement_limits(scale)
    return {
        'x': min(limits['x'], max(-limits['x'], x)),
        'y': min(limits['y'], max(-limits['y'], y)),
        'scale': scale,
    }


def application_photo_position(application):
    return constrain_photo_position(
        application.card_photo_x, application.card_photo_y, application.card_photo_scale)
