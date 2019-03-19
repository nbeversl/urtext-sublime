# under construction

import os
from anytree import Node, RenderTree
from Urtext import UrtextNode

class NodeTree(oldest_node, path):
  """ Display a tree of all nodes connected to this one """
  # to add:
  #   move cursor to the file this was called from
  self.path = path
  self.errors = []   
  oldest_known_filename = self.find_oldest_node(os.path.basename(oldest_node))

  self.tree = Node(oldest_known_filename)
  self.build_node_tree('ROOT -> ' + oldest_known_filename)

  render = ''
  for pre, fill, node in RenderTree(self.tree):
    render += ("%s %s" % (pre, node.name)) + '\n'

  return render

  def find_oldest_node(self, filename):
    """ Locate the oldest node by recursively following 'pulled from' backlinks """
    oldest_known_filename = filename
    this_meta = UrtextNode(filename,self.view.window()).metadata
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