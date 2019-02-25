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
    new_filename = self.index + ' '+ self.title + ' ' + self.node_number + '.txt'
    os.rename(os.path.join(self.path, old_filename), os.path.join(self.path, new_filename))
    self.filename = new_filename
    return new_filename

class RenameFileCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    path = get_path(self.view.window())
    filename = self.view.file_name()
    metadata = Urtext.meta.NodeMetadata(os.path.join(path,filename))
    metadata.log()
    title = metadata.get_tag('title')[0].strip()
    index = metadata.get_tag('index')[0]
    file = UrtextFile(filename)
    file.set_title(title)
    file.set_index(index)
    old_filename = file.filename
    new_filename = file.rename_file()
    v = self.view.window().find_open_file(old_filename)
    if v:
      v.retarget(os.path.join(path,new_filename))

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
      #https://stackoverflow.com/questions/3269293/how-to-write-a-check-in-python-to-see-if-file-is-valid-utf-8
      print("%s invalid utf-8" % file)  
    except:
      print('some other error with %s' % file)
  return urtext_files


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
          try:
            item.append(metadata.get_tag('title')[0])  # should title be a list or a string? 
            node_id = re.search(r'\b\d{14}\b', filename).group(0) # refactor later
            item.append(Urtext.datestimes.date_from_reverse_date(node_id))
            item.append(metadata.filename)
            menu.append(item)
          except:
            print(filename)
        self.sorted_menu = sorted(menu,key=lambda item: item[1], reverse=True )
        self.display_menu = []
        for item in self.sorted_menu: # there is probably a better way to copy this list.
          new_item = [item[0], item[1].strftime('<%a., %b. %d, %Y, %I:%M %p>')]
          self.display_menu.append(new_item)
        def open_the_file(index):
          if index != -1:
            print(self.sorted_menu[index][2])
            urtext_file = UrtextFile(self.sorted_menu[index][2])
            new_view = self.window.open_file(self.sorted_menu[index][2])
        self.window.show_quick_panel(self.display_menu, open_the_file)

class LinkToNodeCommand(sublime_plugin.WindowCommand): # almost the same code as show files. Refactor.
    def run(self):
        files = get_all_files(self.window)
        menu = []
        for filename in files:
          item = []       
          try:
            metadata = Urtext.meta.NodeMetadata(os.join.path(get_path(self.window), filename))
            item.append(metadata.get_tag('title')[0])  # should title be a list or a string?            
            item.append(Urtext.datestimes.date_from_reverse_date(filename[:13]))
            item.append(metadata.filename)
            menu.append(item)
          except:
            pass # probably not a .txt file
        self.sorted_menu = sorted(menu,key=lambda item: item[1], reverse=True )
        self.display_menu = []
        for item in self.sorted_menu: # there is probably a better way to copy this list.
          new_item = [item[0], item[1].strftime('<%a., %b. %d, %Y, %I:%M %p>')]
          self.display_menu.append(new_item)
        def link_to_the_file(index):
          view = self.window.active_view()
          file = self.sorted_menu[index][2].split('/')[-1]
          title = self.sorted_menu[index][0]
          view.run_command("insert", {"characters": title + ' -> '+ file + ' | '})
        self.window.show_quick_panel(self.display_menu, link_to_the_file)

def get_contents(view):
  contents = view.substr(sublime.Region(0, self.view.size()))
  return contents
