# Urtext - Main
import sublime
import sublime_plugin
import os
import re
import datetime
import pprint
import logging
import sys
sys.path.append(os.path.join(os.path.dirname(__file__),"urtext/dependencies"))
sys.path.append(os.path.join(os.path.dirname(__file__)))

from urtext.node import UrtextNode
from urtext.project import UrtextProject
from urtext.metadata import NodeMetadata
import urtext.metadata
from watchdog.events import FileSystemEventHandler
import watchdog
from watchdog.observers import Observer
import webbrowser
from urtext.project_list import ProjectList
from urtext.project import node_id_regex

_UrtextProject = None
_UrtextProjectList = None

class SublimeUrtextWatcher(FileSystemEventHandler):
 
    def on_created(self, event):
        
        global _UrtextProject
        if event.is_directory:
          return None
        filename = event.src_path
        if _UrtextProject.parse_file(filename) == None:
          _UrtextProject.log.info(filename + ' not added.')
          return
        print(filename + ' MODIFIED')
        _UrtextProject.log.info(filename + ' modified. Updating the project object')
        _UrtextProject.build_tag_info()
        _UrtextProject.compile_all()
          
    def on_modified(self, event):
        # this is also called on files being added
        global _UrtextProject
        if event.is_directory:
          return None
        filename = os.path.basename(event.src_path)
        print(filename + ' MODIFIED')
        if filename == _UrtextProject.settings['logfile'] or '.git' in filename:
          return
        _UrtextProject.log.info('MODIFIED ' + filename +' - Updating the project object')
        _UrtextProject.parse_file(filename)
        _UrtextProject.build_tag_info()
        _UrtextProject.compile_all()
          
    def on_deleted(self, event):

      filename = os.path.basename(event.src_path)
      _UrtextProject.log.info('Watchdog saw file deleted: '+filename)
      _UrtextProject.delete_file(filename)
     
    def on_moved(self, event):
        old_filename = os.path.basename(event.src_path)
        new_filename = os.path.basename(event.dest_path)
        if old_filename in _UrtextProject.files:
           _UrtextProject.log.info('RENAMED '+ old_filename +' to ' + new_filename)
           _UrtextProject.handle_renamed(old_filename, new_filename)

def refresh_project(view):

  global _UrtextProject
  current_path = get_path(view)

  if _UrtextProject != None:  
    if current_path == _UrtextProject.path:
      return _UrtextProject
    else:
      return focus_urtext_project(current_path, view)

  # no Urtext project yet defined
  if current_path != None: 
    _UrtextProject = focus_urtext_project(current_path, view)
  
  else:
    print('No Urtext Project')
    return None

  if _UrtextProjectList == None:        
    global _UrtextProjectList
    _UrtextProjectList = ProjectList(_UrtextProject.path, _UrtextProject.other_projects)

  return _UrtextProject


def focus_urtext_project(path, view):
  global _UrtextProject
  _UrtextProject = UrtextProject(path)
  results = _UrtextProject.build_response
  results_view = view.window().new_file()
  results_view.set_scratch(True)
  results_view.run_command("insert_snippet", { "contents": results})     
  event_handler = SublimeUrtextWatcher()
  observer = Observer()
  observer.schedule(event_handler, path=_UrtextProject.path, recursive=False)
  observer.start()
  return _UrtextProject

def get_path(view): ## makes the path persist as much as possible ##
  
  if view.file_name():
    return os.path.dirname(view.file_name())  
  if view.window().project_data():
    return view.window().project_data()['folders'][0]['path']
  return None


