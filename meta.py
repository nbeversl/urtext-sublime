# Urtext
# file metadata handling

# Datestimes -> /Users/nathanielbeversluis/Library/Application Support/Sublime Text 3/Packages/Urtext/datestimes.py

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


meta_separator = '\n------------\n' # = 12 dashes in a row starting a line, followed by a newline
path = '/Users/nathanielbeversluis/Dropbox/txt'

# Needed commands:
# - Check for existing meta DONE <Sun., Jan. 13, 2019, 06:35 PM>
# - Insert meta separator <Sun., Jan. 13, 2019, 06:35 PM>
# - File Created (only for new files) DONE <Sun., Jan. 13, 2019, 06:43 PM>
# - Original filename (only for new files) DONE <Sun., Jan. 13, 2019, 07:28 PM>
# - Meta added : for existing files DONE <Sun., Jan. 13, 2019, 07:31 PM>
# - Filename when meta information added: for existing files
# - File Updated Metadata DONE <Sun., Jan. 13, 2019, 07:34 PM>
# - command to add metadata to an existing file DONE <Sun., Jan. 13, 2019, 07:59 PM>
# - get and parse metadata from existing file into a dict

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




def get_meta(content):
  """
  Reads and parses the metadata at the bottom of the file into a dict by timestamp.
  """  
  if not has_meta(content):
    return None
  raw_meta_data = content.split(meta_separator)[-1]
  metadata = {}
  meta_lines = raw_meta_data.split('\n')
  date_regex = '<(Sat|Sun|Mon|Tue|Wed|Thu|Fri)., (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec). \d{2}, \d{4},\s+\d{2}:\d{2} (AM|PM)>'
  metadata = []
  for line in meta_lines: 
    if line.strip() == '':
      continue
    metadata_entry = {}    
    date_match = re.search(date_regex,line)
    if date_match:
      datestamp_string = date_match.group(0)
      line = line.replace(datestamp_string, '').strip()
      date_stamp = datetime.datetime.strptime(datestamp_string, '<%a., %b. %d, %Y, %I:%M %p>')
    else:
      date_stamp = None
    metadata_entry['datestamp'] = date_stamp

    if ':' in line:
      key = line.split(":")[0]
      value = ''.join(line.split(":")[1:]).strip()
      if ',' in value:
        value = value.split(',')
    else:
      key = '(no_key)'
      value = line

    metadata_entry[key] = value
    metadata.append(metadata_entry)

  return metadata
  print(pprint.pformat(metadata))

class ShowMetadata(sublime_plugin.TextCommand):
  """ Make metadata command available in Sublime command palette """
  def run(self, edit):
    get_meta(self.view.substr(sublime.Region(0, self.view.size())))

class ShowNodeTreeCommand(sublime_plugin.TextCommand):
  """ Display a tree of all nodes connected to this one """
  def run(self, edit):
    oldest_known_filename = self.find_oldest_node(self.view.file_name())
    self.tree = Node(oldest_known_filename)
    self.build_node_tree(oldest_known_filename)
    render = ''
    for pre, fill, node in RenderTree(self.tree):
      render += ("%s-> %s" % (pre, node.name)) + '\n'
    new_view = self.view.window().new_file()
    new_view.run_command("insert_snippet", { "contents": render})

  def find_oldest_node(self, filename):
    """ Locate the oldest node by recursively following 'pulled from' backlinks """
    oldest_known_filename = filename
    with open(filename, 'r', encoding='utf-8') as theFile:
      full_contents = theFile.read()
      theFile.close()
    this_meta = get_meta(full_contents)
    for meta_entry in this_meta:
      if 'pulled from' in meta_entry:
        oldest_known_filename = meta_entry['pulled from'].split(' |')[0].strip(' ->' )
        return self.find_oldest_node(oldest_known_filename)
    return oldest_known_filename

  def build_node_tree(self, oldest_node, parent=None):
    self.tree = Node(oldest_node)
    self.add_children(self.tree)

  def add_children(self, parent):
    """ recursively add children """
    with open(parent.name, 'r', encoding='utf-8') as theFile:
      full_contents = theFile.read()
      theFile.close()
    this_meta = get_meta(full_contents)
    for meta_entry in this_meta:
      if 'pulled to' in meta_entry:
        newer_filename = meta_entry['pulled to'].split(' |')[0].strip(' ->' )
        newer_nodename = Node(newer_filename, parent=parent)
        self.add_children(newer_nodename)

class AddMetaToExistingFile(sublime_plugin.TextCommand):
  """
  Adds metadata to a file that does not already have metadata.
  """
  def run(self, edit):
      if not has_meta(self.view):
        add_separator(self.view)
        timestamp = (datetime.datetime.now().strftime("<%a., %b. %d, %Y, %I:%M %p>"))
        filename = self.view.file_name().split('/')[-1]
        self.view.run_command("move_to", {"to": "eof"})
        self.view.run_command("insert_snippet", { "contents": "Metadata added to existing file: "+timestamp+'\n'})
        self.view.run_command("insert_snippet", { "contents": "Existing filename: "+filename+'\n'})
        self.view.run_command("move_to", {"to": "bof"})

def has_meta(contents):
  """
  Determine whether a view contains metadata.
  """
  global metaseparator
  if meta_separator in contents:
    return True
  else:
    return False

def add_separator(view):
  """
  Adds a metadata separator if one is not already there.
  """
  if not has_meta(view):
    global meta_separator
    view.run_command("move_to", {"to": "eof"})
    view.run_command("insert_snippet", { "contents": "\n\n"+meta_separator})
    view.run_command("move_to", {"to": "bof"})

def add_created_timestamp(view, timestamp):
  """
  Adds an initial "Created: " timestamp
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
