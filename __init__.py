bl_info = {
    "name": "Better Camera Navigation",
    "author": "OpenAI",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "3D Viewport > N > Better Camera",
    "description": "Better camera and viewport navigation",
    "category": "3D View",
}

import math
import bpy
from bpy.props import BoolProperty, FloatProperty, PointerProperty
from bpy.types import Operator, Panel, PropertyGroup
from mathutils import Quaternion, Vector

from .nav_math import (
    mouse_look_delta,
    orbit_delta,
    pan_delta,
    vertical_key_axis,
    movement_speed_multiplier,
    zoom_distance,
    toggle_shortcut_allowed,
    mouse_button_action,
)


ADDON_KEYMAPS = []
_RUNNING = False


def _tag_redraw(area):
    if area:
        area.tag_redraw()


def _active_region_3d(context):
    if context.area and context.area.type == 'VIEW_3D' and context.space_data:
        return context.space_data.region_3d
    return None


def _camera_mode(context, settings):
    rv3d = _active_region_3d(context)
    return bool(
        settings.control_camera_in_camera_view
        and rv3d
        and rv3d.view_perspective == 'CAMERA'
        and context.scene.camera
    )


def _orientation_quaternion(context, settings):
    if _camera_mode(context, settings):
        return context.scene.camera.matrix_world.to_quaternion()
    rv3d = _active_region_3d(context)
    return rv3d.view_rotation.copy() if rv3d else Quaternion()


def _move_target(context, settings, delta):
    if delta.length_squared == 0:
        return

    if _camera_mode(context, settings):
        camera = context.scene.camera
        camera.location += delta
    else:
        rv3d = _active_region_3d(context)
        if rv3d:
            rv3d.view_location += delta


def _apply_rotation(q, yaw, pitch):
    world_yaw = Quaternion(Vector((0.0, 0.0, 1.0)), yaw)
    local_pitch = Quaternion(Vector((1.0, 0.0, 0.0)), pitch)
    return (world_yaw @ q @ local_pitch).normalized()


def _viewport_eye(rv3d):
    forward = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
    return rv3d.view_location - forward * rv3d.view_distance


def _freelook_target(context, settings, yaw, pitch):
    if yaw == 0.0 and pitch == 0.0:
        return

    if _camera_mode(context, settings):
        camera = context.scene.camera
        q = _apply_rotation(camera.matrix_world.to_quaternion(), yaw, pitch)
        camera.rotation_mode = 'QUATERNION'
        camera.rotation_quaternion = q
        return

    rv3d = _active_region_3d(context)
    if not rv3d:
        return

    # Blender normally rotates around view_location. T6Viewer RMB is freelook,
    # so preserve the actual eye position and move the hidden pivot instead.
    eye = _viewport_eye(rv3d)
    q = _apply_rotation(rv3d.view_rotation.copy(), yaw, pitch)
    forward = q @ Vector((0.0, 0.0, -1.0))
    rv3d.view_rotation = q
    rv3d.view_location = eye + forward * rv3d.view_distance


def _orbit_target(context, settings, yaw, pitch):
    if yaw == 0.0 and pitch == 0.0:
        return

    if _camera_mode(context, settings):
        camera = context.scene.camera
        rv3d = _active_region_3d(context)
        distance = max(rv3d.view_distance if rv3d else 10.0, 0.01)
        old_q = camera.matrix_world.to_quaternion()
        old_forward = old_q @ Vector((0.0, 0.0, -1.0))
        pivot = camera.location + old_forward * distance
        q = _apply_rotation(old_q, yaw, pitch)
        new_forward = q @ Vector((0.0, 0.0, -1.0))
        camera.rotation_mode = 'QUATERNION'
        camera.rotation_quaternion = q
        camera.location = pivot - new_forward * distance
        return

    rv3d = _active_region_3d(context)
    if rv3d:
        rv3d.view_rotation = _apply_rotation(rv3d.view_rotation.copy(), yaw, pitch)


def _pan_target(context, settings, horizontal, vertical):
    q = _orientation_quaternion(context, settings)
    right = q @ Vector((1.0, 0.0, 0.0))
    up = q @ Vector((0.0, 1.0, 0.0))
    # Grab-style pan: the scene follows the mouse, so the camera moves opposite.
    delta = -(right * horizontal + up * vertical)
    _move_target(context, settings, delta)


def _zoom_target(context, settings, wheel_steps):
    rv3d = _active_region_3d(context)
    if _camera_mode(context, settings):
        q = _orientation_quaternion(context, settings)
        forward = q @ Vector((0.0, 0.0, -1.0))
        amount = settings.movement_speed * 0.35 * wheel_steps
        _move_target(context, settings, forward * amount)
    elif rv3d:
        rv3d.view_distance = zoom_distance(rv3d.view_distance, wheel_steps)