class FindByMetaCommand(sublime_plugin.TextCommand):

  def run(self, edit):
    refresh_project(self.view)    
    self.tagnames = [ value for value in _UrtextProject.tagnames ]
    self.view.window().show_quick_panel(self.tagnames, self.list_values)

  def list_values(self, index):
    self.selected_tag = self.tagnames[index]
    self.values = [ value for value in _UrtextProject.tagnames[self.selected_tag]]
    self.values.insert(0, '< all >')
    self.view.window().show_quick_panel(self.values, self.display_files)

  def display_files(self, index):
  
    self.selected_value = self.values[index]
    if self.selected_value == '< all >':
      pass # fix this
    self.menu = NodeBrowserMenu(_UrtextProject.tagnames[self.selected_tag][self.selected_value])
    show_panel(self.view.window(), self.menu.display_menu, self.open_the_file)

  def open_the_file(self, selected_option): # copied from below, refactor later.
    if selected_option == -1:
      return
    path = get_path(self.view)
    new_view = self.view.window().open_file(os.path.join(path, self.menu.get_values_from_index(selected_option).filename)) 
    if selected_option[3] and selected_option[3] != None:
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

class ShowTagsCommand(sublime_plugin.TextCommand):

  def run(self, edit):
    refresh_project(self.view)    
    self.tag_values = [ value for value in _UrtextProject.tagnames['tags'] ]
    self.tag_values.insert(0, '< all >')
    self.view.window().show_quick_panel(self.tag_values, self.display_files)

  def display_files(self, index):
  
    self.selected_value = self.tag_values[index]
    if self.selected_value == '< all >':
      pass # fix this
    self.menu = NodeBrowserMenu(_UrtextProject.tagnames['tags'][self.selected_value])
    show_panel(self.view.window(), self.menu.display_menu, self.open_the_file)

  def open_the_file(self, selected_option): # copied from below, refactor later.
    if selected_option == -1:
      return
    path = get_path(self.view)
    new_view = self.view.window().open_file(os.path.join(path, self.menu.get_values_from_index(selected_option).filename)) 
    #if selected_option[3] and selected_option[3] != None:
      #self.locate_node(selected_option[3], new_view)

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

class TagNodeCommand(sublime_plugin.TextCommand): #under construction

  def run(self, edit):
    refresh_project(self.view)
    self.tagnames = [ value for value in _UrtextProject.tagnames ]
    self.view.window().show_quick_panel(self.tagnames, self.list_values)

  def list_values(self, index):
    if index == -1:
      return
    self.selected_tag = self.tagnames[index]
    self.values = [ value for value in _UrtextProject.tagnames[self.selected_tag]]
    self.view.window().show_quick_panel(self.values, self.insert_tag)

  def insert_tag(self, index):
    if index == -1:
      return
    self.selected_value = self.values[index]
    timestamp = self.timestamp(datetime.datetime.now())
    tag = '/-- '+self.selected_tag+': '+self.selected_value+' '+timestamp+' --/'
    self.view.run_command("insert_snippet", { "contents": tag})


  def locate_from_in_node(self, index): # useful in the future.
    selected_tag = self.values[index]
    max_size = self.view.size()
    region = self.view.sel()[0]
    subnode_regexp = re.compile(r'{{(?!.*{{)(?:(?!}}).)*}}', re.DOTALL)
    selection = self.view.substr(region)
    while not subnode_regexp.search(selection):
      a = region.a
      b = region.b
      if selection[:2] != '{{':
        a -= 1
      if selection[-2:] != '}}':
        b += 1
      region = sublime.Region(a, b)
      if a == 0 or b == max_size: # entire file
        break
      selection = self.view.substr(region)

    metadata = urtext.metadata.NodeMetadata(selection[2:-2])
    # this all successfully identifies which node the cursor is in.
    # from here this should probably be done in the metadata class, not here.
    # get the metadata string out, probably using regex
    # find a place where the tag is

    if selected_tag not in metadata.get_tag(self.selected_tag):
      print('ADD IT')

class ShowTreeFromNode(sublime_plugin.TextCommand):
  def run(self, edit):

    if refresh_project(self.view) == None:
      return

    def render_tree(view, tree_render):
        if not view.is_loading():
           view.run_command("insert_snippet", {"contents": tree_render})
        else:
          sublime.set_timeout(lambda: render_tree(view, tree_render), 10)

    filename = self.view.file_name()
    position = self.view.sel()[0].a
    node_id = _UrtextProject.get_node_id_from_position(filename, position)
    tree_render = _UrtextProject.show_tree_from(node_id)
    tree_view = target_tree_view(self.view)
    tree_view.erase(edit, sublime.Region(0, tree_view.size()))
    render_tree(tree_view, tree_render)


class ShowTreeFromRootCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    if refresh_project(self.view) == None:
      return

    def render_tree(view, tree_render):
        if not view.is_loading():
           view.run_command("insert_snippet", {"contents": tree_render})
        else:
          sublime.set_timeout(lambda: render_tree(view, tree_render), 10)

    filename = os.path.basename(self.view.file_name())
    position = self.view.sel()[0].a
    node_id = _UrtextProject.get_node_id_from_position(filename, position)
    tree_render = _UrtextProject.show_tree_from_root_of(node_id)
    tree_view = target_tree_view(self.view)
    tree_view.erase(edit, sublime.Region(0, tree_view.size()))
    render_tree(tree_view, tree_render)

def target_tree_view(view):

  filename = view.file_name()
  if filename == None:
    return

  def locate_view(view, name):
      all_views = view.window().views()
      for view in all_views:
        if view.name() == name:
          return view
      return None

  tree_name = filename + 'TREE' # Make a name for the view
  tree_view = locate_view(view, tree_name)
  if tree_view == None:
    tree_view = view.window().new_file()
    tree_view.set_name(filename+'TREE')
    tree_view.set_scratch(True)

  groups = view.window().num_groups() # copied from traverse. Should refactor
  active_group = view.window().active_group() # 0-indexed
  if active_group == 0 or view.window().get_view_index(tree_view)[0] != active_group -1: 
    print(groups)
    if groups > 1 and view.window().active_view_in_group(active_group - 1).file_name() == None:
      view.window().set_view_index(tree_view, active_group-1, 0)
    else:
      groups += 1
      panel_size = 1 / groups
      cols = [0]
      cells = [[0,0,1,1]]
      for index in range(1,groups):
        cols.append(cols[index-1]+panel_size)
        cells.append([index,0,index+1,1])
      cols.append(1)
      view.window().set_layout({"cols":cols, "rows": [0,1], "cells": cells})
      view.settings().set("word_wrap", False)

      sheets = tree_view.window().sheets_in_group(active_group)
      index = 0
      for sheet in sheets:
        tree_view.window().set_sheet_index(sheet, 
          groups-1, # 0-indexed from 1-indexed value
          index)  
        index += 1
      view.window().set_view_index(tree_view, active_group,0)
      view.window().focus_group(active_group)
  return tree_view

class InsertNodeCommand(sublime_plugin.TextCommand):
  """ inline only, does not make a new file """
  def run(self, edit):
    if refresh_project(self.view) == None:
        return
    filename = self.view.file_name()
    for region in self.view.sel():
      selection = self.view.substr(region)
    node_id = _UrtextProject.add_inline_node(datetime.datetime.now(), filename, selection)
    node_wrapper = '{{ '+selection+' /-- ID:'+node_id+' --/ }}'
    self.view.run_command("insert_snippet", {"contents": node_wrapper})  # (whitespace)
    self.view.run_command("save")

class RenameFileCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    refresh_project(self.view)
    old_filename = self.view.file_name()
    new_filenames = _UrtextProject.rename_file_nodes(old_filename)
    self.view.retarget(os.path.join(_UrtextProject.path, new_filenames[os.path.basename(old_filename)]))

