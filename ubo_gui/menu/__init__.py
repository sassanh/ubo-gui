"""Implement a paginated menu.

The first page starts with a heading and its sub-heading.
Each item may have sub items, in that case activating this item will open a new menu
with its sub items.
Each item can optionally be styled differently.
"""
from __future__ import annotations

import math
import pathlib
import uuid
import warnings
from functools import cached_property
from typing import TYPE_CHECKING, Any, Callable, Sequence, cast

from headless_kivy_pi import HeadlessWidget
from kivy.app import Builder
from kivy.properties import AliasProperty, ListProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import (
    NoTransition,
    Screen,
    ScreenManager,
    SlideTransition,
    SwapTransition,
    TransitionBase,
)

from ubo_gui.page import PageWidget

from .constants import PAGE_SIZE
from .header_menu_page_widget import HeaderMenuPageWidget
from .normal_menu_page_widget import NormalMenuPageWidget
from .types import (
    ActionItem,
    ApplicationItem,
    HeadedMenu,
    Item,
    SubMenuItem,
    menu_items,
    menu_title,
)

if TYPE_CHECKING:
    from menu.types import Menu

    from ubo_gui.animated_slider import AnimatedSlider


class MenuWidget(BoxLayout):
    """Paginated menu."""

    _current_menu: Menu | None = None
    _current_menu_items: Sequence[Item]
    _current_application: PageWidget | None = None
    screen_manager: ScreenManager
    slider: AnimatedSlider
    cancel_items_subscription: Callable[[], None] | None = None

    def _handle_transition_progress(
        self: MenuWidget,
        transition: TransitionBase,
        progression: float,
    ) -> None:
        if progression is 0:  # noqa: F632 - float 0.0 is not accepted, we are looking for int 0
            HeadlessWidget.activate_high_fps_mode()
        transition.screen_out.opacity = 1 - progression
        transition.screen_in.opacity = progression

    def _handle_transition_complete(
        self: MenuWidget,
        transition: TransitionBase,
    ) -> None:
        transition.screen_out.opacity = 0
        transition.screen_in.opacity = 1
        HeadlessWidget.activate_low_fps_mode()

    def _setup_transition(self: MenuWidget, transition: TransitionBase) -> None:
        transition.bind(on_progress=self._handle_transition_progress)
        transition.bind(on_complete=self._handle_transition_complete)

    @cached_property
    def _no_transition(self: MenuWidget) -> NoTransition:
        transition = NoTransition()
        self._setup_transition(transition)
        return transition

    @cached_property
    def _slide_transition(self: MenuWidget) -> SlideTransition:
        transition = SlideTransition()
        self._setup_transition(transition)
        return transition

    @cached_property
    def _swap_transition(self: MenuWidget) -> SwapTransition:
        transition = SwapTransition()
        self._setup_transition(transition)
        return transition

    def __init__(self: MenuWidget, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize a `MenuWidget`."""
        self._current_menu_items = []
        super().__init__(**kwargs)

    def set_root_menu(self: MenuWidget, root_menu: Menu) -> None:
        """Set the root menu."""
        self.stack = []
        self.current_menu = root_menu
        self.screen_manager.switch_to(
            self.current_screen,
            transition=self._no_transition,
        )

    def get_depth(self: MenuWidget) -> int:
        """Return depth of the current screen."""
        return len(self.stack)

    def get_pages(self: MenuWidget) -> int:
        """Return the number of pages of the currently active menu."""
        if not self.current_menu:
            return 0
        if isinstance(self.current_menu, HeadedMenu):
            return math.ceil((len(self.current_menu_items) + 2) / 3)
        return math.ceil(len(self.current_menu_items) / 3)

    def get_title(self: MenuWidget) -> str | None:
        """Return the title of the currently active menu."""
        if self.current_application:
            return getattr(self.current_application, 'title', None)
        if self.current_menu:
            return menu_title(self.current_menu)
        return None

    def go_down(self: MenuWidget) -> None:
        """Go to the next page.

        If it is already the last page, rotate to the first page.
        """
        if self.current_application:
            self.current_application.go_down()
            return

        if len(self.current_menu_items) == 0:
            return
        self.page_index = (self.page_index + 1) % self.pages
        self.screen_manager.switch_to(
            self.current_screen,
            transition=self._slide_transition,
            direction='up',
        )

    def go_up(self: MenuWidget) -> None:
        """Go to the previous page.

        If it is already the first page, rotate to the last page.
        """
        if self.current_application:
            self.current_application.go_up()
            return

        if len(self.current_menu_items) == 0:
            return
        self.page_index = (self.page_index - 1) % self.pages
        self.screen_manager.switch_to(
            self.current_screen,
            transition=self._slide_transition,
            direction='down',
        )

    def select(self: MenuWidget, index: int) -> None:
        """Select one of the items currently visible on the screen.

        Parameters
        ----------
        index: `int`
            An integer number, can only take values greater than or equal to zero and
            less than `PAGE_SIZE`
        """
        if not self.screen_manager.current_screen:
            warnings.warn('`current_screen` is `None`', RuntimeWarning, stacklevel=1)
            return
        current_page = cast(PageWidget, self.screen_manager.current_screen)
        item = current_page.get_item(index)
        if not item:
            warnings.warn('Selected `item` is `None`', RuntimeWarning, stacklevel=1)
            return

        if isinstance(item, ActionItem):
            item = item.action()
            if not item:
                return
            if isinstance(item, type):
                application_instance = item(name=uuid.uuid4().hex)
                self.open_application(application_instance)
            else:
                self.push_menu()
                self.current_menu = item
                self.screen_manager.switch_to(
                    self.current_screen,
                    transition=self._slide_transition,
                    direction='left',
                )
        elif isinstance(item, ApplicationItem):
            application_instance = item.application(name=uuid.uuid4().hex)
            self.open_application(application_instance)
        elif isinstance(item, SubMenuItem):
            self.push_menu()
            self.current_menu = item.sub_menu
            if self.current_screen:
                self.screen_manager.switch_to(
                    self.current_screen,
                    transition=self._slide_transition,
                    direction='left',
                )

    def go_back(self: MenuWidget) -> None:
        """Go back to the previous menu."""
        if self.current_application and self.current_application.go_back():
            return
        HeadlessWidget.activate_high_fps_mode()
        self.pop_menu()

    def get_current_screen(self: MenuWidget) -> Screen | None:
        """Return the current screen page."""
        if self.current_application:
            return self.current_application

        if not self.current_menu:
            return None

        if self.page_index == 0 and isinstance(self.current_menu, HeadedMenu):
            return HeaderMenuPageWidget(
                self.current_menu_items[:1],
                self.current_menu.heading,
                self.current_menu.sub_heading,
                name=f'Page {self.get_depth()} 0',
            )

        offset = -(PAGE_SIZE - 1) if isinstance(self.current_menu, HeadedMenu) else 0
        return NormalMenuPageWidget(
            self.current_menu_items[
                self.page_index * 3 + offset : self.page_index * 3 + 3 + offset
            ],
            name=f'Page {self.get_depth()} 0',
        )

    def _get_current_screen(self: MenuWidget) -> Screen | None:
        """Return the current screen page."""
        return self.get_current_screen()

    def open_application(self: MenuWidget, application: PageWidget) -> None:
        """Open an application."""
        HeadlessWidget.activate_high_fps_mode()
        self.push_menu()
        self.current_application = application
        self.screen_manager.switch_to(
            self.current_screen,
            transition=self._swap_transition,
            duration=0.2,
            direction='left',
        )
        application.bind(on_close=self.close_application)

    def clean_application(self: MenuWidget, application: PageWidget) -> None:
        """Clean up the application bounds."""
        application.unbind(on_close=self.close_application)

    def close_application(self: MenuWidget, application: PageWidget) -> None:
        """Close an application after its `on_close` event is fired."""
        self.clean_application(application)
        if application is self.current_application:
            self.go_back()
        elif application in self.stack:
            self.stack.remove(application)

    def push_menu(self: MenuWidget) -> None:
        """Go one level deeper in the menu stack."""
        if self.current_menu:
            self.stack.append((self.current_menu, self.page_index))
        elif self.current_application:
            self.stack.append(self.current_application)
        self.page_index = 0

    def pop_menu(self: MenuWidget) -> None:
        """Come up one level from of the menu stack."""
        if self.depth == 0:
            return
        target = self.stack.pop()
        transition = self._slide_transition
        if isinstance(target, PageWidget):
            transition = self._swap_transition
            if self.current_application:
                self.clean_application(self.current_application)
            self.current_application = target
        else:
            if self.current_application:
                transition = self._swap_transition
            self.current_menu = target[0]
            self.page_index = target[1]
        self.screen_manager.switch_to(
            self.current_screen,
            transition=transition,
            direction='right',
        )

    def get_is_scrollbar_visible(self: MenuWidget) -> bool:
        """Return whether scroll-bar is needed or not."""
        return not self.current_application and self.pages > 1

    def get_current_application(self: MenuWidget) -> PageWidget | None:
        """Return current application."""
        return self._current_application

    def set_current_application(
        self: MenuWidget,
        application: PageWidget | None,
    ) -> bool:
        """Set current application."""
        self._current_application = application
        if application:
            self.current_menu = None

        return True

    def get_current_menu_items(self: MenuWidget) -> Sequence[Item] | None:
        """Return current menu items."""
        return self._current_menu_items

    def set_current_menu_items(self: MenuWidget, items: Sequence[Item]) -> bool:
        """Set current menu items."""
        self._current_menu_items = items
        return True

    def get_current_menu(self: MenuWidget) -> Menu | None:
        """Return the current menu."""
        return self._current_menu

    def set_current_menu(self: MenuWidget, menu: Menu | None) -> bool:
        """Set the current menu."""
        self._current_menu_items = menu_items(menu)
        if self.cancel_items_subscription:
            self.cancel_items_subscription()
            self.cancel_items_subscription = None
        if menu and hasattr(menu.items, 'subscribe'):

            def refresh_items(items: Sequence[Item]) -> None:
                self.current_menu_items = items
                self.screen_manager.switch_to(
                    self.current_screen,
                    transition=self._no_transition,
                )

            self.cancel_items_subscription = cast(Any, menu.items).subscribe(
                refresh_items,
            )

        self._current_menu = menu

        if not menu:
            self.page_index = 0
            return True

        self.current_application = None

        pages = self.get_pages()
        if self.page_index >= pages:
            self.page_index = max(self.pages - 1, 0)
        self.slider.value = pages - 1 - self.page_index
        return True

    def on_kv_post(self: MenuWidget, base_widget: Any) -> None:  # noqa: ANN401
        """Activate low fps mode when transition is done."""
        _ = base_widget
        self.screen_manager = cast(ScreenManager, self.ids.screen_manager)
        self.slider = self.ids.slider

    page_index = NumericProperty(0)
    stack: list[tuple[Menu, int] | PageWidget] = ListProperty()
    title = AliasProperty(
        getter=get_title,
        bind=['current_menu', 'current_application'],
        cache=True,
    )
    depth: int = AliasProperty(
        getter=get_depth,
        bind=['current_menu', 'current_application'],
        cache=True,
    )
    pages: int = AliasProperty(getter=get_pages, bind=['current_menu'], cache=True)
    current_application: PageWidget | None = AliasProperty(
        getter=get_current_application,
        setter=set_current_application,
        cache=True,
    )
    current_menu_items: Sequence[Item] = AliasProperty(
        getter=get_current_menu_items,
        setter=set_current_menu_items,
        bind=['current_menu'],
        cache=True,
    )
    current_menu: Menu | None = AliasProperty(
        getter=get_current_menu,
        setter=set_current_menu,
        cache=True,
    )
    current_screen: Menu | None = AliasProperty(
        getter=_get_current_screen,
        cache=True,
        bind=['page_index', 'current_application', 'current_menu_items'],
    )
    is_scrollbar_visible = AliasProperty(
        getter=get_is_scrollbar_visible,
        bind=['pages', 'current_application'],
        cache=True,
    )


Builder.load_file(
    pathlib.Path(__file__).parent.joinpath('menu.kv').resolve().as_posix(),
)
