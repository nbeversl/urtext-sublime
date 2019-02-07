# Urtext node metadata handling

import sublime
import sublime_plugin
import os
import re
import datetime
import Urtext.urtext
import pprint
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))
from anytree import Node, RenderTree

# note -> https://forum.sublimetext.com/t/an-odd-problem-about-sublime-load-settings/30335
def get_path(view):
  if view.window().project_data():
    path = view.window().project_data()['urtext_path'] # ? 
  else:
    path = '.'
  return path
settings = sublime.load_settings('urtext-default.sublime-settings')

meta_separator = settings.get('meta_separator') # = 12 dashes in a row starting a line, followed by a newline

class MetadataEntry: # container for a single metadata entry 
  def __init__(self, tag, value, dtstamp):
    self.tag_name = tag
    self.value = value
    self.dtstamp = dtstamp

  def log(self):
    print('tag: %s' % self.tag_name)
    print('value: %s' % self.value)
    print('datetimestamp: %s' % self.dtstamp)

class NodeMetadata: 
  def __init__(self, filename): # always take the metadata from the file, not the view.
    self.entries = []
    self.filename = filename # log the filename as part of the metadata for queries
    try:
      with open(filename, 'r', encoding='utf-8') as theFile:
          full_contents = theFile.read()
          theFile.close()
    except: # file name not exist
      return None

    #necessary?
    if not has_meta(full_contents): # no metadata found
      return None
 
    title_set = False
    raw_meta_data = full_contents.split(meta_separator)[-1]
    meta_lines = raw_meta_data.split('\n')
    date_regex = '<(Sat|Sun|Mon|Tue|Wed|Thu|Fri)., (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec). \d{2}, \d{4},\s+\d{2}:\d{2} (AM|PM)>'

    for line in meta_lines: 
      if line.strip() == '':
        continue
      date_match = re.search(date_regex,line)
      if date_match:
        datestamp_string = date_match.group(0)
        line = line.replace(datestamp_string, '').strip()
        date_stamp = datetime.datetime.strptime(datestamp_string, '<%a., %b. %d, %Y, %I:%M %p>')
      else:
        date_stamp = None
      if ':' in line:
        key = line.split(":")[0]
        value = ''.join(line.split(":")[1:]).strip()
        if ',' in value:
          value = value.split(',')
      else:
        key = '(no_key)'
        value = line
      if key == 'title':
        title_set = True
        title = value
      self.entries.append(MetadataEntry(key, value, date_stamp))

    if not title_set:
      title = full_contents.split('\n')[0]
    self.entries.append(MetadataEntry('title', title, None)) # title defaults to first line. possibly refactor this.
    
  def get_tag(self, tagname):
    """ returns an array of values for the given tagname """ 
    values = []
    for entry in self.entries:
      if entry.tag_name == tagname:
        values.append(entry.value) # allows for multiple tags of the same name
    return values

  def log(self):
    for entry in self.entries:
      entry.log()

  def groups(self): # not used?
    groups_list = []
    for entry in self.entries:
      if entry.tag_name[0] == '_':
        groups_list.append(entry.tag_name)
    return groups_list

class ModifiedCommand(sublime_plugin.TextCommand):
  """
  Adds a modification timestamp to the metadata.
  """
  def run(self, edit):
      if not has_meta(self.view):
        add_separator(self.view)
        self.view.run_command("move_to", {"to": "eof"})
        self.view.run_command("insert_snippet", { "contents": "[ no existing metadata ]\n"})
      timestamp = (datetime.datetime.now().strftime("<%a., %b. %d, %Y, %I:%M %p>"))
      self.view.run_command("move_to", {"to": "eof"})
      self.view.run_command("insert_snippet", { "contents": "Modified: "+timestamp+'\n'})
      self.view.run_command("move_to", {"to": "bof"})

class ShowMetadata(sublime_plugin.TextCommand):
  """ Make metadata command available in Sublime command palette """
  def run(self, edit):
    filename = self.view.file_name()
    print(NodeMetadata(filename).log_metadata())