class NodeBrowserCommand(sublime_plugin.WindowCommand):
    def run(self):
      if refresh_project(self.window.active_view()) == None:
        return
      global _UrtextProject
      self.menu = NodeBrowserMenu(_UrtextProject.indexed_nodes())
      self.menu.add(_UrtextProject.unindexed_nodes())
      show_panel(self.window, self.menu.display_menu, self.open_the_file)

    def open_the_file(self, selected_option):
      path = get_path(self.window.active_view())
      title = self.menu.get_values_from_index(selected_option).title
      new_view = self.window.open_file(os.path.join(path, self.menu.get_values_from_index(selected_option).filename)) 

      # delete any nodes in front of this one (making a new navigation branch)
      del _UrtextProject.navigation[_UrtextProject.nav_index+1:]

      # add the newly opened file as the new "HEAD"
      _UrtextProject.navigation.append(self.menu.get_values_from_index(selected_option).node_id)
      
      # increment the index to match
      _UrtextProject.nav_index += 1

      print(_UrtextProject.navigation)

      self.locate_node(self.menu.get_values_from_index(selected_option).position, new_view, title)

    def locate_node(self, position, view, title):
      if not view.is_loading(): 
        view.sel().clear()
        view.show_at_center(int(position)) 
        view.sel().add(sublime.Region(int(position)))
      else:
        sublime.set_timeout(lambda: self.locate_node(int(position), view, title), 10)

class NodeBrowserMenu():
  """ custom class to store more information on menu items than is displayed """

  global _UrtextProject
  def __init__(self, node_ids):
    self.full_menu = make_node_menu(node_ids)
    self.display_menu = sort_menu(self.full_menu)

  def get_values_from_index(self, selected_option):
    index = self.display_menu.index(selected_option)
    return self.full_menu[index]

  def add(self, node_ids):
    self.full_menu.extend(make_node_menu(_UrtextProject.unindexed_nodes()))
    self.display_menu = sort_menu(self.full_menu)

class NodeInfo():
    def __init__(self, node_id):
      self.title = _UrtextProject.nodes[node_id].get_title()
      if self.title.strip() == '':
        self.title = '(no title)' 
      self.date = _UrtextProject.nodes[node_id].date
      self.filename = _UrtextProject.nodes[node_id].filename
      self.position = _UrtextProject.nodes[node_id].ranges[0][0]
      self.title = _UrtextProject.nodes[node_id].get_title()
      self.node_id = _UrtextProject.nodes[node_id].id

def make_node_menu(node_ids):
  menu = []
  for node_id in node_ids:
    item = NodeInfo(node_id)
    menu.append(item)
  return menu

def sort_menu(menu):
  display_menu = []
  for item in menu: # there is probably a better way to copy this list.
    item.position = str(item.position)
    new_item = [item.title, item.date.strftime('<%a., %b. %d, %Y, %I:%M %p>')]
    display_menu.append(new_item)
  return display_menu 



class LinkToNodeCommand(sublime_plugin.WindowCommand): 
    def run(self):
      if refresh_project(self.window.active_view()) == None:
        return
      self.menu = NodeBrowserMenu(_UrtextProject.nodes)
      show_panel(self.window, self.menu.display_menu, self.link_to_the_file)

    def link_to_the_file(self, selected_option):
      view = self.window.active_view()
      node_id = self.menu.get_values_from_index(selected_option).node_id
      title = self.menu.get_values_from_index(selected_option).title
      view.run_command("insert", {"characters":  title + ' >'+node_id})

class LinkNodeFromCommand(sublime_plugin.WindowCommand): 
    def run(self):
      if refresh_project(self.window.active_view()) == None:
        return
      self.current_file = os.path.basename(self.window.active_view().file_name())
      self.position = self.window.active_view().sel()[0].a
      self.menu = NodeBrowserMenu(_UrtextProject.nodes)
      show_panel(self.window, self.menu.display_menu, self.link_from_the_file)

    def link_from_the_file(self, selected_option):
        new_view = self.window.open_file(self.menu.get_values_from_index(selected_option).filename)
        self.show_tip(new_view)

    def show_tip(self, view):
      if not view.is_loading(): 
        node_id = _UrtextProject.get_node_id_from_position(self.current_file, self.position)
        
        title = _UrtextProject.nodes[node_id].get_title()
        link = title + ' >' + node_id
        sublime.set_clipboard(link)
        view.show_popup('Link to ' + link + ' copied to the clipboard')
      else:
        sublime.set_timeout(lambda: self.show_tip(view), 10)

