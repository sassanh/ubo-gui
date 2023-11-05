from pathlib import Path

from kivy.factory import Factory

ROOT_PATH = Path(__file__).parent
ASSETS_PATH = ROOT_PATH.joinpath('assets')
FONTS_PATH = ASSETS_PATH.joinpath('fonts')


Factory.register('AnimatedSlider', module='ubo_gui.animated_slider')
Factory.register('GaugeWidget', module='ubo_gui.gauge')
Factory.register('ItemWidget', module='ubo_gui.menu.item_widget')
Factory.register('MenuWidget', module='ubo_gui.menu')
Factory.register('NotificationWidget', module='ubo_gui.notification')
Factory.register('PromptWidget', module='ubo_gui.prompt')
Factory.register('VolumeWidget', module='ubo_gui.volume')
