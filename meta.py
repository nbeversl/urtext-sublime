# Urtext node metadata handling

import sublime
import sublime_plugin
import os
import re
import datetime
import Urtext.urtext as Urtext
import pprint
import logging
import sys

sys.path.append(os.path.join(os.path.dirname(__file__)))
from anytree import Node, RenderTree
import anytree

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
  def __init__(self, full_contents):
    self.entries = []
    meta = re.compile(r'\/-.*-\/', re.DOTALL)
    raw_meta_data = ''
    for section in re.findall(meta, full_contents):
      meta_block = section.replace('-/','')
      meta_block = meta_block.replace('/-','')
      raw_meta_data += meta_block + '\n'
    title_set = False
    #raw_meta_data += full_contents.split(meta_separator())[-1]
    #meta_lines = raw_meta_data.split('\n')
    meta_lines = re.split(';|\n',raw_meta_data)
    
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
      first_line = full_contents.split('\n')[0][:50]
      first_line = first_line.split('------------')[0]
      title = first_line.split('->')[0] # don't include links in the title, for traversing files clearly.
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
  """ Adds a modification timestamp to the metadata. """
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
    this_meta = Urtext.UrtextNode(filename,self.view.window()).metadata
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
      with open(os.path.join(self.path, parent_filename),'r',encoding='utf-8') as this_file:
        contents = this_file.read()
        this_file.close()
    except:
      self.errors.append('Broken link: -> %s\n' % parent_filename)
      return
    this_meta = NodeMetadata(contents)

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
  #
  # Also this command does not currently utilize the global array, it reads files manually.
  # Necessary to change it?

  def run(self, edit):
    Urtext.refresh_nodes(self.view.window())
    self.path = Urtext.get_path(self.view.window())
    self.errors = [] 
    self.visited_files = []
    self.backward_visited_files = []
    self.tree = Node(self.view.file_name())

    root_node_id = Urtext._UrtextProject.get_node_id(os.path.basename(self.view.file_name()))
    root_node = Urtext._UrtextProject.nodes[root_node_id]
    root_meta = Urtext._UrtextProject.nodes[root_node_id].metadata

    self.build_node_tree(root_meta.get_tag('title')[0] + ' -> ' + root_node.filename)
    self.build_backward_node_tree(root_meta.get_tag('title')[0] + ' -> ' + root_node.filename)
    
    window = self.view.window()
    window.focus_group(0) # always show the tree on the leftmost focus'
    new_view = window.new_file()
    window.focus_view(new_view)

    def render_tree(new_view):
      if not new_view.is_loading():
        render = ''
        for pre, fill, node in RenderTree(self.backward_tree):
          render += ("%s%s" % (pre, node.name)) + '\n'
        render = render.replace('└','┌')    
        render = render.split('\n')
        render = render[1:] # avoids duplicating the root node
        render_upside_down = ''
        for index in range(len(render)):
          render_upside_down += render[len(render)-1 - index] + '\n'
        for line in render_upside_down:
          new_view.run_command("insert_snippet", { "contents": line })
        new_view.run_command("insert_snippet", { "contents": '\n'.join(self.errors)})
      
        render = ''
        for pre, fill, node in RenderTree(self.tree):
          render += ("%s%s" % (pre, node.name)) + '\n'
 
        render = render.split('\n')
        for line in render:
          new_view.run_command("insert_snippet", { "contents": line+'\n'})
        new_view.run_command("insert_snippet", { "contents": '\n'.join(self.errors)})
        new_view.set_scratch(True)
      else:
        sublime.set_timeout(lambda: render_tree(new_view), 10)
    
    render_tree(new_view)

  def build_node_tree(self, oldest_node, parent=None):
      self.tree = Node(oldest_node)
      self.add_children(self.tree)

  def get_file_links_in_file(self,filename):
      with open(os.path.join(self.path, filename),'r',encoding='utf-8') as this_file:
        contents = this_file.read()
      nodes = re.findall('(?:->\s)(?:[^\|\r\n]*\s)?(\d{14})',contents) # link RegEx
      filenames = []
      for node in nodes:
        filenames.append(Urtext._UrtextProject.get_file_name(node))
      return filenames
 
  def add_children(self, parent):
    """ recursively add children """
    parent_filename = parent.name.split('->')[1].strip()
    links = self.get_file_links_in_file(parent_filename)
    for link in links:
      if link in self.visited_files:
        child_metadata = Urtext.UrtextNode(os.path.join(self.path, link)).metadata
        child_nodename = Node(' ... ' + child_metadata.get_tag('title')[0] + ' -> ' + link, parent=parent)
        continue
      self.visited_files.append(link)
      if link == None:
        child_nodename = Node('(Broken Link)',parent=parent)
      else:
        child_metadata = Urtext.UrtextNode(os.path.join(self.path, link)).metadata
        child_nodename = Node(child_metadata.get_tag('title')[0] + ' -> ' + link, parent=parent)
      self.add_children(child_nodename) # bug fix here

  def build_backward_node_tree(self, oldest_node, parent=None):
      self.backward_tree = Node(oldest_node)
      self.add_backward_children(self.backward_tree)

  def get_links_to_file(self, filename):
      if filename == '':
        return []
      files = Urtext._UrtextProject.get_all_files()
      links_to_file = []
      for file in files:
        with open(os.path.join(self.path, file),'r',encoding='utf-8') as this_file:
          contents = this_file.read()
          this_file = Urtext.UrtextNode(os.path.join(self.path, filename))
          links = re.findall('->\s[^\|\r\n]*' + this_file.node_number, contents) # link RegEx
          if len(links) > 0:
            links_to_file.append(file)
      return links_to_file

  def add_backward_children(self, parent):
    parent_filename = parent.name.split('->')[1].strip()
    links = self.get_links_to_file(parent_filename)
    for link in links:   
      if link in self.backward_visited_files:   
        with open(os.path.join(self.path, file),'r',encoding='utf-8') as this_file:       
           contents = this_file.read()
        child_metadata = NodeMetadata(contents)
        child_nodename = Node(' ... ' + child_metadata.get_tag('title')[0] + ' -> ' + link, parent=parent)
        continue
      self.backward_visited_files.append(link)  
      link = link.split('/')[-1]
      child_metadata = NodeMetadata(contents)
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
    self.tagnames = [ value for value in Urtext._UrtextProject.tagnames ]
    self.view.window().show_quick_panel(self.tagnames, self.list_values)

  def list_values(self, index):
    self.selected_tag = self.tagnames[index]
    self.values = [ value for value in Urtext._UrtextProject.tagnames[self.selected_tag]]
    self.values.insert(0, '< all >')
    self.view.window().show_quick_panel(self.values, self.list_files)

  def list_files(self, index):
    self.selected_value = self.values[index]
    new_view = self.view.window().new_file()
    new_view.set_scratch(True)
    if self.selected_value == '< all >':
      new_view.run_command("insert_snippet", { "contents": '\nFiles found for tag: %s\n\n' % self.selected_value})
      for value in Urtext._UrtextProject.tagnames[self.selected_tag]:
        new_view.run_command("insert_snippet", { "contents": value + "\n"})       
        for node in Urtext._UrtextProject.tagnames[self.selected_tag][value]:
          new_view.run_command("insert_snippet", { "contents": " -> " +node + "\n"})   
        new_view.run_command("insert_snippet", { "contents": "\n"})       

    else:
      new_view.run_command("insert_snippet", { "contents": '\nFiles found for tag: %s with value %s\n\n' % (self.selected_tag, self.selected_value)})
      for node in Urtext._UrtextProject.tagnames[self.selected_tag][self.selected_value]:
        new_view.run_command("insert_snippet", { "contents": " -> " +node + "\n"})       

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
