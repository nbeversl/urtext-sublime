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