def show_panel(window, menu, main_callback): 
  def private_callback(index):
    if index == -1:
      return
    main_callback(menu[index])
  window.show_quick_panel(menu, private_callback)


def get_contents(view):
  if view != None:
    contents = view.substr(sublime.Region(0, view.size()))
    return contents
  return None


class ToggleTraverse(sublime_plugin.TextCommand):
  def run(self,edit): 
    if refresh_project(self.view) == None :
      return
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

    global _UrtextProject
    #
    # TODO:
    # Add a failsafe in case the user has closed the next group to the left
    # but traverse is still on. 
    #
    if view.window() == None:
      return
    self.groups = view.window().num_groups()
    self.active_group = view.window().active_group() # 0-indexed
    self.content_sheet = view.window().active_sheet_in_group(self.active_group)
    contents = get_contents(self.content_sheet.view())
    
    def move_to_location(view, position, tree_view):
        if not view.is_loading():
          view.window().focus_group(self.active_group+1)
          self.content_sheet.view().show_at_center(position)
          self.return_to_left(view, tree_view)
        else:
          sublime.set_timeout(lambda: move_to_location(view,position), 10)


    if view.settings().get('traverse') == 'true':
      tree_view = view

      window = view.window()
      full_line = view.substr(view.line(view.sel()[0]))
      links = re.findall('>'+node_id_regex,full_line) # allows for spaces and symbols in filenames, spaces stripped later
    
      if len(links) == 0 : # might be an inline node view        
        link = full_line.strip('└── ').strip('├── ')
        position = self.content_sheet.view().find('{{\s+'+link, 0)
        line = self.content_sheet.view().line(position)
        self.content_sheet.view().sel().add(line)
        move_to_location(view,position,tree_view)
        return

      filenames = []
      for link in links:
        filenames.append(_UrtextProject.get_file_name(link[1:]))
      if len(filenames) > 0 :
        path = get_path(view)
        window.focus_group(self.active_group + 1)
        file_view = window.open_file(os.path.join(path, filenames[0]), sublime.TRANSIENT)
        self.return_to_left(file_view, tree_view)
         
  def return_to_left(self, view, return_view):
    if not view.is_loading():
        view.window().focus_view(return_view)
        view.window().focus_group(self.active_group)
    else:
      sublime.set_timeout(lambda: self.return_to_left(view,return_view), 10)

class ShowAllNodesCommand(sublime_plugin.TextCommand):

  def run(self,edit):
    if refresh_project(self.view) == None :
      return
    new_view = self.view.window().new_file()
    output = _UrtextProject.list_nodes()
    new_view.run_command("insert", {"characters": output})

class NewNodeCommand(sublime_plugin.WindowCommand):

  def run(self):
      if refresh_project(self.window.active_view()) == None :
        return
      self.path = _UrtextProject.path
      filename = _UrtextProject.new_file_node()
      new_view = self.window.open_file(os.path.join(self.path, filename))

class DeleteThisNodeCommand(sublime_plugin.TextCommand):

  def run(self, edit):
      if refresh_project(self.view) == None :
        return
      file_name = os.path.basename(self.view.file_name())
      if self.view.is_dirty():
          self.view.set_scratch(True)
      self.view.window().run_command('close_file')
      os.remove(os.path.join(_UrtextProject.path, file_name))
      _UrtextProject.delete_file(file_name) # remove if adding delete back to watchdog

class InsertTimestampCommand(sublime_plugin.TextCommand):

  def run(self, edit):
    if refresh_project(self.view) == None :
      return

    now = datetime.datetime.now()
    datestamp = _UrtextProject.timestamp(now)
    for s in self.view.sel():
        if s.empty():
            self.view.insert(edit, s.a, datestamp)
        else:
            self.view.replace(edit, s, datestamp)

