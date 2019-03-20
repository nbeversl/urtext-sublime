# Urtext - Main
import sublime
import sublime_plugin
import os
import re
import urtext.datestimes
import sublime_urtext_datestimes
from urtext.node import UrtextNode
from urtext.project import UrtextProject
import datetime

# TODOS
# Have the node tree auto update on save.
# Fix indexing not working in fuzzy search in panel
# update documentation
# investigate multiple scopes
# investigate git and diff support

_UrtextProject = None

def get_path(window): # transfer this to an urtext .cfg file
  """ Returns the Urtext path from settings """
  if window.project_data():
    path = window.project_data()['urtext_path'] # ? 
  else:
    path = '.'
  return path

class ShowTagsCommand(sublime_plugin.TextCommand):

  global _UrtextProject

  def run(self, edit):
    self.tagnames = [ value for value in _UrtextProject.tagnames ]
    print(self.tagnames)
    self.view.window().show_quick_panel(self.tagnames, self.list_values)

  def list_values(self, index):
    self.selected_tag = self.tagnames[index]
    self.values = [ value for value in _UrtextProject.tagnames[self.selected_tag]]
    self.values.insert(0, '< all >')
    self.view.window().show_quick_panel(self.values, self.display_files)

  def display_files(self, index):
  
    self.selected_value = self.values[index]
    menu = make_node_menu(_UrtextProject.tagnames[self.selected_tag][self.selected_value], menu=[])
    print(menu)
    display_menu = sort_menu(menu)
    show_panel(self.view.window(), display_menu, self.open_the_file)

  def open_the_file(self, selected_option): # copied from below, refactor later.
    print(selected_option)
    path = get_path(self.view.window())
    new_view = self.view.window().open_file(os.path.join(path, selected_option[2])) 
    if selected_option[3] != None:
      self.locate_node(selected_option[3], new_view)


  def list_files(self, index):
    self.selected_value = self.values[index]
    new_view = self.view.window().new_file()
    new_view.set_scratch(True)
    if self.selected_value == '< all >':
      new_view.run_command("insert_snippet", { "contents": '\nFiles found for tag: %s\n\n' % self.selected_value})
      for value in _UrtextProject.tagnames[self.selected_tag]:
        new_view.run_command("insert_snippet", { "contents": value + "\n"})       
        for node in _UrtextProject.tagnames[self.selected_tag][value]:
          new_view.run_command("insert_snippet", { "contents": " -> " +node + "\n"})   
        new_view.run_command("insert_snippet", { "contents": "\n"})       

    else:
      new_view.run_command("insert_snippet", { "contents": '\nFiles found for tag: %s with value %s\n\n' % (self.selected_tag, self.selected_value)})
      for node in _UrtextProject.tagnames[self.selected_tag][self.selected_value]:
        new_view.run_command("insert_snippet", { "contents": " -> " +node + "\n"})       

class ShowInlineNodeTree(sublime_plugin.TextCommand):
  def run(self, edit):

    def render_tree(view):
        if not view.is_loading():
           view.run_command("insert_snippet", {"contents": _UrtextProject.nodes[node_id].tree})
        else:
          sublime.set_timeout(lambda: render_tree(view), 10)

    def locate_view(name):
      all_views = self.view.window().views()
      for view in  all_views:
        if view.name() == name:
          return view
      return None

    global _UrtextProject

    filename = self.view.file_name()
    node_id = _UrtextProject.get_node_id(os.path.basename(filename))  
    tree_name = node_id + 'TREE'
    tree_view = locate_view(tree_name)
    #
    # See if a view is already named.
    #
    if tree_view == None:    
      add_one_split(self.view)
      # these two values are duplicated in add_one_split .. better way?
      groups = self.view.window().num_groups() # copied from traverse. Should refactor
      active_group = self.view.window().active_group() # 0-indexed

      # move everything to the right
      views = self.view.window().views_in_group(active_group)
      index = 0
      for view in views:
        self.view.window().set_view_index(view, 
          groups-1, # 0-indexed from 1-indexed value
          index)  
        index += 1
    
      self.view.window().focus_group(active_group)
      tree_view = self.view.window().new_file()
      tree_view.set_name(node_id+'TREE')
    else:
      tree_view.erase(edit, sublime.Region(0,1000)) # TODO - not 1000. Entire view.

    render_tree(tree_view)

def add_one_split(view):
  groups = view.window().num_groups() # copied from traverse. Should refactor
  active_group = view.window().active_group() # 0-indexed
  groups += 1
  
  # side the panels (refactor this)
  panel_size = 1 / groups
  cols = [0]
  cells = [[0,0,1,1]]
  for index in range(1,groups):
    cols.append(cols[index-1]+panel_size)
    cells.append([index,0,index+1,1])
  cols.append(1)
  view.window().set_layout({"cols":cols, "rows": [0,1], "cells": cells})
  view.settings().set("word_wrap", False)

def refresh_nodes(window):
  global _UrtextProject
  if _UrtextProject == None:
    print('_UrtextProject rebuilt')
    _UrtextProject = UrtextProject(get_path(window))  

class InsertNodeCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    node_id = urtext.datestimes.make_node_id(datetime.datetime.now())
    for region in self.view.sel():
      selection = self.view.substr(region)
    node_wrapper = '{{ '+selection+'\n /- ID:'+node_id+' -/ }}'
    self.view.run_command("insert_snippet", {
                             "contents": node_wrapper})  # (whitespace)
    self.view.run_command("save")

class UrtextSave(sublime_plugin.EventListener):
  """ This takes the place of an file watcher"""

  def on_post_save(self, view):    
    global _UrtextProject
  
    try: # not a new file
      file = UrtextNode(view.file_name())
      _UrtextProject.nodes[file.node_number] = file
      for node_number in _UrtextProject.files[os.path.basename(view.file_name())]:
        del _UrtextProject.nodes[node_number]
      _UrtextProject.build_sub_nodes(view.file_name())

    except KeyError: # new file
      file = UrtextNode(view.file_name())
      _UrtextProject.nodes[file.node_number] = file
      _UrtextProject.files[os.path.basename(view.file_name())] = [file.node_number]

    node_id = _UrtextProject.get_node_id(os.path.basename(view.file_name()))

    if '[[' in _UrtextProject.nodes[node_id].contents:
      _UrtextProject.compile(node_id)

    if node_id+'TREE' in [view.name() for view in view.window().views()]:
      # not yet working
      ShowInlineNodeTree.run(view)

    # too much, revise later.
    for node in list(_UrtextProject.nodes):
      _UrtextProject.compile(node)
    
    _UrtextProject.build_tag_info()

class RenameFileCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    global _UrtextProject
    old_filename = self.view.file_name()
    new_filename = _UrtextProject.rename(old_filename)
    v = self.view.window().find_open_file(old_filename)
    if v:
      v.retarget(os.path.join(_UrtextProject.path,new_filename))
      v.set_name(new_filename)

class NodeBrowserCommand(sublime_plugin.WindowCommand):
    def run(self):
      global _UrtextProject  
      refresh_nodes(self.window)
      menu = make_node_menu(_UrtextProject.indexed_nodes(), menu = [])
      menu = make_node_menu(_UrtextProject.unindexed_nodes(), menu = menu)
      display_menu = sort_menu(menu)      
      show_panel(self.window, display_menu, self.open_the_file)

    def open_the_file(self, selected_option):
      path = get_path(self.window)
      new_view = self.window.open_file(os.path.join(path,selected_option[2])) 
      if selected_option[3] != None:
        self.locate_node(selected_option[3], new_view)

    def locate_node(self, position, view):
      if not view.is_loading(): 
        view.sel().clear()
        view.show_at_center(position) 
        view.sel().add(sublime.Region(position))
      else:
        sublime.set_timeout(lambda: self.locate_node(position, view), 10)

class LinkToNodeCommand(sublime_plugin.WindowCommand): 
    def run(self):
      show_panel(self.window, self.link_to_the_file)

    def link_to_the_file(self, selected_option):
      view = self.window.active_view()
      filename = os.path.basename(selected_option[2])
      view.run_command("insert", {"characters": ' -> '+ filename + ' | '})

class LinkNodeFromCommand(sublime_plugin.WindowCommand): 
    def run(self):
      self.current_file = os.path.basename(self.window.active_view().file_name())
      show_panel(self.window, self.link_from_the_file)

    def link_from_the_file(self, selected_option):
        new_view = self.window.open_file(selected_option[2])
        sublime.set_clipboard(' -> ' + self.current_file)
        self.show_tip(new_view)

    def show_tip(self, view):
      if not view.is_loading(): 
        view.show_popup('Link to ' + self.current_file + ' copied to the clipboard')
      else:
        sublime.set_timeout(lambda: self.show_tip(view), 10)

def show_panel(window, menu, main_callback): 
  def private_callback(index):
    if index == -1:
      return
    main_callback(menu[index])
  window.show_quick_panel(menu, private_callback)

def make_node_menu(node_ids, menu=[]):
  for node_id in node_ids:
    item = []
    metadata = _UrtextProject.nodes[node_id].metadata
    item.append(metadata.get_tag('title')[0])  # should title be a list or a string? 
    item.append(urtext.datestimes.date_from_reverse_date(node_id))
    item.append(_UrtextProject.nodes[node_id].filename)
    item.append(_UrtextProject.nodes[node_id].position)
    menu.append(item)
  return menu

def sort_menu(menu):
  display_menu = []
  for item in menu: # there is probably a better way to copy this list.
    new_item = [item[0], item[1].strftime('<%a., %b. %d, %Y, %I:%M %p>'),item[2]]
    display_menu.append(new_item)
  return display_menu 

def get_contents(view):
  contents = view.substr(sublime.Region(0, view.size()))
  return contents

class ShowAllNodesCommand(sublime_plugin.TextCommand):
  def run(self,edit):
    global _UrtextProject
    refresh_nodes(self.view.window())
    new_view = self.view.window().new_file()
    output = _UrtextProject.list_nodes()
    new_view.run_command("insert", {"characters": output})
    
class DeleteThisNodeCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        global _UrtextProject
        file_name = os.path.basename(self.view.file_name())
        if self.view.is_dirty():
            self.view.set_scratch(True)
        self.view.window().run_command('close_file')
        _UrtextProject.delete(file_name)
