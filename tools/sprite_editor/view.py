import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

ZOOM = 8
_W = 32  # canvas pixel width
_H = 32  # canvas pixel height


class TileCanvas(Gtk.DrawingArea):
    """Cairo-based drawing area for the tile sheet at 8× zoom."""

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.active_color = 0
        self.set_size_request(_W * ZOOM, _H * ZOOM)
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK |
            Gdk.EventMask.BUTTON1_MOTION_MASK
        )
        self.connect('draw', self._on_draw)
        self.connect('button-press-event', self._on_click)
        self.connect('motion-notify-event', self._on_drag)

    def _on_draw(self, widget, cr):
        for y in range(_H):
            for x in range(_W):
                idx = self.model.get_pixel(x, y)
                if idx == 0:
                    # Transparent: checkerboard
                    light = ((x + y) % 2 == 0)
                    v = 0.75 if light else 0.55
                    cr.set_source_rgb(v, v, v)
                else:
                    r8, g8, b8 = self.model.palette.get_color_rgb888(idx)
                    cr.set_source_rgb(r8 / 255, g8 / 255, b8 / 255)
                cr.rectangle(x * ZOOM, y * ZOOM, ZOOM, ZOOM)
                cr.fill()

        # Tile grid overlay
        cr.set_source_rgba(0.2, 0.2, 0.2, 0.4)
        cr.set_line_width(1)
        tile_px = 8 * ZOOM
        for i in range(5):  # 0..4 (4 tiles = 5 lines)
            cr.move_to(i * tile_px, 0)
            cr.line_to(i * tile_px, _H * ZOOM)
            cr.stroke()
            cr.move_to(0, i * tile_px)
            cr.line_to(_W * ZOOM, i * tile_px)
            cr.stroke()

    def _paint_at(self, ex, ey):
        x = int(ex / ZOOM)
        y = int(ey / ZOOM)
        if 0 <= x < _W and 0 <= y < _H:
            self.model.set_pixel(x, y, self.active_color)
            self.queue_draw()

    def _on_click(self, widget, event):
        if event.button == 1:
            self._paint_at(event.x, event.y)

    def _on_drag(self, widget, event):
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            self._paint_at(event.x, event.y)


class PalettePanel(Gtk.Box):
    """Vertical panel: 4 color buttons + RGB sliders for the active color."""

    def __init__(self, model, canvas):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.model = model
        self.canvas = canvas
        self.active_index = 0
        self._build()

    def _build(self):
        lbl = Gtk.Label(label='<b>Palette</b>', use_markup=True)
        self.pack_start(lbl, False, False, 0)

        self.color_buttons = []
        for i in range(4):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            btn = Gtk.Button()
            btn.set_size_request(36, 36)
            btn.connect('clicked', self._select_color, i)
            self.color_buttons.append(btn)
            row.pack_start(btn, False, False, 0)
            if i == 0:
                row.pack_start(Gtk.Label(label='(transparent)'), False, False, 0)
            self.pack_start(row, False, False, 0)
            self._refresh_button(i)

        # RGB sliders
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.pack_start(sep, False, False, 4)

        self.sliders = {}
        for ch in ('R', 'G', 'B'):
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            box.pack_start(Gtk.Label(label=ch), False, False, 0)
            adj = Gtk.Adjustment(value=0, lower=0, upper=31,
                                 step_increment=1, page_increment=5,
                                 page_size=0)
            scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                              adjustment=adj)
            scale.set_digits(0)
            scale.set_hexpand(True)
            scale.connect('value-changed', self._on_slider, ch)
            self.sliders[ch] = scale
            box.pack_start(scale, True, True, 0)
            self.pack_start(box, False, False, 0)

        self._load_sliders()
        self._highlight_active()

    def _select_color(self, btn, index):
        self.active_index = index
        self.canvas.active_color = index
        self._load_sliders()
        self._highlight_active()

    def _load_sliders(self):
        r5, g5, b5 = self.model.palette.colors[self.active_index]
        self.sliders['R'].set_value(r5)
        self.sliders['G'].set_value(g5)
        self.sliders['B'].set_value(b5)

    def _on_slider(self, scale, channel):
        val = int(scale.get_value())
        r5, g5, b5 = self.model.palette.colors[self.active_index]
        if channel == 'R':
            r5 = val
        elif channel == 'G':
            g5 = val
        else:
            b5 = val
        self.model.palette.set_color(self.active_index, r5, g5, b5)
        self._refresh_button(self.active_index)
        self.canvas.queue_draw()

    def _refresh_button(self, index):
        r8, g8, b8 = self.model.palette.get_color_rgb888(index)
        rgba = Gdk.RGBA(r8 / 255, g8 / 255, b8 / 255, 1.0)
        self.color_buttons[index].override_background_color(
            Gtk.StateFlags.NORMAL, rgba)

    def _highlight_active(self):
        for i, btn in enumerate(self.color_buttons):
            relief = Gtk.ReliefStyle.NONE if i == self.active_index else Gtk.ReliefStyle.NORMAL
            btn.set_relief(relief)