class ConsolidateMetadataCommand(sublime_plugin.TextCommand):

  def run(self, edit):
    if refresh_project(self.view) == None :
      return
    self.view.run_command('save') # TODO insert notification
    filename = os.path.basename(self.view.file_name())
    position = self.view.sel()[0].a
    node_id = _UrtextProject.get_node_id_from_position(filename, position)
    consolidated_contents = _UrtextProject.consolidate_metadata(node_id, one_line=True)
    
    print(consolidated_contents)
    # just need to write this to the view.

class InsertDynamicNodeDefinitionCommand(sublime_plugin.TextCommand):

  def run(self, edit):
    now = datetime.datetime.now()
    node_id = _UrtextProject.next_index()
    content = '[[ ID:'+node_id +'\n\n ]]'
    for s in self.view.sel():
        if s.empty():
            self.view.insert(edit, s.a, content)
        else:
            view.replace(edit, s, content)

class UrtextSearchProjectCommand(sublime_plugin.TextCommand):

  def run(self,edit):
    if refresh_project(self.view) == None :
      return
    caption = 'Search String: '
    self.view.window().show_input_panel(caption, '', self.search_project, None, None)

  def search_project(self, string):
    results = _UrtextProject.search(string).split('\n')

    new_view = self.view.window().new_file()
    new_view.set_scratch(True)
    for line in results:
      new_view.run_command("insert_snippet", { "contents": line + '\n'})

class OpenUrtextLinkCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    if refresh_project(self.view) == None :
      return
    position = self.view.sel()[0].a
    column = self.view.rowcol(position)[1]
    full_line = self.view.substr(self.view.line(self.view.sel()[0]))
    link = _UrtextProject.get_link(full_line, position=column)
    if link == None: 
      # check to see if it's in another known project
      #other_project_node = _UrtextProjectList.get_node_link(full_line)
      """_UrtextProject.navigation.append(other_project_node)
      filename = other_project_node['filename']
      path = other_project_node['project_path']
      sublime.run_command("new_window")
      sublime.active_window().open_file(filename)"""
      return

    if link[0] == 'HTTP':
      if not webbrowser.get().open(link[1]):
          sublime.error_message(
              'Could not open tab using your "web_browser_path" setting: {}'.format(browser_path))
      return
    if link[0] == 'NODE':

      # delete any nodes in front of this one (making a new navigation branch)
      del _UrtextProject.navigation[_UrtextProject.nav_index+1:]

      # add the newly opened file as the new "HEAD"
      _UrtextProject.navigation.append(link[1])
      
      # increment the index to match
      _UrtextProject.nav_index += 1

      print(_UrtextProject.navigation)

      open_urtext_node(self.view, link[1], link[2])
    

def open_urtext_node(view, node_id, position):

  def center_node(view, position): # copied from old OpenNode. Refactor
      if not view.is_loading():
        view.sel().clear()
        view.show_at_center(int(position)) 
        view.sel().add(sublime.Region(int(position)))
      else:
        sublime.set_timeout(lambda: center_node(view, position), 10)
  
  filename = _UrtextProject.get_file_name(node_id)
  if filename == None:
    return
  file_view = view.window().open_file(os.path.join(_UrtextProject.path, filename))
  position = int(position)

  center_node(file_view, position)

class TagFromOtherNodeCommand(sublime_plugin.TextCommand):

  def run(self, edit):
    if refresh_project(self.view) == None :
      return
    full_line = self.view.substr(self.view.line(self.view.sel()[0]))
    links = re.findall('(?:[^\|]*\s)?>('+node_id_regex+')(?:\s[^\|]*)?\|?',full_line)
    if len(links) == 0:
      return
    path = get_path(self.view)
    node_id = links[0]
    timestamp = _UrtextProject.timestamp(datetime.datetime.now())

    # TODO move this into urtext, not Sublime
    tag = '/-- tags: done '+timestamp+' --/'
    _UrtextProject.tag_node(node_id, tag)
    _UrtextProject.build_tag_info()
    _UrtextProject.compile_all()
 
