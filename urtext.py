# Urtext - Main
import sublime
import sublime_plugin
import os
import re
import Urtext.datestimes
import Urtext.meta
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))
from anytree import Node, RenderTree
import codecs
import logging

# note -> https://forum.sublimetext.com/t/an-odd-problem-about-sublime-load-settings/30335

_UrtextProject = None

class Project:
  def __init__(self, window):
    self.path = get_path(window)
    self.window = window
    self.nodes = {}
    files = os.listdir(self.path)
    regexp = re.compile(r'\b\d{14}\b')
    for file in files:
      try:
        f = codecs.open(os.path.join(self.path, file), encoding='utf-8', errors='strict')
        for line in f:
            pass
        if regexp.search(file):  
          thisfile = UrtextNode(os.path.basename(file), window)
          if thisfile.node_number not in self.nodes:
            self.nodes[thisfile.node_number] = thisfile
      except UnicodeDecodeError:
        print("Urtext Skipping %s, invalid utf-8" % file)  
      except:
        print('Urtext Skipping %s' % file)   
    print('URtext has %d files' % len(self.nodes))
    self.build_tag_info()

  def get_file_name(self, node_id):
    for node in self.nodes:
      if node == node_id:
        return self.nodes[node].filename
    return None

  def from_file_name(self, node_id):
    for node in self.nodes:
      if node == node_id:
        return self.nodes[node]
    return None


  def get_node_id(self, filename):
    for node in self.nodes:
      if self.nodes[node].filename == filename:
        return node
    return None

  def get_all_files(self):
    all_files = []
    for node in self.nodes:
      all_files.append(self.nodes[node].filename)
    return all_files

  def unindexed_nodes(self):
    """ returns an array of node IDs of unindexed nodes, in reverse order (most recent) by Node ID """

    unindexed_nodes = []
    for node_id in self.nodes:
      if self.nodes[node_id].metadata.get_tag('index') == []:
        unindexed_nodes.append(node_id)
    sorted_unindexed_nodes = sorted(unindexed_nodes)
    return sorted_unindexed_nodes

  def indexed_nodes(self):
    """ returns an array of node IDs of indexed nodes, in indexed order """
    indexed_nodes = []
    for node in self.nodes:
      if self.nodes[node].metadata.get_tag('index') != []:
          indexed_nodes.append([node, self.nodes[node].metadata.get_tag('index')[0]])
    sorted_indexed_nodes = sorted(indexed_nodes, key=lambda item: item[1])
    for i in range(len(sorted_indexed_nodes)):
      sorted_indexed_nodes[i] = sorted_indexed_nodes[i][0]
    return sorted_indexed_nodes

  def build_tag_info(self):
    self.tagnames = {}
    for node in self.nodes:
      for entry in self.nodes[node].metadata.entries:
        if entry.tag_name.lower() != 'title': 
          if entry.tag_name not in self.tagnames:
            self.tagnames[entry.tag_name] = {}
          if not isinstance(entry.value, list):
            entryvalues = [entry.value]
          else:
            entryvalues = entry.value
          for value in entryvalues:
            if value not in self.tagnames[entry.tag_name]:
              self.tagnames[entry.tag_name][value] = []
            self.tagnames[entry.tag_name][value].append(node)

def refresh_nodes(window):
  global _UrtextProject 
  if _UrtextProject == None:
    _UrtextProject = Project(window)  

def get_path(window):
  """ Returns the Urtext path from settings """
  if window.project_data():
    path = window.project_data()['urtext_path'] # ? 
  else:
    path = '.'
  return path

class UrtextNode:
  """ Takes a filename without path, gets path from the project settings """
  def __init__(self, filename, window):
    self.path = get_path(window)
    self.filename = filename
    self.node_number = re.search(r'(\d{14})',filename).group(0)
    self.title = re.search(r'[^\d]+|$',filename).group(0)
    self.metadata = Urtext.meta.NodeMetadata(os.path.join(self.path, self.filename))
    self.index = self.metadata.get_tag('index')

  def set_index(self, new_index):
    self.index = new_index

  
  def set_title(self, new_title):
    self.title = new_title

  def log(self):
    logging.info(self.node_number)
    logging.info(self.title)
    logging.info(self.index)
    logging.info(self.filename)
    logging.info(self.metadata.log())

  def rename_file(self):
    old_filename = self.filename
    if len(self.index) > 0:
      new_filename = self.index + ' '+ self.title + ' ' + self.node_number + '.txt'
    elif self.title != 'Untitled':
      new_filename = self.node_number + ' ' + self.title + '.txt'
    else:
      new_filename = old_filename
    os.rename(os.path.join(self.path, old_filename), os.path.join(self.path, new_filename))
    self.filename = new_filename
    return new_filename

  def contents(self):
    with open(os.path.join(self.path, self.filename),'r',encoding='utf-8') as theFile:
      full_contents = theFile.read()
    theFile.close()
    return full_contents

