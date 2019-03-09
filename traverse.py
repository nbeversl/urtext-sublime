import sublime
import sublime_plugin
import os
import re
import Urtext.urtext as Urtext

class ToggleTraverse(sublime_plugin.TextCommand):
  def run(self,edit):  
    groups = self.view.window().num_groups()
    if self.view.settings().has('traverse'):
      if self.view.settings().get('traverse') == 'true':
        self.view.settings().set('traverse','false')
        self.view.set_status('traverse', 'Traverse: Off')
        
        self.view.window().set_layout({"cols":[0,1], "rows": [0,1]})
        self.view.settings().set("word_wrap", True)
        return

    # if 'traverse' is not in settings or it's false: 
    self.view.settings().set('traverse', 'true')
    self.view.set_status('traverse', 'Traverse: On')

    panel_size = 1 / groups
    cols = [0]
    for index in range(1,groups):
      cols.append(cols[index-1]+panel_size)
    cols.append(1)

    self.view.window().set_layout({"cols":[0,0.4,1], "rows": [0,1], "cells": [[0, 0, 1, 1], [1, 0, 2, 1]]})
    self.view.settings().set("word_wrap", False)
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
        filenames.append(Urtext._UrtextProject.get_file_name(link))
      if len(filenames) > 0 :
        path = Urtext.get_path(window)
        window.focus_group(1)
        file_view = window.open_file(os.path.join(path, filenames[0]), sublime.TRANSIENT)
        self.return_to_left(file_view, tree_view)
         
  def return_to_left(self, view, return_view):
    if not view.is_loading():
        view.window().focus_view(return_view)
        view.window().focus_group(0)
    else:
      sublime.set_timeout(lambda: self.return_to_left(view,return_view), 10)

class OpenNodeCommand(sublime_plugin.TextCommand):
    def run(self, edit):
      full_line = self.view.substr(self.view.line(self.view.sel()[0]))
      links = re.findall('->\s(?:[^\|]*\s)?(\d{14})(?:\s[^\|]*)?\|?',full_line) # allows for spaces 
      if len(links) == 0:
        return
      path = Urtext.get_path(self.view.window())
      filename = Urtext._UrtextProject.get_file_name(links[0])
      file_view = self.view.window().open_file(os.path.join(path, filename))