class MineimatorNavSettings(PropertyGroup):
    enabled: BoolProperty(
        name="Enabled",
        default=False,
        description="Enable Better Camera Navigation in this 3D Viewport",
    )
    movement_speed: FloatProperty(
        name="Move Speed",
        default=4.0,
        min=0.01,
        max=1000.0,
        soft_max=100.0,
    )
    mouse_sensitivity: FloatProperty(
        name="Look Sensitivity",
        default=0.004,
        min=0.0001,
        max=0.05,
        precision=4,
    )
    pan_sensitivity: FloatProperty(
        name="Pan Sensitivity",
        default=0.01,
        min=0.0001,
        max=1.0,
        precision=4,
    )
    fast_multiplier: FloatProperty(
        name="Space Multiplier",
        default=4.0,
        min=1.0,
        max=20.0,
    )
    slow_multiplier: FloatProperty(
        name="Shift Multiplier",
        default=0.25,
        min=0.05,
        max=1.0,
    )
    invert_x: BoolProperty(name="Invert Horizontal", default=False)
    invert_y: BoolProperty(name="Invert Vertical", default=False)
    control_camera_in_camera_view: BoolProperty(
        name="Move Camera in Camera View",
        default=True,
        description="When in Numpad 0 camera view, move the actual scene camera",
    )


