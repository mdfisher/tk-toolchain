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
        context_menu = self._generate_context_menu(ctx)
        menus = [
            {"type": "menu", "title": str(ctx), "children": context_menu},
            self._create_separator(),
        ]

        commands = getattr(None, "filter_menu_commands", lambda cmds, ctx: cmds)(
            self.commands, ctx
        )

        for name, details in commands.items():
            if details["properties"].get("type") == "context_menu":
                context_menu.append(
                    self._create_menu_item(
                        name, details["callback"], details["properties"].get("icon")
                    )
                )
            # app = details.get("app")
            # try:
            #     app_name = self._app.display_name
            # except AttributeError:
            #     app_name = None

        self._build_menu(menus)

        # menu.extend(self._generate_favorites(commands))

    def _build_menu(self, menu_items, parent_menu=None):
        if parent_menu is None:
            parent_menu = self._menu_bar.addMenu("Shotgun")

        for item in menu_items:
            if item["type"] == "separator":
                parent_menu.addSeparator()
            elif item["type"] == "menu":
                sub_menu = parent_menu.addMenu(item["title"])
                self._build_menu(item["children"], sub_menu)
            else:
                parent_menu.addAction(item["title"]).triggered.connect(item["callback"])

    # def _generate_favorites(self, commands):

    #     favorites = []
    #     for fav in self.engine.get_setting("menu_favourites", []):
    #         app_instance_name = fav["app_instance"]
    #         menu_name = fav["name"]

    #         # Scan through all menu items.
    #         for name, details in commands.items():
    #              if details["app"] and details["app"].instance_name == app_instance_name and name == menu_name:
    #                  favorites =
    #     menu_handle.addSeparator()

    def _generate_context_menu(self, ctx):
        context_menu = [self._create_menu_item("Jump to Shotgun", self._jump_to_sg)]
        if ctx.filesystem_locations:
            context_menu.append(
                self._create_menu_item("Jump to File System", self._jump_to_fs)
            )

        context_menu.append(self._create_separator())
        return context_menu

    def _create_separator(self):
        return {"type": "separator"}

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

    def _create_menu_item(self, title, callback, icon=None):
        return {"type": "action", "title": title, "icon": icon, "callback": callback}

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
