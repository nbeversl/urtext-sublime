# Urtext
# file metadata handling

# Datestimes -> /Users/nathanielbeversluis/Library/Application Support/Sublime Text 3/Packages/Urtext/datestimes.py

import sublime
import sublime_plugin
import os
import re
import datetime

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

def has_meta(view):
  global metaseparator
  contents = Urtext.get_contents()
  if meta_separator in contents:
    return True
  else:
    return False

def add_separator(view):
  if not has_meta(view):
    contents += "\n\n"+meta_separator
    pass

def add_created_timestamp(view):
    filename = view.file_name().split('/')[-1]
    timestamp = (datetime.datetime.now().strftime("<%a., %b. %d, %Y, %I:%M %p>"))
    view.run_command("move_to", {"to": "eof"})
    view.run_command("insert_snippet", { "contents": "\n\n"+meta_separator+"Created "+timestamp+'\n'})
    view.run_command("move_to", {"to": "bof"})

def add_original_filename(view):
    filename = view.file_name().split('/')[-1]
    view.run_command("move_to", {"to": "eof"})
    view.run_command("insert_snippet", { "contents": "Original filename: "+filename+'\n'})
    view.run_command("move_to", {"to": "bof"})


class ModifiedCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        timestamp = (datetime.datetime.now().strftime("<%a., %b. %d, %Y, %I:%M %p>"))
        self.view.run_command("move_to", {"to": "eof"})
        self.view.run_command("insert_snippet", { "contents": "Modified: "+timestamp+'\n'})
        self.view.run_command("move_to", {"to": "bof"})

class ExistingFilename(sublime_plugin.TextCommand):
    def run(self, edit):
        timestamp = (datetime.datetime.now().strftime("<%a., %b. %d, %Y, %I:%M %p>"))
        filename = view.file_name().split('/')[-1]
        self.view.run_command("move_to", {"to": "eof"})
        self.view.run_command("insert_snippet", { "contents": "Metadata added to existing file: "+timestamp+'\n'})
        self.view.run_command("insert_snippet", { "contents": "Existing filename: "+timestamp+'\n'})
        self.view.run_command("move_to", {"to": "bof"})


#------- OLD STUFF
"""
def clear_meta(contents):
  global metaseparator
  if has_meta(contents):
    contents = contents.split(meta_separator)[0]
  return contents

def add_file_modified_meta(view): 
  timestamp = (datetime.now().strftime("<%a., %b. %d, %Y, %I:%M %p>"))
  view.run_command("move_to", {"to": "eof"})
  view.run_command("insert_snippet", { "contents": "\nModified: "+timestamp})
  view.run_command("move_to", {"to": "bof"})
  return

  def add_content(self, view): #https://forum.sublimetext.com/t/wait-until-is-loading-finnish/12062/5
      if not view.is_loading():
        view.run_command("insert_snippet", { "contents": self.contents})
        add_file_created_meta(view)
        view.run_command("move_to", {"to": "eof"})
        view.run_command("insert_snippet", { "contents": "\nForked from: "+self.old_filename + " (editorial://open/"+self.old_filename+"?root=dropbox)"})
        view.run_command("move_to", {"to": "bof"})
        view.run_command('save')
      else:
        sublime.set_timeout(lambda: self.add_content(view), 10)
"""
