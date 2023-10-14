from __future__ import annotations

import pathlib

from kivy.app import Builder
from kivy.properties import ColorProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout

from ubo.constants import PRIMARY_COLOR, SECONDARY_COLOR


class VolumeWidget(BoxLayout):
    value = NumericProperty(50)
    fill_color = ColorProperty(PRIMARY_COLOR)
    background_color = ColorProperty(SECONDARY_COLOR)


Builder.load_file(pathlib.Path(
    __file__).parent.joinpath('volume_widget.kv').resolve().as_posix())
