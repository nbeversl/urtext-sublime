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

def get_path(window):
  """ Returns the Urtext path from settings """
  if window.project_data():
    path = window.project_data()['urtext_path'] # ? 
  else:
    path = '.'
  return path

def get_all_files(window):
  """ Get all files in the Urtext Project. Returns an array without file path. """
  path = get_path(window)
  files = os.listdir(path)
  urtext_files = []
  regexp = re.compile(r'\b\d{14}\b')
  for file in files:
    try:
      f = codecs.open(os.path.join(path, file), encoding='utf-8', errors='strict')
      for line in f:
          pass
      if regexp.search(file):  
        urtext_files.append(file)
    except UnicodeDecodeError:
      print("Urtext Skipping %s, invalid utf-8" % file)  
    except:
      print('Urtext Skipping %s' % file)
  return urtext_files

class UrtextFile:
  def __init__(self, filename):
    self.path = os.path.dirname(filename)
    self.filename = os.path.basename(filename)
    self.node_number = re.search(r'\b\d{14}\b|$',filename).group(0)
    self.index = re.search(r'^\d{2}\b|$', filename).group(0)
    self.title = re.search(r'[^\d]+|$',filename).group(0).strip()
    self.log()

  def set_index(self, new_index):
    self.index = new_index

  def set_title(self, new_title):
    self.title = new_title

  def log(self):
    logging.info(self.node_number)
    logging.info(self.title)
    logging.info(self.index)
    logging.info(self.filename)

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

class RenameFileCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    path = get_path(self.view.window())
    filename = self.view.file_name()
    metadata = Urtext.meta.NodeMetadata(os.path.join(path,filename))
    file = UrtextFile(filename)
    if metadata.get_tag('title') != 'Untitled':
      title = metadata.get_tag('title')[0].strip()
      file.set_title(title)
    if metadata.get_tag('index') != []:
      print('setting new index')
      index = metadata.get_tag('index')[0].strip()
      file.set_index(index)
    old_filename = file.filename
    new_filename = file.rename_file()
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
        path = get_path(self.window)
        files = get_all_files(self.window)
        menu = []
        for filename in files:
          item = []
          metadata = Urtext.meta.NodeMetadata(os.path.join(path, filename))
          item.append(metadata.get_tag('title')[0])  # should title be a list or a string? 
          node_id = re.search(r'\b\d{14}\b', filename).group(0) # refactor later
          print(node_id)
          item.append(Urtext.datestimes.date_from_reverse_date(node_id))
          item.append(metadata.filename)
          menu.append(item)
        self.sorted_menu = sorted(menu,key=lambda item: item[1], reverse=True )
        self.display_menu = []
        for item in self.sorted_menu: # there is probably a better way to copy this list.
          new_item = [item[0], item[1].strftime('<%a., %b. %d, %Y, %I:%M %p>')]
          self.display_menu.append(new_item)
        def open_the_file(index):
          if index != -1:
            urtext_file = UrtextFile(self.sorted_menu[index][2])
            new_view = self.window.open_file(self.sorted_menu[index][2])
        self.window.show_quick_panel(self.display_menu, open_the_file)

class LinkToNodeCommand(sublime_plugin.WindowCommand): # almost the same code as show files. Refactor.
    def run(self):
        files = get_all_files(self.window)
        menu = []
        for filename in files:
          item = []       
          file_info = UrtextFile(filename)
          metadata = Urtext.meta.NodeMetadata(os.path.join(get_path(self.window), file_info.filename))
          item.append(metadata.get_tag('title')[0])  # should title be a list or a string?  
          item.append(Urtext.datestimes.date_from_reverse_date(file_info.node_number))
          item.append(metadata.filename)
          menu.append(item)
        self.sorted_menu = sorted(menu,key=lambda item: item[1], reverse=True )
        self.display_menu = []
        for item in self.sorted_menu: # there is probably a better way to copy this list.
          new_item = [item[0], item[1].strftime('<%a., %b. %d, %Y, %I:%M %p>')]
          self.display_menu.append(new_item)
        def link_to_the_file(index):
          view = self.window.active_view()
          file = self.sorted_menu[index][2]
          title = self.sorted_menu[index][0]
          view.run_command("insert", {"characters": title + ' -> '+ file_info.filename + ' | '})
        self.window.show_quick_panel(self.display_menu, link_to_the_file)

def get_contents(view):
  contents = view.substr(sublime.Region(0, self.view.size()))
  return contents
