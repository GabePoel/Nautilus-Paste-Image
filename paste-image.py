#!/usr/bin/python3

import os
from gi.repository import Nautilus, GObject, Gio, Gtk
from urllib.parse import urlparse


def detect_x11():
    """
    Determines if x11 or Wayland is used. This prevents crashes when Nautilus
    copies files on systems running x11.
    """
    if detect_silverblue():
        return True
    s = "loginctl show-session $(awk '/tty/ {print $1}' <(loginctl)) -p Type"
    s += " | awk -F= '{print $2}'"
    result = os.popen(s).read()
    return 'x' in result


def get_image_formats():
    """
    Gets possible image formats to paste from clipboard.

    Returns
    -------
    list
        List of strings showing the extension of the image formats.
    """
    if detect_x11():
        return ['png']
    s = 'xclip -selection clip -t TARGETS -o &'
    if detect_silverblue():
        home = os.path.expanduser('~')
        script_path = os.path.join(
            home,
            '.local',
            'share',
            'nautilus-python',
            'extensions',
            'paste-image',
            'immutable-preview.sh')
        s = 'toolbox run sh ' + script_path
    formats = os.popen(s).read().splitlines()
    image_types = [f[6:] for f in formats if f[:6] == 'image/']
    return image_types


def detect_silverblue():
    s = 'hostnamectl | grep -i "Operating System"'
    result = os.popen(s).read()
    return 'silverblue' in result.lower() or 'kinoite' in result.lower()


def paste_image(fp):
    """
    Pastes images to the given directory.

    Parameters
    ----------
    fp : str
        File path for a directory.
    """
    if not detect_image_in_clipboard:
        return
    if not os.path.isdir(fp):
        fp = os.path.dirname(fp)
    f = str(get_image_formats()[0])
    ext = f
    if 'png' in get_image_formats():
        f = 'png'
        ext = 'png'
    elif 'jpeg' in get_image_formats():
        f = 'jpeg'
        ext = 'jpg'
    if len(f) >= 2 and f[:2] == 'x-':
        f = f[2:]
    fp = os.path.join(fp, 'Pasted Image.' + ext)
    ogfp = fp
    n = 1
    while os.path.exists(fp):
        fp = ogfp[:-(len(ext) + 1)] + ' ' + str(n) + '.' + ext
        n += 1
    fs = '"' + fp + '"'
    s = 'xclip -selection clipboard -t image/' + f + ' -o >' + fs + ' &'
    if detect_silverblue():
        home = os.path.expanduser('~')
        script_path = os.path.join(
            home,
            '.local',
            'share',
            'nautilus-python',
            'extensions',
            'paste-image',
            'immutable-paste.sh')
        s = 'toolbox run sh ' + script_path + ' ' + f + ' ' + fs
    os.system(s)


def detect_image_in_clipboard():
    """
    Determines if there's an image stored in the clipboard.

    Returns
    -------
    bool
        Whether or not there's a pasteable image in the clipboard.
    """
    if detect_x11():
        return True
    return len(get_image_formats()) > 0


class PasteProvider(GObject.GObject, Nautilus.LocationWidgetProvider):
    """
    Provider for the '<Shift><Ctrl>v' keyboard shortcut to paste an image.
    """

    def __init__(self):
        self._window = None
        self._uri = None

    def _paste_image(self, arg1, arg2):
        p = urlparse(self._uri)
        fp = os.path.abspath(os.path.join(p.netloc, p.path))
        paste_image(fp)

    def _assign(self):
        """
        Assign the shortcut accelerators.
        """
        app = Gtk.Application.get_default()
        action_group = Gio.SimpleActionGroup()
        self._window.insert_action_group('pimg', action_group)
        paste_action = Gio.SimpleAction(name="paste")
        paste_action.connect("activate", self._paste_image)
        action_group.add_action(paste_action)
        app.set_accels_for_action('pimg.paste', ["<Shift><Ctrl>v"])

    def get_widget(self, uri, window):
        self._window = window
        self._uri = uri
        self._assign()


class PasteMenuProvider(GObject.GObject, Nautilus.MenuProvider):
    """
    Provider for the image pasting menu items.
    """

    def __init__(self):
        pass

    def _paste_image(self, file):
        fp = file.get_location().get_path()
        paste_image(fp)

    def _paste_images(self, files):
        for file in files:
            self._paste_image(file)

    def menu_activate_cb(self, menu, files):
        self._paste_images(files)

    def background_activate_cb(self, menu, file):
        self._paste_image(file)

    def get_file_items(self, window, files):
        """
        Menu for selected directories.
        """
        if not detect_image_in_clipboard():
            return
        are_dirs = [file.is_directory() for file in files]
        if not any(are_dirs):
            return
        if len(files) == 1:
            label = 'Paste Image Into Folder'
            tip = 'Paste image into %s' % files[0].get_name()
        else:
            label = 'Paste Image Into Folders'
            tip = 'Paste image into selected directories'
        item = Nautilus.MenuItem(name='PasteImages',
                                 label=label,
                                 tip=tip)
        item.connect('activate', self.menu_activate_cb, files)
        return item,

    def get_background_items(self, window, file):
        """
        Menu for the background window.
        """
        if not detect_image_in_clipboard():
            return
        detect_image_in_clipboard()
        item = Nautilus.MenuItem(name='PasteImage',
                                 label='Paste Image',
                                 tip='Paste image in %s' % file.get_name())
        item.connect('activate', self.background_activate_cb, file)
        return item,
