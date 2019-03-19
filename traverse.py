import sublime
import sublime_plugin
import os
import re
import sublime_urtext

class ToggleTraverse(sublime_plugin.TextCommand):
  def run(self,edit): 
    Urtext.refresh_nodes(self.view.window()) 
    if self.view.settings().has('traverse'):
      if self.view.settings().get('traverse') == 'true':
        self.view.settings().set('traverse','false')
        self.view.set_status('traverse', 'Traverse: Off')
        self.view.settings().set("word_wrap", True)
        return
    #
    # if 'traverse' is not in settings or it's 'false': 
    #
    self.view.settings().set('traverse', 'true')
    self.view.set_status('traverse', 'Traverse: On')

  
    #
    # Add another group to the left if needed
    #
    groups = self.view.window().num_groups()
    active_group = self.view.window().active_group() # 0-indexed
    if active_group + 1 == groups:
      groups += 1
    panel_size = 1 / groups
    cols = [0]
    cells = [[0,0,1,1]]
    for index in range(1,groups):
      cols.append(cols[index-1]+panel_size)
      cells.append([index,0,index+1,1])
    cols.append(1)
  
    self.view.window().set_layout({"cols":cols, "rows": [0,1], "cells": cells})
    self.view.settings().set("word_wrap", False)

    #
    # move any other open tabs to rightmost pane.
    #

    views = self.view.window().views_in_group(active_group)
    index = 0
    for view in views:
      if view != self.view:
        self.view.window().set_view_index(view, 
          groups-1, # 0-indexed from 1-indexed value
          index)  
        index += 1
    
    # This doesn't yet work:
    #command = TraverseFileTree()
    #command.on_selection_modified(self.view)
    self.view.window().focus_group(active_group)


class TraverseFileTree(sublime_plugin.EventListener):

  def on_selection_modified(self, view):

    #
    # ? TODO:
    # Add a failsafe in case the user has closed the next group to the left
    # but traverse is still on. 
    #
    self.groups = view.window().num_groups()
    self.active_group = view.window().active_group() # 0-indexed
    self.content_view = view.window().active_view_in_group(self.active_group)
    contents = sublime_urtext.get_contents(self.content_view)
    
    def move_to_location(view, position, tree_view):
        if not view.is_loading():
          view.window().focus_group(self.active_group+1)
          self.content_view.show_at_center(position)
          #self.return_to_left(view, tree_view)
        else:
          sublime.set_timeout(lambda: move_to_location(view,position), 10)


    if view.settings().get('traverse') == 'true':
      tree_view = view

      window = view.window()
      full_line = view.substr(view.line(view.sel()[0]))
      links = re.findall('->\s(?:[^\|]*\s)?(\d{14})(?:\s[^\|]*)?\|?',full_line) # allows for spaces and symbols in filenames, spaces stripped later
      
      if len(links) ==0 : # might be an inline node view        
        link = full_line.strip('└── ').strip('├── ')
        position = self.content_view.find('{{\s+'+link, 0)
        line = self.content_view.line(position)
        self.content_view.sel().add(line)
        move_to_location(view,position,tree_view)
        return

      filenames = []
      for link in links:
        filenames.append(Urtext._UrtextProject.get_file_name(link))
      if len(filenames) > 0 :
        path = Urtext.get_path(window)
        window.focus_group(self.active_group + 1)
        file_view = window.open_file(os.path.join(path, filenames[0]), sublime.TRANSIENT)
        self.return_to_left(file_view, tree_view)
         
  def return_to_left(self, view, return_view):
    if not view.is_loading():
        view.window().focus_view(return_view)
        view.window().focus_group(self.active_group)
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
