# Urtext node metadata handling

import sublime
import sublime_plugin
import os
import re
import datetime
import pprint
import logging
import sys
sys.path.append(os.path.join(os.path.dirname(__file__),"urtext/dependencies"))
sys.path.append(os.path.join(os.path.dirname(__file__)))
from urtext.node_pull_tree import NodePullTree
import sublime_urtext

def meta_separator():
    return "------------" # to remove later


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
  # most of this is now in urtext module

  def run(self, edit):
    sublime_urtext.refresh_nodes(self.view.window())
    self.errors = []
    path = sublime_urtext._UrtextProject.path
    tree = NodePullTree(self.view.file_name(), path)
    window = self.view.window()
    window.focus_group(0) # always show the tree on the leftmost focus
    new_view = self.view.window().new_file()
    new_view.run_command("insert_snippet", { "contents": tree.render})
    new_view.run_command("insert_snippet", { "contents": '\n'.join(self.errors)})

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
      with open(os.path.join(self.path, link),'r',encoding='utf-8') as this_file:       
         contents = this_file.read()
      if link in self.backward_visited_files:   
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
  view.run_command("insert_snippet", { "contents": text_timestamp+'\n'})

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
