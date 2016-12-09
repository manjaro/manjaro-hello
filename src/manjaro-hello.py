#!/usr/bin/env python3

import gettext
import gi
import json
import locale
import os
import subprocess
import sys
import webbrowser
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

class ManjaroHello():
    def __init__(self):
        # App vars
        self.app = "manjaro-hello"
        self.default_locale = "en_US"
        self.sys_locale = locale.getlocale()[0]
        self.social_urls = {
            "google+": "https://plus.google.com/118244873957924966264",
            "facebook": "https://www.facebook.com/ManjaroLinux",
            "twitter": "https://twitter.com/ManjaroLinux",
            "reddit": "https://www.reddit.com/r/ManjaroLinux"
        }

        # Path vars
        config_path = os.path.expanduser("~") + "/.config/"
        #share_path = "/usr/share/"
        self.preferences_path = config_path + self.app + ".json"
        self.desktop_path = os.getcwd() + "/" + self.app + ".desktop" # later use share_path
        self.autostart_path = config_path + "autostart/" + self.app + ".desktop"
        self.icon_path = "./" + self.app + ".png" # later use share_path
        self.locale_path = "locale"

        # Load preferences
        self.preferences = self.get_preferences()
        if not self.preferences:
            self.preferences = {
                "autostart": os.path.isfile(self.autostart_path),
                "locale": None
            }

        # Init translation
        locales = os.listdir(self.locale_path)
        locales.append(self.default_locale)
        if self.preferences["locale"] not in locales:
            if self.sys_locale in locales:
                self.preferences["locale"] = self.sys_locale
            else:
                self.preferences["locale"] = self.default_locale

        if self.preferences["locale"] != self.default_locale:
            locale.bindtextdomain(self.app, self.locale_path)
            gettext.bindtextdomain(self.app, self.locale_path)
            gettext.textdomain(self.app)
            lang = gettext.translation(self.app, localedir=self.locale_path, languages=[self.preferences["locale"]])
            lang.install()

        # Save new locale
        self.save_preferences()

        # Load system infos
        self.infos = get_infos()

        # Init window
        self.builder = Gtk.Builder()
        self.builder.set_translation_domain(self.app)
        self.builder.add_from_file("manjaro-hello.glade")
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("window")

        # Change selected language
        self.builder.get_object("languages").set_active_id(self.preferences["locale"]);
        self.builder.get_object("languages").connect("changed", self.on_languages_changed)

        # Set window subtitle
        if self.infos["codename"] and self.infos["release"]:
            self.builder.get_object("headerbar").props.subtitle = self.infos["codename"] + " " + self.infos["release"] + " "
        self.builder.get_object("headerbar").props.subtitle += self.infos["arch"]

        # Set autostart switcher state
        self.builder.get_object("autostart").set_active(self.preferences["autostart"])

        # Init pages
        for page in ("readme", "release", "involved"):
            self.builder.get_object(page + "text").set_markup(self.read_page(page))

        # Live systems
        if self.infos["live"]:
            can_install = False
            if os.path.isfile("/usr/bin/calamares"):
                self.builder.get_object("installgui").set_visible(True)
                can_install = True
            if os.path.isfile("/usr/bin/cli-installer"):
                self.builder.get_object("installcli").set_visible(True)
                can_install = True
            if can_install:
                self.builder.get_object("installlabel").set_visible(True)

        self.window.show();

    def change_autostart(self, state):
        if state and not os.path.isfile(self.autostart_path):
            try:
                os.symlink(self.desktop_path, self.autostart_path)
            except OSError as e:
                print(e)
        elif not state and os.path.isfile(self.autostart_path):
            try:
                os.unlink(self.autostart_path)
            except OSError as e:
                print(e)
        self.preferences["autostart"] = state
        self.save_preferences()

    def save_preferences(self):
        try:
            with open(self.preferences_path, "w") as f:
                json.dump(self.preferences, f)
        except OSError as e:
            print(e)

    def get_preferences(self):
        try:
            with open(self.preferences_path, "r") as f:
                return json.load(f)
        except OSError as e:
            return None

    def read_page(self, name):
        filename = "pages/{}/{}".format(self.preferences["locale"], name)
        if not os.path.isfile(filename):
            filename = "pages/{}/{}".format(self.default_locale, name)
        try:
            with open(filename, "r") as f:
                return f.read()
        except OSError as e:
            return None

    # Handlers
    def on_languages_changed(self, combobox):
        self.preferences["locale"] = combobox.get_active_id()
        self.save_preferences()
        os.execv(sys.executable, ['python'] + sys.argv)

    def on_about_clicked(self, btn):
        dialog = self.builder.get_object("aboutdialog")
        dialog.set_transient_for(self.window)
        dialog.run()
        dialog.hide()

    def on_welcome_btn_clicked(self, btn):
        name = btn.get_name()
        if name == "readmebtn":
            self.builder.get_object("stack").set_visible_child(self.builder.get_object("documentation"))
            self.builder.get_object("documentation").set_current_page(0)
        elif name == "releasebtn":
            self.builder.get_object("stack").set_visible_child(self.builder.get_object("documentation"))
            self.builder.get_object("documentation").set_current_page(1)
        elif name == "involvedbtn":
            self.builder.get_object("stack").set_visible_child(self.builder.get_object("project"))
            self.builder.get_object("project").set_current_page(0)
        elif name == "installgui":
            subprocess.call(["sudo", "-E", "calamares"])
        elif name == "installcli":
            subprocess.call(["sudo cli-installer"])

    def on_social_pressed(self, eventbox, _):
        webbrowser.open_new_tab(self.social_urls[eventbox.get_name()])

    def on_autostart_switched(self, switch, _):
        autostart = True if switch.get_active() else False
        self.change_autostart(autostart)

    def on_delete_window(self, *args):
        Gtk.main_quit(*args)

def get_infos():
    lsb = get_lsb_information()
    infos = {}
    infos["codename"] = lsb.get("CODENAME", None)
    infos["release"] = lsb.get("RELEASE", None)
    infos["arch"] = "64-bits" if sys.maxsize > 2**32 else "32-bits"
    infos["live"] = os.path.exists("/bootmnt/manjaro") or os.path.exists("/run/miso/bootmnt/manjaro")

    return infos

def get_lsb_information():
    lsb = {}
    try:
        with open("/etc/lsb-release") as lsb_file:
            for line in lsb_file:
                if "=" in line:
                    var, arg = line.rstrip().split("=")
                    if var.startswith("DISTRIB_"):
                        var = var[8:]
                    if arg.startswith("\"") and arg.endswith("\""):
                        arg = arg[1:-1]
                    if arg:
                        lsb[var] = arg
    except OSError as e:
        print(e)

    return lsb

if __name__ == "__main__":
    ManjaroHello()
    Gtk.main()
