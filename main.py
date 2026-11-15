import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw
from ui.window import VisionCompWindow

def on_activate(app):
    win = VisionCompWindow(app)
    win.present()

if __name__ == '__main__':
    app = Adw.Application(application_id='com.vision.comp')
    app.connect('activate', on_activate)
    sys.exit(app.run(sys.argv))