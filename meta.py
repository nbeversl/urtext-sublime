# Urtext
# file metadata handling

# Datestimes -> /Users/nathanielbeversluis/Library/Application Support/Sublime Text 3/Packages/Urtext/datestimes.py

import sublime
import sublime_plugin
import os
import re
import datetime
import Urtext.urtext

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

def get_meta(view):
  """
  Reads and parses the metadata at the bottom of the file into a dict by timestamp.

  """  
  if not has_meta(view):
    return None
  content = Urtext.urtext.get_contents(view)
  raw_meta_data = content.split(meta_separator)[-1]
  metadata = {}
  meta_lines = raw_meta_data.split('\n')
  print(meta_lines)
  undated_message_key = 1
  existing_keys =[]
  for line in meta_lines:
    try:
      key = datetime.datetime.strptime(line[:31], '<%a., %b. %d, %Y, %I:%M %p>')
      message = line[32:]
      while key in existing_keys:
        key = key + datetime.timedelta(seconds=1) # seconds are used as an index
    except:
      key = "undated_message_" + str(undated_message_key)
      undated_message_key += 1;
      message = line
    if message.strip() != '':
      metadata[key] = message
      existing_keys.append(key)
  print(metadata)
  return metadata

def get_meta_old(view):
  """
  Reads and parses the metadata at the bottom of the file into a dict by timestamp.
  """  
  if not has_meta(view):
    return None
  content = Urtext.urtext.get_contents(view)
  raw_meta_data = content.split(meta_separator)[-1]
  metadata = {}
  found_keys = []
  meta_lines = raw_meta_data.split('\n')
  for line in meta_lines:
    key = line.split(':')[0].strip()
    value = ''.join(line.split(':',1)[1:]).strip()
    index = 1
    sanitized_key = key
    while key in found_keys:
      sanitized_key = key + str(index)
      index += 1
    key = sanitized_key
    if key.strip() != '':
      found_keys.append(sanitized_key)
      metadata[sanitized_key] = value
  print(metadata)
  return metadata

class ShowMetadata(sublime_plugin.TextCommand):
  """
  Make metadata command available in Sublime command palette
  """
  def run(self, edit):
    get_meta(self.view)


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

def has_meta(view):
  """
  Determine whether a view contains metadata.
  """
  global metaseparator
  contents = Urtext.urtext.get_contents(view)
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