class ShowNodeTreeCommand(sublime_plugin.TextCommand):
  """ Display a tree of all nodes connected to this one """
  # to add:
  #   move cursor to the file this was called from

  def run(self, edit):
    self.errors = []   
    oldest_known_filename = self.find_oldest_node(self.view.file_name())
    self.tree = Node(oldest_known_filename)
    self.build_node_tree('ROOT -> ' + oldest_known_filename)
    render = ''
    for pre, fill, node in RenderTree(self.tree):
      render += ("%s-> %s" % (pre, node.name)) + '\n'
    window = self.view.window()
    window.focus_group(0) # always show the tree on the leftmost focus
    new_view = self.view.window().new_file()
    new_view.run_command("insert_snippet", { "contents": render})
    new_view.run_command("insert_snippet", { "contents": '\n'.join(self.errors)})

  def find_oldest_node(self, filename):
    """ Locate the oldest node by recursively following 'pulled from' backlinks """
    oldest_known_filename = filename
    this_meta = NodeMetadata(filename)
    if this_meta.get_tag('pulled from'): # 0 = always use first value. should not be pulled from more than one place.
      oldest_known_filename = this_meta.get_tag('pulled from')[0].split(' |')[0].strip(' ->' )
      return self.find_oldest_node(oldest_known_filename)
    return oldest_known_filename

  def build_node_tree(self, oldest_node, parent=None):
    self.tree = Node(oldest_node)
    self.add_children(self.tree)

  def add_children(self, parent):
    """ recursively add children """
    parent_filename = parent.name.split('->')[1].strip()
    try:
      this_meta = NodeMetadata(parent_filename)
    except:
      self.errors.append('Broken link: -> %s\n' % parent_filename)
      return
    for entry in this_meta.entries:
      if entry.tag_name == 'pulled to':
        newer_filename = entry.value.split(' |')[0].strip(' ->' )
        newer_metadata = NodeMetadata(newer_filename)
        newer_nodename = Node(newer_metadata.get_tag('title')[0] + ' -> ' + newer_filename, parent=parent)
        self.add_children(newer_nodename)

class AddMetaToExistingFile(sublime_plugin.TextCommand):
  """ Add metadata to a file that does not already have metadata.  """
  def run(self, edit):
      if not has_meta(self.view):
        add_separator(self.view)
        timestamp = (datetime.datetime.now().strftime("<%a., %b. %d, %Y, %I:%M %p>"))
        filename = self.view.file_name().split('/')[-1]
        self.view.run_command("move_to", {"to": "eof"})
        self.view.run_command("insert_snippet", { "contents": "Metadata added to existing file: "+timestamp+'\n'})
        self.view.run_command("insert_snippet", { "contents": "Existing filename: "+filename+'\n'})
        self.view.run_command("move_to", {"to": "bof"})

class ShowTagsCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    self.found_tags = []
    self.tagged_files = {}
    path = get_path(self.view)
    print(path)
    files = os.listdir(path) #migrate this to pull from project settings
    for file in files:
      if file[-4:] == '.txt':
        metadata = NodeMetadata(path + '/' + file)
        for tag in metadata.get_tag('tags'):
          if isinstance(tag, str):
            tag = [ tag ]
          for item in tag:
            if item not in self.found_tags: # this is incredibly ugly code. Redo it.
              self.found_tags.append(item)
              self.tagged_files[item] = []
            self.tagged_files[item].append(metadata) # append the full file so title can be shown with filename
    self.view.window().show_quick_panel(self.found_tags, self.list_files)

  def list_files(self, selected_tag):
    tag = self.found_tags[selected_tag]
    new_view = self.view.window().new_file()
    new_view.run_command("insert_snippet", { "contents": '\nFiles found for tag: %s\n\n' % tag})
    for file in self.tagged_files[tag]:
      file.log()
      listing = '\n\t -> ' + file.filename + '  |  ' + file.get_tag('title')[0]      
      new_view.run_command("insert_snippet", { "contents": listing})       

def has_meta(contents):
  """ 
  Determine whether a view contains metadata. 
  :contents: -- the full contents of a file or fragment
  """
  global metaseparator
  if meta_separator in contents:
    return True
  else:
    return False

def add_separator(view):
  """
  Adds a metadata separator if one is not already there.
  :view: a Sublime view
  """
  if not has_meta(view):
    global meta_separator
    view.run_command("move_to", {"to": "eof"})
    view.run_command("insert_snippet", { "contents": "\n\n"+meta_separator})
    view.run_command("move_to", {"to": "bof"})

def add_created_timestamp(view, timestamp):
  """
  Adds an initial "Created: " timestamp
  view: Sublime view
  timestamp: a datetime.datetime object
  """
  filename = view.file_name().split('/')[-1]
  text_timestamp = timestamp.strftime("<%a., %b. %d, %Y, %I:%M %p>")
  view.run_command("move_to", {"to": "eof"})
  view.run_command("insert_snippet", { "contents": "\n\n"+meta_separator+"Created "+text_timestamp+'\n'})
  view.run_command("move_to", {"to": "bof"})

def add_original_filename(view):
  """
  Adds an initial "Original Filename: " metadata stamp
  """
  filename = view.file_name().split('/')[-1]
  view.run_command("move_to", {"to": "eof"})
  view.run_command("insert_snippet", { "contents": "Original filename: "+filename+'\n'})
  view.run_command("move_to", {"to": "bof"})

def clear_meta(contents):
  global meta_separator
  return contents.split(meta_separator)[0]