class UrtextSave(sublime_plugin.EventListener):
  def on_post_save(self, view):
    file = UrtextNode(os.path.basename(view.file_name()), view.window())
    global _Urtext_Files
    _UrtextProject.nodes[file.node_number] = file

class RenameFileCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    path = Urtext.urtext.get_path(self.view.window())
    filename = self.view.file_name()
    node = _UrtextProject.get_node_id(os.path.basename(filename))
    title = _UrtextProject.nodes[node].metadata.get_tag('title')[0].strip()
    index = _UrtextProject.nodes[node].metadata.get_tag('index')
    if index != []:
       _UrtextProject.nodes[node].set_index(index)     
    _UrtextProject.nodes[node].set_title(title)
    old_filename = filename
    new_filename = _UrtextProject.nodes[node].rename_file()
    v = self.view.window().find_open_file(old_filename)
    if v:
      v.retarget(os.path.join(path,new_filename))
      v.set_name(new_filename)


class CopyPathCoolerCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    filename = self.view.window().extract_variables()['file_name']
    self.view.show_popup('`'+filename + '` copied to the clipboard')
    sublime.set_clipboard(filename)

class ShowFilesWithPreview(sublime_plugin.WindowCommand):
    def run(self):
      show_panel(self.window, self.open_the_file)

    def open_the_file(self, filename):
      path = get_path(self.window)
      new_view = self.window.open_file(os.path.join(path,filename))

class LinkToNodeCommand(sublime_plugin.WindowCommand): # almost the same code as show files. Refactor.
    def run(self):
      show_panel(self.window, self.link_to_the_file)

    def link_to_the_file(self, filename):
      view = self.window.active_view()
      filename = os.path.basename(filename)
      view.run_command("insert", {"characters": ' -> '+ filename + ' | '})

class LinkNodeFromCommand(sublime_plugin.WindowCommand): # almost the same code as show files. Refactor.
    def run(self):
      self.current_file = os.path.basename(self.window.active_view().file_name())
      show_panel(self.window, self.link_from_the_file)

    def link_from_the_file(self, filename):
        new_view = self.window.open_file(filename)
        sublime.set_clipboard(' -> ' + self.current_file)
        self.show_tip(new_view)

    def show_tip(self, view):
      if not view.is_loading(): 
        view.show_popup('Link to ' + self.current_file + ' copied to the clipboard')
      else:
        sublime.set_timeout(lambda: self.show_tip(view), 10)
      
def show_panel(window, main_callback):
  refresh_nodes(window)
  menu = []
  for node_id in _UrtextProject.indexed_nodes():
    item = []
    metadata = _UrtextProject.nodes[node_id].metadata
    item.append(metadata.get_tag('title')[0])  # should title be a list or a string? 
    item.append(Urtext.datestimes.date_from_reverse_date(node_id))
    item.append(_UrtextProject.nodes[node_id].filename)
    menu.append(item)
  for node_id in _UrtextProject.unindexed_nodes():
    item = []
    metadata = _UrtextProject.nodes[node_id].metadata
    item.append(metadata.get_tag('title')[0])  # should title be a list or a string? 
    item.append(Urtext.datestimes.date_from_reverse_date(node_id))
    item.append(_UrtextProject.nodes[node_id].filename)
    menu.append(item)
  display_menu = []
  for item in menu: # there is probably a better way to copy this list.
    new_item = [item[0], item[1].strftime('<%a., %b. %d, %Y, %I:%M %p>')]
    display_menu.append(new_item)

  def private_callback(index):
    main_callback(menu[index][2])

  window.show_quick_panel(display_menu, private_callback)

def get_contents(view):
  contents = view.substr(sublime.Region(0, self.view.size()))
  return contents

class ShowAllNodesCommand(sublime_plugin.TextCommand):
  def run(self,edit):
    refresh_nodes(self.view.window())
    new_view = self.view.window().new_file()
    for node_id in _UrtextProject.indexed_nodes():
      title = _UrtextProject.nodes[node_id].metadata.get_tag('title')[0]
      new_view.run_command("insert", {"characters": '-> ' + title + ' ' + node_id + '\n'})
    for node_id in _UrtextProject.unindexed_nodes():
      title = _UrtextProject.nodes[node_id].metadata.get_tag('title')[0]
      new_view.run_command("insert", {"characters": '-> ' + title + ' ' + node_id + '\n'})
      
class DeleteThisNodeCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        window = sublime.active_window()
        view = sublime.Window.active_view(window)
        file_name = view.file_name()
        message = "Are you sure you want to delete '{}'?"
        message = message.format(file_name)
    
        if not sublime.ok_cancel_dialog(message):
            return
        if view.is_dirty():
            view.set_scratch(True)
        window.run_command('close_file')

        if (file_name is not None and os.path.isfile(file_name)):
            node_id = _UrtextProject.get_node_id(os.path.basename(file_name))
            os.remove(file_name)
            _UrtextProject.nodes.pop(node_id)

