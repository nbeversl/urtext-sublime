# Module to handle reverse dating of filenames

import sublime
import sublime_plugin
import datetime
import os
import time
import sys
sys.path.append(os.path.join(os.path.dirname(__file__),"urtext/dependencies"))
sys.path.append(os.path.join(os.path.dirname(__file__)))
import urtext
# = 12 dashes in a row starting a line, followed by a newline

def meta_separator():
    settings = sublime.load_settings('urtext-default.sublime-settings')
    meta_separator = settings.get('meta_separator') 
    return meta_separator

class ShowReverseDateFilenameCommand(sublime_plugin.TextCommand):
    """
    Takes the timestamp-formatted date highlighted and converts it into a reverse-dated
    filename which is copied to the clipboard. For file naming.
    """
    def run(self, edit):
        for region in self.view.sel():
            text = self.view.substr(region)
            date = datetime.datetime.strptime(text, urtext.datestimes.timestamp_format)
            sublime.set_clipboard(urtext.datestimes.make_node_id(date))
            self.view.show_popup(
            'Reverse-dated filename copied to clipboard.')

class ReFile(sublime_plugin.TextCommand):
    def run(self, edit):
        now = datetime.datetime.now()