class VIEW3D_OT_mineimator_navigation(Operator):
    bl_idname = "view3d.mineimator_navigation"
    bl_label = "Better Camera Navigation"
    bl_description = "Start or stop Better Camera Navigation"
    bl_options = {'REGISTER'}

    _timer = None
    _last_mouse_x = 0
    _last_mouse_y = 0
    _look_drag = False
    _orbit_drag = False
    _pan_drag = False
    _pressed = None
    _area = None
    _last_time = 0.0

    def invoke(self, context, event):
        global _RUNNING

        if context.area is None or context.area.type != 'VIEW_3D':
            self.report({'WARNING'}, "Run this from a 3D Viewport")
            return {'CANCELLED'}

        settings = context.scene.mineimator_nav
        if _RUNNING:
            settings.enabled = False
            return {'FINISHED'}

        settings.enabled = True
        _RUNNING = True
        self._area = context.area
        self._pressed = set()
        self._last_mouse_x = event.mouse_x
        self._last_mouse_y = event.mouse_y

        wm = context.window_manager
        self._timer = wm.event_timer_add(1.0 / 120.0, window=context.window)
        wm.modal_handler_add(self)
        _tag_redraw(self._area)
        return {'RUNNING_MODAL'}

    def _stop(self, context):
        global _RUNNING
        settings = context.scene.mineimator_nav
        settings.enabled = False
        _RUNNING = False
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None
        self._pressed.clear()
        _tag_redraw(self._area)
        return {'CANCELLED'}

    def modal(self, context, event):
        settings = context.scene.mineimator_nav
        if not settings.enabled:
            return self._stop(context)

        # Keep Blender usable outside the viewport where the operator was started.
        if context.area != self._area:
            return {'PASS_THROUGH'}

        if event.type == 'ESC' and event.value == 'PRESS':
            return self._stop(context)

        if event.type in {'W', 'A', 'S', 'D', 'Q', 'E', 'SPACE', 'LEFT_SHIFT', 'RIGHT_SHIFT'}:
            if event.value == 'PRESS':
                self._pressed.add(event.type)
            elif event.value == 'RELEASE':
                self._pressed.discard(event.type)
            return {'RUNNING_MODAL'}

        if event.type == 'RIGHTMOUSE':
            if event.value == 'PRESS':
                self._look_drag = True
                self._last_mouse_x = event.mouse_x
                self._last_mouse_y = event.mouse_y
            elif event.value == 'RELEASE':
                self._look_drag = False
            return {'RUNNING_MODAL'}

        if event.type == 'MIDDLEMOUSE' and event.value == 'PRESS':
            # Exact Blender Shift+MMB behavior: invoke Blender's own View Pan operator.
            if mouse_button_action(event.type, shift=event.shift) == 'NATIVE_PAN':
                bpy.ops.view3d.move('INVOKE_DEFAULT')
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE':
            if event.value == 'PRESS':
                shift_held = ('LEFT_SHIFT' in self._pressed or 'RIGHT_SHIFT' in self._pressed or event.shift)
                action = mouse_button_action(event.type, shift=shift_held)
                self._pan_drag = action == 'PAN'
                self._orbit_drag = action == 'ORBIT'
                self._last_mouse_x = event.mouse_x
                self._last_mouse_y = event.mouse_y
            elif event.value == 'RELEASE':
                self._orbit_drag = False
                self._pan_drag = False
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE' and (self._look_drag or self._orbit_drag or self._pan_drag):
            dx = event.mouse_x - self._last_mouse_x
            dy = event.mouse_y - self._last_mouse_y
            self._last_mouse_x = event.mouse_x
            self._last_mouse_y = event.mouse_y

            if self._look_drag:
                yaw, pitch = mouse_look_delta(
                    dx, dy, settings.mouse_sensitivity, settings.invert_x, settings.invert_y
                )
                _freelook_target(context, settings, yaw, pitch)

            if self._orbit_drag:
                yaw, pitch = orbit_delta(
                    dx, dy, settings.mouse_sensitivity, settings.invert_x, settings.invert_y
                )
                _orbit_target(context, settings, yaw, pitch)

            if self._pan_drag:
                horizontal, vertical = pan_delta(
                    dx, dy, settings.pan_sensitivity, settings.invert_x, settings.invert_y
                )
                _pan_target(context, settings, horizontal, vertical)

            _tag_redraw(self._area)
            return {'RUNNING_MODAL'}

        if event.type in {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'} and event.value == 'PRESS':
            step = 1 if event.type == 'WHEELUPMOUSE' else -1
            _zoom_target(context, settings, step)
            _tag_redraw(self._area)
            return {'RUNNING_MODAL'}

        if event.type == 'TIMER':
            q = _orientation_quaternion(context, settings)
            forward = q @ Vector((0.0, 0.0, -1.0))
            right = q @ Vector((1.0, 0.0, 0.0))
            world_up = Vector((0.0, 0.0, 1.0))

            direction = Vector((0.0, 0.0, 0.0))
            if 'W' in self._pressed:
                direction += forward
            if 'S' in self._pressed:
                direction -= forward
            if 'D' in self._pressed:
                direction += right
            if 'A' in self._pressed:
                direction -= right
            direction += world_up * vertical_key_axis(self._pressed)

            if direction.length_squared > 0.0:
                direction.normalize()
                space = 'SPACE' in self._pressed
                shift = 'LEFT_SHIFT' in self._pressed or 'RIGHT_SHIFT' in self._pressed
                multiplier = movement_speed_multiplier(
                    space=space,
                    shift=shift,
                    fast_multiplier=settings.fast_multiplier,
                    slow_multiplier=settings.slow_multiplier,
                )
                speed = settings.movement_speed * multiplier
                _move_target(context, settings, direction * speed * (1.0 / 120.0))
                _tag_redraw(self._area)

            return {'RUNNING_MODAL'}

        # Block conflicting navigation only while enabled; most other Blender shortcuts pass through.
        return {'PASS_THROUGH'}


class VIEW3D_OT_mineimator_toggle(Operator):
    bl_idname = "view3d.mineimator_toggle"
    bl_label = "Toggle Better Camera Navigation"

    @classmethod
    def poll(cls, context):
        return bool(
            context.area
            and context.area.type == 'VIEW_3D'
            and toggle_shortcut_allowed(context.mode)
        )

    def execute(self, context):
        settings = context.scene.mineimator_nav
        if settings.enabled:
            settings.enabled = False
            return {'FINISHED'}
        bpy.ops.view3d.mineimator_navigation('INVOKE_DEFAULT')
        return {'FINISHED'}


class VIEW3D_PT_mineimator_camera(Panel):
    bl_label = "Better Camera Navigation"
    bl_idname = "VIEW3D_PT_mineimator_camera"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Better Camera"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.mineimator_nav

        row = layout.row()
        row.scale_y = 1.4
        row.operator(
            "view3d.mineimator_toggle",
            text="Disable Navigation" if settings.enabled else "Enable Navigation",
            icon='PAUSE' if settings.enabled else 'PLAY',
        )

        status = layout.box()
        status.label(text="ACTIVE" if settings.enabled else "INACTIVE", icon='CHECKMARK' if settings.enabled else 'CANCEL')
        if settings.enabled:
            status.label(text="ESC also disables navigation")

        col = layout.column(align=True)
        col.label(text="Movement")
        col.prop(settings, "movement_speed")
        col.prop(settings, "fast_multiplier")
        col.prop(settings, "slow_multiplier")
        col.prop(settings, "control_camera_in_camera_view")

        col = layout.column(align=True)
        col.label(text="Mouse")
        col.prop(settings, "mouse_sensitivity")
        col.prop(settings, "pan_sensitivity")
        col.prop(settings, "invert_x")
        col.prop(settings, "invert_y")

        help_box = layout.box()
        help_box.label(text="RMB drag: Walk / Look")
        help_box.label(text="LMB drag: Orbit")
        help_box.label(text="Shift + LMB: Pan")
        help_box.label(text="MMB: Blender Pan")
        help_box.label(text="WASD: Move")
        help_box.label(text="Q / E: Down / Up")
        help_box.label(text="Space: Faster")
        help_box.label(text="Shift: Slower")
        help_box.label(text="Wheel: Zoom")
        help_box.label(text="Ctrl+F: Toggle")


CLASSES = (
    MineimatorNavSettings,
    VIEW3D_OT_mineimator_navigation,
    VIEW3D_OT_mineimator_toggle,
    VIEW3D_PT_mineimator_camera,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.mineimator_nav = PointerProperty(type=MineimatorNavSettings)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new('view3d.mineimator_toggle', type='F', value='PRESS', ctrl=True)
        ADDON_KEYMAPS.append((km, kmi))


def unregister():
    global _RUNNING
    _RUNNING = False

    for km, kmi in ADDON_KEYMAPS:
        km.keymap_items.remove(kmi)
    ADDON_KEYMAPS.clear()

    if hasattr(bpy.types.Scene, 'mineimator_nav'):
        del bpy.types.Scene.mineimator_nav

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
