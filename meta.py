# Urtext node metadata handling

import sublime
import sublime_plugin
import os
import re
import datetime
import Urtext.urtext as Urtext
import pprint
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))

from anytree import Node, RenderTree
import anytree
import logging

def meta_separator():
    settings = sublime.load_settings('urtext-default.sublime-settings')
    meta_separator = settings.get('meta_separator') 
    return meta_separator

class MetadataEntry: # container for a single metadata entry 
  def __init__(self, tag, value, dtstamp):
    self.tag_name = tag.strip()
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
 
    title_set = False
    raw_meta_data = full_contents.split(meta_separator())[-1]
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
        if '|' in value:
          items = value.split('|')
          value = []
          for item in items:
             value.append(item.strip())
      else:
        key = '(no_key)'
        value = line
      if key == 'title':
        title_set = True
        title = value
      self.entries.append(MetadataEntry(key, value, date_stamp))

    if title_set == False: # title is the the first many lines if not set
      full_contents = full_contents.strip()
      title = full_contents.split('\n')[0]
      first_line = full_contents[:150] # not used now 
      first_line = first_line.split('------------')[0] # not used now 
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
      render += ("%s %s" % (pre, node.name)) + '\n'
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
    path = Urtext.get_path(self.view.window())
    parent_filename = parent.name.split('->')[1].strip()
    try:
      this_meta = NodeMetadata(os.path.join(path, parent_filename))
    except:
      self.errors.append('Broken link: -> %s\n' % parent_filename)
      return
    for entry in this_meta.entries:
      if entry.tag_name == 'pulled to':
        newer_filename = entry.value.split(' |')[0].strip(' ->' )
        newer_metadata = NodeMetadata(newer_filename)
        newer_nodename = Node(newer_metadata.get_tag('title')[0] + ' -> ' + newer_filename, parent=parent)
        self.add_children(newer_nodename)

class ShowFileRelationshipsCommand(sublime_plugin.TextCommand):
  """ Display a tree of all nodes connected to this one """
  # TODO: for files that link to the same place more than one time,
  # show how many times on one tree node, instead of showing multiple nodes
  # would this require building the tree after scanning all files?
  
  def run(self, edit):
    self.path = Urtext.get_path(self.view.window())
    self.errors = [] 
    self.visited_files = []
    self.backward_visited_files = []
    self.tree = Node(self.view.file_name())

    root_file = Urtext.UrtextFile(os.path.join(self.path, self.view.file_name()))
    root_meta = NodeMetadata(os.path.join(self.path, root_file.filename))
    self.build_node_tree(root_meta.get_tag('title')[0] + ' -> ' + root_file.filename)
    self.build_backward_node_tree(root_meta.get_tag('title')[0] + ' -> ' + root_file.filename)
    
    window = self.view.window()
    window.focus_group(0) # always show the tree on the leftmost focus'
    new_view = self.view.window().new_file()

    render = ''
    for pre, fill, node in RenderTree(self.backward_tree):
      render += ("%s%s" % (pre, node.name)) + '\n'
    render = render.replace('└','┌')    
    render = render.split('\n')
    render = render[1:]
    render_upside_down = ''
    for index in range(len(render)):
      render_upside_down += render[len(render)-1 - index] + '\n'
    render_upside_down = ''.join(render_upside_down)
    new_view.run_command("insert_snippet", { "contents": render_upside_down})
    new_view.run_command("insert_snippet", { "contents": '\n'.join(self.errors)})

    render = ''
    for pre, fill, node in RenderTree(self.tree):
      render += ("%s%s" % (pre, node.name)) + '\n'
    
    new_view.run_command("insert_snippet", { "contents": render})
    new_view.run_command("insert_snippet", { "contents": '\n'.join(self.errors)})
    new_view.set_scratch(True)
    
  def build_node_tree(self, oldest_node, parent=None):
      self.tree = Node(oldest_node)
      self.add_children(self.tree)

  def get_file_links_in_file(self,filename):
      with open(os.path.join(self.path, filename),'r',encoding='utf-8') as this_file:
        contents = this_file.read()
      links = re.findall('->\s+(?!http)([\w\.\/]+)',contents) # link RegEx
      return links
 
  def add_children(self, parent):
    """ recursively add children """
    parent_filename = parent.name.split('->')[1].strip()
    links = self.get_file_links_in_file(parent_filename)
    self.visited_files = []
    for link in links:
      if link in self.visited_files:
        child_metadata = NodeMetadata(os.path.join(self.path, link))
        child_nodename = Node(' ... ' + child_metadata.get_tag('title')[0] + ' -> ' + link, parent=parent)
        continue
      self.backward_visited_files.append(link)
      self.visited_files.append(link)
      link = link.split('/')[-1]
      child_metadata = NodeMetadata(os.path.join(self.path, link))
      child_nodename = Node(child_metadata.get_tag('title')[0] + ' -> ' + link, parent=parent)
      self.add_children(child_nodename) # bug fix here

  def build_backward_node_tree(self, oldest_node, parent=None):
      self.backward_tree = Node(oldest_node)
      self.add_backward_children(self.backward_tree)

  def get_links_to_file(self, filename):
      visited_files = []    
      if filename == '':
        return []
      files =Urtext.get_all_files(self.view.window())
      links_to_file = []
      for file in files:
        if file[-4:] == '.txt':
            with open(os.path.join(self.path, file),'r',encoding='utf-8') as this_file:
              try:
                contents = this_file.read() # in case there's a binary file in there or something.
              except:
                continue
              links = re.findall('-> '+ filename.replace('.txt',''), contents) # link RegEx
              for link in links:
                links_to_file.append(file)
      return links_to_file

  def add_backward_children(self, parent):
    visited_files = []    
    print(parent)
    parent_filename = parent.name.split('->')[1].strip()
    print(parent_filename)
    #parent_filename = parent_filename.split('/')[-1]
    links = self.get_links_to_file(parent_filename)
    for link in links:   
      print(link)
      if link in self.visited_files:
        child_metadata = NodeMetadata(os.path.join(self.path, link))
        child_nodename = Node(' ... ' + child_metadata.get_tag('title')[0] + ' -> ' + link, parent=parent)
        continue
      self.backward_visited_files.append(link)  
      self.visited_files.append(link)
      link = link.split('/')[-1]
      child_metadata = NodeMetadata(os.path.join(self.path, link))
      child_nodename = Node(child_metadata.get_tag('title')[0] + ' -> ' + link, parent=parent)
      self.add_backward_children(child_nodename)
  
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
    files = Urtext.get_all_files(self.view.window())
    for file in files:
      if file[-4:] == '.txt':
        metadata = NodeMetadata(os.path.join(Urtext.get_path(self.view.window()), file))
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
      listing = file.get_tag('title')[0] + ' -> ' + file.filename + '\n'    
      new_view.run_command("insert_snippet", { "contents": listing})       

def has_meta(contents):
  """ 
  Determine whether a view contains metadata. 
  :contents: -- the full contents of a file or fragment
  """
  global metaseparator
  if meta_separator() in contents:
    return True
  else:
    return False

def add_separator(view):
  """
  Adds a metadata separator if one is not already there.
  :view: a Sublime view
  """
  if not has_meta(view):
    view.run_command("move_to", {"to": "eof"})
    view.run_command("insert_snippet", { "contents": "\n\n"+meta_separator()})
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
  view.run_command("insert_snippet", { "contents": "\n\n"+meta_separator()+"Created "+text_timestamp+'\n'})
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
  return contents.split(meta_separator())[0]
