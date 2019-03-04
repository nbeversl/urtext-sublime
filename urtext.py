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

_Urtext_Nodes = {}

class NodeList:
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
          thisfile = UrtextFile(os.path.basename(file), window)
          if thisfile.node_number not in self.nodes:
            self.nodes[thisfile.node_number] = thisfile
      except UnicodeDecodeError:
        print("Urtext Skipping %s, invalid utf-8" % file)  
      except:
        print('Urtext Skipping %s' % file)   
    print('URtext has %d files' % len(self.nodes))

  def get_file_name(self, node_id):
    for node in self.nodes:
      if node == node_id:
        print(node)
        return self.nodes[node].filename
    return None

  def get_node_id(self, filename):
    for node in self.nodes:
      if self.nodes[node].filename == filename:
        print(node)
        return node
    return None


def refresh_nodes(window):
  global _Urtext_Nodes 
  if _Urtext_Nodes == {}: # needs better logic
    _Urtext_Nodes = NodeList(window)

def get_file_from_node(node, window):
  files = get_all_files(window)
  for file in files:
    if node in file:
      return file
  return None

def get_path(window):
  """ Returns the Urtext path from settings """
  if window.project_data():
    path = window.project_data()['urtext_path'] # ? 
  else:
    path = '.'
  return path

class UrtextFile:
  """ Takes a filename without path, gets path from the project settings """
  def __init__(self, filename, window):
    self.path = get_path(window)
    self.filename = filename
    self.node_number = re.search(r'(\d{14})',filename).group(0)
    self.index = re.search(r'^\d{2}\b|$', filename).group(0)
    self.title = re.search(r'[^\d]+|$',filename).group(0)
    self.metadata = Urtext.meta.NodeMetadata(os.path.join(self.path, self.filename))

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
    file = UrtextFile(os.path.basename(view.file_name()), view.window())
    global _Urtext_Files
    _Urtext_Nodes.nodes[file.node_number] = file

class RenameFileCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    path = get_path(self.view.window())
    filename = self.view.file_name()
    file = UrtextFile(filename, self.view.window())
    if file.metadata.get_tag('title') != 'Untitled':
      title = file.metadata.get_tag('title')[0].strip()
      file.set_title(title)
    if file.metadata.get_tag('index') != []:
      print('setting new index')
      index = file.metadata.get_tag('index')[0].strip()
      file.set_index(index)
    old_filename = file.filename
    new_filename = file.rename_file()
    _Urtext_Nodes[file.node_number] = file
    v = self.view.window().find_open_file(old_filename)
    if v:
      v.retarget(os.path.join(path,new_filename))

class CopyPathCoolerCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    filename = self.view.window().extract_variables()['file_name']
    self.view.show_popup('`'+filename + '` copied to the clipboard')
    sublime.set_clipboard(filename)

class ShowFilesWithPreview(sublime_plugin.WindowCommand):
    def run(self):     
      show_panel(self.window, self.open_the_file)

    def open_the_file(self, filename):
      new_view = self.window.open_file(filename)

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
  for node_id in _Urtext_Nodes.nodes:
    item = []
    metadata = _Urtext_Nodes.nodes[node_id].metadata
    item.append(metadata.get_tag('title')[0])  # should title be a list or a string? 
    item.append(Urtext.datestimes.date_from_reverse_date(node_id))
    item.append(metadata.filename)
    menu.append(item)
  sorted_menu = sorted(menu,key=lambda item: item[1], reverse=True )
  display_menu = []
  for item in sorted_menu: # there is probably a better way to copy this list.
    new_item = [item[0], item[1].strftime('<%a., %b. %d, %Y, %I:%M %p>')]
    display_menu.append(new_item)
  def private_callback(index):
    main_callback(sorted_menu[index][2])
  window.show_quick_panel(display_menu, private_callback)

def get_contents(view):
  contents = view.substr(sublime.Region(0, self.view.size()))
  return contents

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
            node_id = _Urtext_Nodes.get_node_id(os.path.basename(file_name))
            print(os.path.basename(file_name))
            print(node_id)
            os.remove(file_name)
            _Urtext_Nodes.nodes.pop(node_id)

