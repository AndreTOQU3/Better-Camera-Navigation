import math


def mouse_look_delta(dx, dy, sensitivity, invert_x=False, invert_y=False):
    """Mouse-look delta: right drag turns right; upward drag looks upward."""
    x_sign = 1.0 if invert_x else -1.0
    y_sign = -1.0 if invert_y else 1.0
    return dx * sensitivity * x_sign, dy * sensitivity * y_sign


def orbit_delta(dx, dy, sensitivity, invert_x=False, invert_y=False):
    """T6Viewer/Mine-imator orbit uses the same corrected mouse directions."""
    return mouse_look_delta(dx, dy, sensitivity, invert_x, invert_y)


def mouse_rotation_delta(dx, dy, sensitivity, invert_x=False, invert_y=False):
    # Backward-compatible alias for v1 settings/tests.
    return mouse_look_delta(dx, dy, sensitivity, invert_x, invert_y)


def pan_delta(dx, dy, sensitivity, invert_x=False, invert_y=False):
    x_sign = -1.0 if invert_x else 1.0
    y_sign = -1.0 if invert_y else 1.0
    return dx * sensitivity * x_sign, dy * sensitivity * y_sign


def vertical_key_axis(pressed):
    """Vertical movement mapping: Q down, E up."""
    axis = 0.0
    if 'Q' in pressed:
        axis -= 1.0
    if 'E' in pressed:
        axis += 1.0
    return axis


def movement_speed_multiplier(space=False, shift=False, fast_multiplier=4.0, slow_multiplier=0.25):
    """Current T6Viewer overlay: Space faster, Shift slower."""
    multiplier = 1.0
    if space:
        multiplier *= fast_multiplier
    if shift:
        multiplier *= slow_multiplier
    return multiplier


def speed_with_modifiers(base_speed, shift=False, fast_multiplier=4.0):
    # Backward-compatible helper from v1.
    return base_speed * (fast_multiplier if shift else 1.0)


def zoom_distance(distance, wheel_steps, factor=1.18, minimum=0.01, maximum=1000000.0):
    if wheel_steps > 0:
        distance /= factor ** wheel_steps
    elif wheel_steps < 0:
        distance *= factor ** (-wheel_steps)
    return max(minimum, min(maximum, distance))


def adjust_speed(speed, wheel_steps, factor=1.25, minimum=0.01, maximum=1000.0):
    if wheel_steps > 0:
        speed *= factor ** wheel_steps
    elif wheel_steps < 0:
        speed /= factor ** (-wheel_steps)
    return max(minimum, min(maximum, speed))


def clamp_pitch(pitch, limit_degrees=89.0):
    limit = math.radians(limit_degrees)
    return max(-limit, min(limit, pitch))


def toggle_shortcut_allowed(context_mode):
    """Keep Blender's native Ctrl+F Face menu available in mesh Edit Mode."""
    return context_mode != 'EDIT_MESH'


def mouse_button_action(button, shift=False):
    """Return the Mine-imator navigation action for a mouse press."""
    if button == 'MIDDLEMOUSE':
        return 'NATIVE_PAN'
    if button == 'LEFTMOUSE':
        return 'PAN' if shift else 'ORBIT'
    if button == 'RIGHTMOUSE':
        return 'FREELOOK'
    return None
