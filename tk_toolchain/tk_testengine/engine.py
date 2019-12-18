# -*- coding: utf-8 -*-
# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import sys


class TestEngine(sgtk.platform.Engine):
    """
    Test engine.

    The engine will initialize a QApplication if possible right before
    applications start registering themselves so it looks as if they
    are running within a GUI environment.
    """

    def pre_app_init(self):
        """
        Called before apps and loaded.
        """
        # Since this method is called after Qt has been setup, but before
        # apps have been loaded, this makes it the perfect opportunity to
        # initialize QApplication so that apps can call has_ui and get a
        # positive answer back from the engine.
        QtGui = sgtk.platform.qt.QtGui
        try:
            q_app = sgtk.platform.qt.QtGui.QApplication.instance()
            self._q_app = q_app or sgtk.platform.qt.QtGui.QApplication(sys.argv)
        except Exception:
            # This will fail if Qt is not available.
            self._q_app = None

        if self._q_app:
            self._initialize_dark_look_and_feel()
            self._menu_bar = QtGui.QMenuBar()

    def post_app_init(self):
        self.__build_menu(self.context)

    def __build_menu(self, ctx):
        """
        Build the DCC menu. No-op of the engine doesn't implement the menu
        building interface.

        :param ctx: Current context.
        """

        # Copy the list of commands since we'll be doing edits to it.
        commands = self.commands.copy()

        # Extract favorites and context menu items from the list of commands
        # because they each go to a dedicated section.
        favorites = self._extract_favorites(commands)
        context_menu_items = self._extract_context_menu_items(commands)

        # Let the DCC do some further filtering. Certain DCCs, like Nuke, will add
        # shortcuts to apps in other sections of the UI.
        commands = getattr(None, "filter_menu_commands", lambda cmds, ctx: cmds)(
            self.commands, ctx
        )

        # Generates the first menu entry, the context menu.
        menus = [self._generate_context_menu(ctx, context_menu_items)]
        self._add_separator(menus)

        # Then follows all the favorites, if any.
        if favorites:
            self._add_separator(menus)
            menus.extend(favorites)
            self._add_separator(menus)

        # Finally we add the actions.
        self._add_menu_actions(menus, commands)

        # builds the menu
        self._build_menu(menus)

    def _add_menu_actions(self, menu, commands):
        """
        Add menu actions to a given menu.

        :param list menu: List of menu items to add to.
        :param commands: ``dict`` of commands to be added. See :meth:`Engine.commands` for more information.
        """
        commands_per_app = {}

        # First, we need to group commands per application so we can create a sub-menu
        # for each.
        for name, details in commands.items():
            # Only apps show up under their name. Framework commands show up as Other Items.
            # FIXME: Why??? This was standard practice in the engines but documented nowhere.
            app = details["properties"].get("app")
            try:
                app_name = app.display_name
            except AttributeError:
                app_name = "Other Items"
            commands_per_app.setdefault(app_name, {})[name] = details

        # For each app
        for app_name in sorted(commands_per_app):
            # If there's only a single command for that app, create a single menu item.
            if len(commands_per_app[app_name]) == 1:
                name, details = list(commands_per_app[app_name].items()).pop()
                self._add_command_to_menu(menu, name, details)
            else:
                # If there's more than one, group them under a menu named after
                # the app name.
                app_menu = {"type": "menu", "title": app_name, "children": []}
                menu.append(app_menu)
                for name, details in commands_per_app[app_name].items():
                    self._add_command_to_menu(app_menu["children"], name, details)

    def _extract_favorites(self, commands):
        """
        Extract favorites from the list of commands.

        :param commands: ``dict`` of commands. See :meth:`Engine.commands` for more information.

        :returns: List of menu items to create.
        :rtype: list
        """
        favorites = []

        for fav in self.get_setting("menu_favourites", []):
            app_instance_name = fav["app_instance"]
            menu_name = fav["name"]

            # For each of the favorite in the list of commands.
            for name, details in list(commands.items()):
                # If the favorite matches the current app.
                if (
                    self._get_app_instance_name(details) == app_instance_name
                    and name == menu_name
                ):
                    self._add_command_to_menu(favorites, name, details)
                    del commands[name]
                    break
            else:
                # No match was made, log a warning.
                self.logger.warning(
                    "Could not add favorite app %s:%s", app_instance_name, menu_name
                )

        return favorites

    def _extract_context_menu_items(self, commands):
        """
        Extract context menu items from the list of commands.

        :param commands: ``dict`` of commands. See :meth:`Engine.commands` for more information.

        :returns: List of menu items to create.
        :rtype: list
        """
        context_menu_items = []

        #
        for name in sorted(commands):
            details = commands[name]
            if details["properties"].get("type") == "context_menu":
                self._add_command_to_menu(context_menu_items, name, details)
                del commands[name]

        return context_menu_items

    def _get_app_instance_name(self, details):
        """
        Get the app instance name for a given application details.

        :param details: Details object taken from :meth:`Engine.commands`.

        :returns: Name of the application instance or ``None`` if the application
            instance was not found.
        """
        app = details["properties"].get("app")
        if app is None:
            return None

        for (app_instance_name, app_instance_obj) in self.apps.items():
            if app == app_instance_obj:
                return app_instance_name

        return None

    def _add_command_to_menu(self, menu, name, details):
        """
        Add a command to the menu.

        :param menu: List of children to add to.
        :param name: Name of the command.
        :param details: Details for a command.
        """
        menu.append(
            self._create_menu_item(
                name, details["callback"], details["properties"].get("icon")
            )
        )

    def _create_menu_item(self, title, callback, icon=None):
        """
        Create a menu item ``dict``.

        :param title: Title of the menu.
        :param callback: Callable to invoke when the menu is selected.
        :param icon: Icon to display next to the menu item.
        """
        return {"type": "action", "title": title, "icon": icon, "callback": callback}

    def _generate_context_menu(self, ctx, context_menu_commands):
        """
        Create the context menu.

        :param ctx: Current context.
        :param context_menu_commands: Commands to add to the context menu.
        """
        items = []
        context_menu = {"type": "menu", "title": str(ctx), "children": items}

        items.append(self._create_menu_item("Jump to Shotgun", self._jump_to_sg))
        if ctx.filesystem_locations:
            items.append(
                self._create_menu_item("Jump to File System", self._jump_to_fs)
            )
        self._add_separator(items)
        items.extend(context_menu_commands)
        return context_menu

    def _add_separator(self, menu):
        """
        Add a separator to the menu.

        :param list: List of menu items.
        """
        menu.append({"type": "separator"})

    def _jump_to_sg(self):
        """
        Jump from a context to Shotgun.
        """
        url = self.context.shotgun_url
        sgtk.platform.qt.QtGui.QDesktopServices.openUrl(
            sgtk.platform.qt.QtCore.QUrl(url)
        )

    def _jump_to_fs(self):
        """
        Jump from a context to the filesystem.
        """
        paths = self.context.filesystem_locations
        for disk_location in paths:
            if not sgtk.platform.qt.QtGui.QDesktopServices.openUrl(
                "file://{0}".format(disk_location).replace("\\", "/")
            ):
                self.logging.error("Failed to open '%s'!", disk_location)

    def _build_menu(self, menu_items, parent_menu=None):
        """
        DCC
        """
        if parent_menu is None:
            parent_menu = self._menu_bar.addMenu("Shotgun")

        for item in menu_items:
            if item["type"] == "separator":
                parent_menu.addSeparator()
            elif item["type"] == "menu":
                sub_menu = parent_menu.addMenu(item["title"])
                self._build_menu(item["children"], sub_menu)
            else:
                action = parent_menu.addAction(item["title"])
                action.triggered.connect(item["callback"])
                if item["icon"]:
                    action.setIcon(sgtk.platform.qt.QtGui.QIcon(item["icon"]))

    @property
    def q_app(self):
        """
        The QtGui.QApplication instance, if available.
        """
        return self._q_app

    def _emit_log_message(self, handler, record):
        """
        Print any log message to the console.
        """
        print(handler.format(record))

    def show_dialog(self, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a dialog.

        See sgtk.platform.Engine documentation's for more details.
        """
        dialog = super(self.__class__, self).show_dialog(
            title, bundle, widget_class, *args, **kwargs
        )
        # Forces the dialog to show on top of other dialogs when using PySide 1
        dialog.window().raise_()
        dialog.window().show()
        return dialog
