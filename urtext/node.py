import os
import sys
sys.path.append(os.path.dirname(__file__))

from metadata import NodeMetadata
import re
import datetime
import logging
from anytree.node import Node
from anytree import PreOrderIter
import anytree
dynamic_def = re.compile('(?:\[\[)(.*?)(?:\]\])', re.DOTALL)

class UrtextNode:
  """ Urtext Node object"""

  def __init__(self, filename, contents='', root=False):
    self.filename = os.path.basename(filename) 
    self.project_path = os.path.dirname(filename)
    self.position = 0
    self.ranges = [[0,0]]
    self.tree = None
    self.metadata = NodeMetadata(contents)
    self.dynamic = False
    self.id = None
    self.new_id = None
    self.root_node = root
    self.date = datetime.datetime(1970,1,1) # temporary default
    self.prefix = None
    self.project_settings = False
    self.contains_dynamic_def = False
    if self.metadata.get_tag('ID') != []:
      node_id = self.metadata.get_tag('ID')[0].lower().strip()
      if re.match('^[a-z0-9]{3}$', node_id):
        self.id = node_id
    if self.metadata.get_tag('title') == ['project_settings']:
        self.project_settings = True
    if dynamic_def.search(contents):
      self.contains_dynamic_def = True

    stripped_contents = self.strip_dynamic_definitions(contents)
    self.metadata = NodeMetadata(stripped_contents)
    self.parent = None
    self.index = self.metadata.get_tag('index')
    self.reset_node()
    self.title = None
    
  def reset_node(self):
    self.tree_node = Node(self.id)

  def duplicate_tree(self):
    return duplicate_tree(self.tree_node)

  def contents(self):
    with open(os.path.join(self.project_path, self.filename), 'r',encoding='utf-8') as theFile:
      file_contents = theFile.read()
      theFile.close()
    node_contents = ''
    for segment in self.ranges:
      node_contents += file_contents[segment[0]:segment[1]]
    return node_contents

  def strip_metadata(self, contents=''):
    if contents == '':
      contents = self.contents()
    stripped_contents = re.sub(r'(\/--(?:(?!\/--).)*?--\/)', '', contents, flags=re.DOTALL)
    return stripped_contents
  def strip_inline_nodes(self, contents=''):
    if contents == '':
      contents = self.contents()
    subnode_regexp = re.compile(r'{{(?!.*{{)(?:(?!}}).)*}}', re.DOTALL)
    stripped_contents = contents
    while subnode_regexp.search(stripped_contents):
      for inline_node in subnode_regexp.findall(stripped_contents): 
          stripped_contents = stripped_contents.replace(inline_node, '')
    return stripped_contents

  def strip_dynamic_definitions(self,contents=''):
    if contents == '':
      contents = self.contents()
    dynamic_def_regexp = re.compile(r'\[\[.*?\]\]', re.DOTALL)
    stripped_contents = contents
    while dynamic_def_regexp.search(stripped_contents):
      for dynamic_definition in dynamic_def_regexp.findall(stripped_contents): 
          stripped_contents = stripped_contents.replace(dynamic_definition, '')
    return stripped_contents

  def content_only(self):

    contents = self.strip_metadata(contents=self.contents())
    contents = self.strip_dynamic_definitions(contents=contents)
    return contents
    
  def set_index(self, new_index):
    self.index = new_index
  
  def get_title(self):
    if self.title != None:
      return self.title
    return self.set_title()

  def set_title(self):
    if len(self.metadata.get_tag('title')) > 0: # title is the first many lines if not set
      self.title = self.metadata.get_tag('title')[0]
      return self.title

    full_contents = self.content_only().strip().split('\n')    
    index = 0
    while full_contents[index].strip() == '':
      if index == len(full_contents) - 1:
        self.title = '(untitled)'
        return self.title
      index += 1
       
    first_line = full_contents[index][:100].replace('{{','').replace('}}','')
    first_line = re.sub('\/-.*(-\/)?','',first_line, re.DOTALL)
    self.title = first_line.strip()
    return self.title
 
  def get_ID(self):
    if len(self.metadata.get_tag('ID')) > 0: # title is the first many lines if not set
      return self.metadata.get_tag('ID')[0]
    return self.id # don't include links in the title, for traversing files clearly.


  def log(self):
    logging.info(self.id)
    logging.info(self.index)
    logging.info(self.filename)
    logging.info(self.metadata.log())

  def consolidate_metadata(self, one_line=False):

    def line_separator(one_line=False):
      if one_line == True:
        return '; '
      else: 
        return '\n'

    tags = {}
    for entry in self.metadata.entries:
      if entry.tag_name not in tags:
        tags[entry.tag_name] = []
      entry_value = entry.value
      if isinstance(entry.value,str):
        entry_value = [entry_value]
      for value in entry_value:
        tags[entry.tag_name].append(value)
    new_metadata = '\n/--'
    new_metadata += line_separator(one_line)
    new_metadata += 'ID:'+self.get_ID() + line_separator(one_line=one_line)
    new_metadata += 'title:'+self.title + line_separator(one_line=one_line)      

    for tag in tags:
      if tag in ['ID','title']: # do not duplicate these
        continue
      new_metadata += tag + ': '
      new_metadata += ' | '.join(tags[tag])
      new_metadata += line_separator(one_line)
    if one_line == True:
      new_metadata = new_metadata[:-2] + ' '

    new_metadata += '--/'
    return new_metadata


def duplicate_tree(original_node):
  
    new_root = Node(original_node.name) 

    all_nodes = PreOrderIter(original_node, maxlevel=2) # iterate immediate children only
    
    for node in all_nodes:
      if node == original_node:
        continue

      if node.name in [ancestor.name for ancestor in node.ancestors]:

        recursion_name = 'RECURSION '+node.name
        new_node = Node(recursion_name)
        new_node.parent = new_root
        continue

      if node.parent == original_node:
        new_node = duplicate_tree(node)
        new_node.parent = new_root
      
    return new_root