class GenerateTimelineCommand(sublime_plugin.TextCommand):
    def run(self,edit):
      if refresh_project(self.view) == None :
        return
      new_view = self.view.window().new_file()
      nodes = [_UrtextProject.nodes[node_id] for node_id in _UrtextProject.nodes]
      timeline = _UrtextProject.timeline(nodes)
      self.show_stuff(new_view, timeline)
      new_view.set_scratch(True)

    def show_stuff(self, view, timeline):
          if not view.is_loading(): 
            view.run_command("append", {"characters": timeline+'\n|'})
          else:
            sublime.set_timeout(lambda: self.show_stuff(view,timeline), 10)

class ShowLinkedRelationshipsCommand(sublime_plugin.TextCommand):
  """ Display a tree of all nodes connected to this one """
  # TODO: for files that link to the same place more than one time,
  # show how many times on one tree node, instead of showing multiple nodes
  # would this require building the tree after scanning all files?
  #
  # Also this command does not currently utilize the global array, it reads files manually.
  # Necessary to change it?

  def run(self, edit):
    if refresh_project(self.view) == None :
      return
    filename = os.path.basename(self.view.file_name())
    position = self.view.sel()[0].a
    node_id = _UrtextProject.get_node_id_from_position(filename, position)
    render = _UrtextProject.get_node_relationships(node_id)

    def draw_tree(view, render ):
      if not view.is_loading():
        view.run_command("insert_snippet", { "contents": render })
        view.set_scratch(True)
      else:
        sublime.set_timeout(lambda: draw_tree(view, render), 10)

    window = self.view.window()
    window.focus_group(0) # always show the tree on the leftmost focus'
    new_view = window.new_file()
    window.focus_view(new_view)
    draw_tree(new_view, render)    


class RightAlignGroupCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    selection = self.view.substr(self.view.sel()[0])
    line_position = self.view.rowcol(self.view.sel()[0].a)[1]
    new_line = ' ' * (119 - len(selection) - line_position) 
    new_line += selection
    lines = selection.split('\n')
    new_text = ''
    for line in lines:
      new_text += ' ' * (120 - len(line))
      new_text += line + '\n'
    self.view.replace(edit,self.view.sel()[0],new_line)
    
class RightAlignHereCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    line_region = self.view.line(self.view.sel()[0])
    cursor_pos = self.view.rowcol(self.view.sel()[0].a)[1]
    line_contents = self.view.substr(line_region)
    left = line_contents[:cursor_pos]
    right = line_contents[cursor_pos:]
    new_right = ' ' * ((120 - len(right.strip(' '))) - cursor_pos) 
    new_right += right.strip(' ')
    self.view.replace(edit, sublime.Region(self.view.sel()[0].a,self.view.sel()[0].a+len(right)),new_right)

class RightAlignSelectionCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    selection = self.view.split_by_newlines(self.view.line(self.view.sel()[0]))
    difference = 0
    for region in selection:
      region = sublime.Region(region.a + difference, region.b + difference)
      original_content = self.view.substr(region)
      stripped_content = original_content.strip()
      new_right = ' ' * (120 - len(stripped_content))
      new_right += stripped_content
      difference += len(new_right) - len(original_content)
      self.view.replace(edit, region, new_right)

class ReIndexFilesCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    if refresh_project(self.view) == None :
      return
    global _UrtextProject
    renamed_files = _UrtextProject.reindex_files()
    for view in self.view.window().views():
      if view.file_name() == None:
        continue
      if os.path.basename(view.file_name()) in renamed_files:
        view.retarget(os.path.join(_UrtextProject.path, renamed_files[os.path.basename(view.file_name())]))

class AddNodeIdCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    if refresh_project(self.view) == None :
      return
    global _UrtextProject
    new_id = _UrtextProject.next_index()
    self.view.run_command("insert_snippet", { "contents": "/-- ID: "+new_id+" --/"})

class DebugCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    if refresh_project(self.view) == None :
      return
    filename = self.view.file_name()
    position = self.view.sel()[0].a
    node_id = _UrtextProject.get_node_id_from_position(filename, position)

class ImportProjectCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    global _UrtextProject
    _UrtextProject = UrtextProject(get_path(self.view), import_project=True)

class ShowUrtextHelpCommand(sublime_plugin.WindowCommand):
  def run(self):
    global _UrtextProject
    active_window = sublime.active_window()
    this_file_path = os.path.dirname(__file__)
    open_windows = sublime.windows()
    #for window in open_windows:
    _UrtextProject = UrtextProject(os.path.join(os.path.dirname(__file__),"example project"))

    """if help_view != None:
        window.focus_view(help_view)
        if window != active_window:
          sublime.message_dialog('Urtext help is open in another window. Use Super - ~ to switch between windows  ')
        return"""
    sublime.run_command("new_window")
    
    help_view = sublime.active_window().new_file()
    open_urtext_node(help_view, _UrtextProject.settings['home'], 0)
    
class OpenUrtextLogCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    if refresh_project(self.view) == None :
      return
    file_view = self.view.window().open_file( os.path.join(_UrtextProject.path, _UrtextProject.settings['logfile']))
    
    def go_to_end(view):
      if not view.is_loading(): 
          view.sel().add(sublime.Region(view.size()))
          view.show_at_center(sublime.Region(view.size()))
      else:
        sublime.set_timeout(lambda: self.go_to_end(view), 10)    

    go_to_end(file_view)


class UrtextHomeCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    if refresh_project(self.view) == None :
      return
    node_id = _UrtextProject.settings['home']
    open_urtext_node(self.view, node_id, 0)

class UrtextReloadProjectCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    if refresh_project(self.view) == None :
      return  
    global _UrtextProject
    current_path = get_path(self.view)
    if current_path != None: 
      _UrtextProject = focus_urtext_project(current_path, self.view)
    else:
      print('No Urtext Project')
      return None

    if _UrtextProjectList == None:        
      global _UrtextProjectList
      _UrtextProjectList = ProjectList(_UrtextProject.path, _UrtextProject.other_projects)

    return _UrtextProject


class NavigateBackwardCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    if refresh_project(self.view) == None :
      return

    # return if there are no saved locations
    if len( _UrtextProject.navigation) == 0:
      print('There is no nav history')
      return

    print(_UrtextProject.nav_index)

    # return if the index is already at the beginning
    if _UrtextProject.nav_index == 0:
      print('index is already at the beginning.')
      return

    # otherwise, move backwards one
    _UrtextProject.nav_index -= 1

    # and open this node
    last_node = _UrtextProject.navigation[_UrtextProject.nav_index]          
    position = _UrtextProject.nodes[last_node].ranges[0][0]
    open_urtext_node(self.view, last_node, position)

class NavigateForwardCommand(sublime_plugin.TextCommand):
  def run(self, edit):

    if refresh_project(self.view) == None :
      return

    # return if there are no saved locations
    if len( _UrtextProject.navigation) == 0:
      print('There is no more nav history')
      return

    print(_UrtextProject.nav_index)

    # return if the index is already at the end
    if _UrtextProject.nav_index == len(_UrtextProject.navigation) - 1:
      print('index is already at the end.')
      return

    # otherwise move it forward by one
    _UrtextProject.nav_index += 1

    # and open this node
    last_node = _UrtextProject.navigation[_UrtextProject.nav_index]          
    position = _UrtextProject.nodes[last_node].ranges[0][0]
    open_urtext_node(self.view, last_node, position)

class NavigateLastLinkCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    if refresh_project(self.view) == None :
        return

    # return only if there are no saved locations
    if len( _UrtextProject.navigation) == 0: 
      print('There is no more nav history')
      return

    # and open this node
    last_node = _UrtextProject.navigation[_UrtextProject.nav_index]          
    position = _UrtextProject.nodes[last_node].ranges[0][0]
    open_urtext_node(self.view, last_node, position)

