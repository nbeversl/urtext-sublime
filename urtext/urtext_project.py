import codecs
import re
import os
from urtext.urtext_node import UrtextNode
from anytree import Node, RenderTree

class UrtextProject:

  def __init__(self, path):
    self.path = path
    self.nodes = {}
    self.files = {}
    files = os.listdir(self.path)
    regexp = re.compile(r'\b\d{14}\b')
    num_files = 0
    for file in files:
      try:
        f = codecs.open(os.path.join(self.path, file), encoding='utf-8', errors='strict')
        for line in f:
            pass
        if regexp.search(file):
          thisfile = UrtextNode(os.path.join(self.path, file))
          if thisfile.node_number not in self.nodes:
            self.nodes[thisfile.node_number] = thisfile
            num_files += 1
        else:
          continue # skip files without Node ID's in the filename
      except UnicodeDecodeError:
        print("Urtext Skipping %s, invalid utf-8" % file) 
        continue
      except IsADirectoryError:
        continue
      #except:
      #  print('Urtext Skipping %s' % file)   
      #  continue
      self.files[os.path.basename(file)] = []
    
    for file in self.files:
      self.build_sub_nodes(file)
      
    print('URtext has %d files, %d nodes' % (num_files, len(self.nodes)))
    self.build_tag_info()
    for node in list(self.nodes):
      self.compile(node)

  def get_file_name(self, node_id):

    for node in self.nodes:
      if node == node_id:
        return self.nodes[node].filename
    return None

  def from_file_name(self, node_id):
 
    for node in self.nodes:
      if node == node_id:
        return self.nodes[node]
    return None

  def get_node_id(self, filename):
    regexp = re.compile(r'\b\d{14}\b')
    return regexp.search(filename).group(0)

  def get_all_files(self):

    all_files = []
    for node in self.nodes:
      all_files.append(self.nodes[node].filename)
    return all_files

  def unindexed_nodes(self):
    """ returns an array of node IDs of unindexed nodes, in reverse order (most recent) by Node ID """

    unindexed_nodes = []
    for node_id in self.nodes:
      if self.nodes[node_id].metadata.get_tag('index') == []:
        unindexed_nodes.append(node_id)
    sorted_unindexed_nodes = sorted(unindexed_nodes)
    return sorted_unindexed_nodes

  def indexed_nodes(self):
    """ returns an array of node IDs of indexed nodes, in indexed order """
  
    indexed_nodes = []
    for node in self.nodes:
      if self.nodes[node].metadata.get_tag('index') != []:
          indexed_nodes.append([node, self.nodes[node].metadata.get_tag('index')[0]])
    sorted_indexed_nodes = sorted(indexed_nodes, key=lambda item: item[1])
    for i in range(len(sorted_indexed_nodes)):
      sorted_indexed_nodes[i] = sorted_indexed_nodes[i][0]
    return sorted_indexed_nodes

  def build_tag_info(self):

    self.tagnames = {}
    for node in self.nodes:
      for entry in self.nodes[node].metadata.entries:
        if entry.tag_name.lower() != 'title': 
          if entry.tag_name not in self.tagnames:
            self.tagnames[entry.tag_name] = {}
          if not isinstance(entry.value, list):
            entryvalues = [entry.value]
          else:
            entryvalues = entry.value
          for value in entryvalues:
            if value not in self.tagnames[entry.tag_name]:
              self.tagnames[entry.tag_name][value] = []
            self.tagnames[entry.tag_name][value].append(node)

  def build_sub_nodes(self, filename):
      token = '======#########CHILDNODE'
      token_regex = re.compile(token+'\d{14}')

      self.files[os.path.basename(filename)] = []

      with open(os.path.join(self.path, filename),'r',encoding='utf-8') as theFile:
        full_file_contents = theFile.read()
        theFile.close()


      subnode_regexp = re.compile(r'{{(?!.*{{)(?:(?!}}).)*}}', re.DOTALL) # regex to match an innermost node <Mon., Mar. 11, 2019, 05:19 PM>
      #subnode_regexp = re.compile ('{{((?!{{)(?!}}).)+}}', flags=re.DOTALL ) # regex to match an innermost node <Mon., Mar. 11, 2019, 05:19 PM>
      # TODO - the second RegEx is better. I'm not sure why it doesn't work.
      #
      #
      tree = {}
      filename = os.path.basename(filename)
      root_node_id = self.get_node_id(filename)
      tree[root_node_id] = []

      remaining_contents = full_file_contents
      while subnode_regexp.search(remaining_contents):
        for sub_contents in subnode_regexp.findall(remaining_contents):      
          stripped_contents = sub_contents.strip('{{').strip('}}')        
          childnodes = token_regex.findall(stripped_contents)
          sub_node = UrtextNode(os.path.join(self.path,filename), contents=stripped_contents)        
          self.nodes[sub_node.node_number] = sub_node
          if not sub_node.node_number in tree:
            tree[sub_node.node_number] = []
          for child_node in token_regex.findall(stripped_contents): 
            tree[sub_node.node_number].append(child_node[len(token):])   
          stripped_contents = re.sub(token_regex,'',stripped_contents)
          identifier_text = '{{'+stripped_contents.split('{{')[0].split('/-')[0].rstrip()
          position = full_file_contents.find(identifier_text)
          self.nodes[sub_node.node_number].position = position
          remaining_contents = remaining_contents.replace(sub_contents,token + sub_node.node_number)
          self.files[os.path.basename(filename)].append(sub_node.node_number)

      # this is now the root node; get all its children;
      for child_node in token_regex.findall(remaining_contents):   
        tree[root_node_id].append(child_node[len(token):])

      root = Node(root_node_id)

      def add_children(parent):
        for child in tree[parent.name]:
          title = self.nodes[child].metadata.get_tag('title')[0]
          new_node = Node(child, parent=parent)
          add_children(new_node)
      
      add_children(root)

      tree_render = ''
      for pre, _, node in RenderTree(root):
        try:
           tree_render += "%s%s" % (pre, self.nodes[node.name].metadata.get_tag('title')[0]) + '\n' 
        except:
          print('Error parsing node in file: %s' % filename)
      self.nodes[root_node_id].tree = tree_render

  def compile(self, node_id):
    keys = re.compile('(?:\[\[)(.*?)(?:\]\])', re.DOTALL)
    node_id_match = re.compile('\d{14}')

    for match in keys.findall(self.nodes[node_id].contents):       
      compiled_node_id = node_id_match.search(match).group(0)
      entries = re.split(';|\n', match)
      contents = ''
      metadata = '/- ID:'+compiled_node_id + '\n'
      for entry in entries:
        atoms = [atom.strip() for atom in entry.split(':')]
        if atoms[0].lower() == 'include':
          if atoms[1].lower() == 'metadata':
            key = atoms[2]
            value = atoms[3]
            right_key = None
            for indexed_value in self.tagnames[key]:
              if indexed_value.lower().strip() == value:
                right_value = value  
            if right_value != None:
              for other_node in self.tagnames[key][right_value]:
                contents += strip_metadata(self.nodes[other_node].contents) + '\n'
        if atoms[0].lower() == 'metadata':
          if atoms[1].lower() == 'title':
            metadata += 'title: '+atoms[2] + '\n'
      metadata += ' -/'
      with open(os.path.join(self.path,compiled_node_id+'.txt'),"w") as theFile:            
        theFile.write(contents)
        theFile.write(metadata)        
        theFile.close()
        self.nodes[compiled_node_id] = UrtextNode(compiled_node_id+'.txt', contents=contents+metadata)
        self.files[compiled_node_id+'.txt'] = [compiled_node_id]

def strip_metadata(contents):
   meta = re.compile('\/-.*?-\/', re.DOTALL)
   for section in re.findall(meta, contents):
      contents = contents.replace(section,'')
   return contents


