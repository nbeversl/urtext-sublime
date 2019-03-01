import sublime
import sublime_plugin
import os
import re
import Urtext.urtext as Urtext

class ToggleTraverse(sublime_plugin.TextCommand):
  def run(self,edit):  
    if self.view.settings().has('traverse'):
      if self.view.settings().get('traverse') == 'true':
        self.view.settings().set('traverse','false')
        self.view.set_status('traverse', 'Traverse: Off')
        return
    # if 'traverse' is not in settings or it's false: 
    self.view.settings().set('traverse', 'true')
    self.view.set_status('traverse', 'Traverse: On')
    self.view.window().set_layout({"cols":[0,0.4,1], "rows": [0,1], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})

    # This moves all the files to right pane.
    # Maybe it's better to check individuall if they're already open, and then move them, as they are clicked.
    views = self.view.window().views()
    index = 0
    for view in views:
      if view != self.view:
        self.view.window().set_view_index(view, 1, index)
        index += 1

    self.view.window().focus_group(0)
    
class TraverseFileTree(sublime_plugin.EventListener):

  def on_selection_modified(self, view):
    if view.settings().get('traverse') == 'true':
      tree_view = view
      window = view.window()
      full_line = view.substr(view.line(view.sel()[0]))
      links = re.findall('->\s(?:[^\|]*\s)?(\d{14})(?:\s[^\|]*)?\|?',full_line) # allows for spaces and symbols in filenames, spaces stripped later
      filenames = []
      for link in links:
        filenames.append(Urtext.get_file_from_node(link, window))
      if len(filenames) > 0 :
        path = Urtext.get_path(window)
        window.focus_group(1)
        file_view = window.open_file(os.path.join(path, filenames[0]), sublime.TRANSIENT)
        file_view.set_scratch(True)
        self.return_to_left(file_view, tree_view)
         
  def return_to_left(self, view, return_view):
    if not view.is_loading():
        view.window().focus_view(return_view)
        view.window().focus_group(0)
    else:
      sublime.set_timeout(lambda: self.return_to_left(view,return_view), 10)

