import codecs
import re
import os
import datetime
import sys
import itertools
import platform
import logging
import operator
import difflib

parent_dir = os.path.dirname(__file__)
sys.path.append(os.path.join(parent_dir, 'anytree'))
sys.path.append(os.path.join(parent_dir, 'anytree/node'))
sys.path.append(os.path.join(parent_dir, 'whoosh'))
sys.path.append(parent_dir)

from anytree.node import Node
from anytree.render import RenderTree
from anytree import PreOrderIter
import urtext.timeline
from urtext.node import UrtextNode
import interlinks

from whoosh.fields import Schema, TEXT, ID
from whoosh.index import create_in, exists_in, open_dir
from whoosh.query import *
from whoosh.qparser import QueryParser
from whoosh.highlight import UppercaseFormatter

node_id_regex = r'\b[0-9,a-z]{3}\b'
node_link_regex = r'>[0-9,a-z]{3}\b'
keys = re.compile('(?:\[\[)(.*?)(?:\]\])', re.DOTALL)

class UrtextProject:
  """ Urtext project object """

  def __init__(self, path, 
        make_new_files=True, 
        rename=False, 
        recursive=False, 
        import_project=False):
        
    if path == None:
      print ('No path found. No project opened')
      return None 

    self.path = path
    self.build_response = ''
    self.log = setup_logger('urtext_log',os.path.join(self.path,'urtext_log.txt'))
    self.make_new_files = make_new_files
    self.nodes = {}
    self.files = {}
    self.tagnames = {}
    self.zero_page = ''
    self.other_projects = []
    self.navigation = [] # Stores, in order, the path of navigation
    self.nav_index = -1  # pointer to the CURRENT position in the navigation list
    self.settings = { # defaults
      'logfile' : 'urtext_log.txt',
      'timestamp_format' : ['%a., %b. %d, %Y, %I:%M %p', '%B %-d, %Y', '%B %Y', '%m-%d-%Y'],
      'filenames': ['PREFIX', 'DATE %m-%d-%Y', 'TITLE'],
      'node_list': '00000.txt'
      }
    self.to_import = []
    self.settings_initialized = False
    self.dynamic_defs = []
    self.compiled = False
    self.alias_nodes = []

    chars = [ '0','1','2','3','4','5','6','7','8','9','a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 
      'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 
      'u', 'v', 'w', 'x', 'y', 'z']
    
    self.indexes = itertools.product(chars, repeat=3)

    filelist = os.listdir(self.path)
    
    for file in filelist:
      self.parse_file(file, import_project=import_project)
    
    for file in self.to_import:
      self.import_file(file)
            
    for node_id in list(self.nodes): # needs do be done once manually on project init
      self.parse_meta_dates(node_id) 

    self.compile_all()

    self.compiled = True    

    self.update()


  def update(self):
    """ 
    Main method to keep the project updated. 
    Should be called whenever file or directory content changes
    """
    #for filename in self.files:
    #  self.set_tree_elements(filename)
      
    self.build_alias_trees() # Build copies of trees wherever there are Node Pointers (>>)
    self.rewrite_recursion()
    self.compile_all()
      
    # Update lists:
    self.update_node_list()
    self.update_metadata_list()

    
  
  """ 
  Parsing
  """

  def parse_file(self, filename, import_project=False):
    """ Main method for parsing a single file into nodes """

    filename = os.path.basename(filename)
    if self.filter_filenames(filename) == None:
      return

    full_file_contents = self.get_file_contents(filename)
    if full_file_contents == None:
      return

    # clear all node_id's defined from this file in case the file has changed
    self.remove_file(filename)

    # re-add the file to the project
    self.files[filename] = {}
    self.files[filename]['nodes'] = []

    """
    Find all node symbols in the file
    """
    symbols = {}
    for symbol in ['{{','}}','>>']:
      loc = -2
      while loc != -1:       
        loc = full_file_contents.find(symbol, loc+2) 
        symbols[loc] = symbol

    positions = sorted([key for key in symbols.keys() if key != -1])
    length = len(full_file_contents)

    """
    Counters and trackers
    """
    nested = 0                # tracks depth of node nesting
    nested_levels = {}
    last_start = 0            # tracks the most recently parsed position
    parsed_items = {}         # stores parsed items

    for position in positions:

      # Allow node nesting arbitrarily deep
      if nested not in nested_levels:
        nested_levels[nested] = []

      # If this opens a new node, track the ranges of the outer one.
      if symbols[position] == '{{':
        nested_levels[nested].append([last_start, position]) 
        nested += 1
        last_start = position + 2
        continue

      # If this points to an outside node, find which node
      if symbols[position] == '>>':
        parsed_items[position] = full_file_contents[position:position + 5]
        continue
      
      # If this closes a node:
      if symbols[position] == '}}': # pop 
        nested_levels[nested].append([last_start, position]) 
        
        # Get the node contents and construct the node
        node_contents=''
        for file_range in nested_levels[nested]:
          node_contents += full_file_contents[file_range[0]:file_range[1]]
        new_node = UrtextNode(os.path.join(self.path,filename), contents=node_contents)
        
        if new_node.id != None and re.match(node_id_regex, new_node.id):
          if self.is_duplicate_id(new_node.id, filename):
            return
          else:
            self.add_node(new_node, nested_levels[nested])
            parsed_items[position] = new_node.id
            
        else:
          error_line  = full_file_contents[position - 50:position].split('\n')[-1]
          error_line += full_file_contents[position:position + 50].split('\n')[0]
          message = [
              'Node missing ID in ', filename, '\n',
              error_line, '\n', ' ' * len(error_line), '^'
              ]
          message = ''.join(message)
          self.log_item(message)
          return self.remove_file(filename)

        del nested_levels[nested]

        last_start = position + 2
        nested -= 1
        
        if nested < 0:            
          error_line  = full_file_contents[position - 50:position].split('\n')[0]
          error_line += full_file_contents[position:position + 50].split('\n')[0]
          message = [
              'Stray closing wrapper in ', filename, ' at position ', str(position),'\n',
              error_line, '\n', ' ' * len(error_line), '^'
              ]
          message = ''.join(message)
          self.log_item(message)
          return self.remove_file(filename)
    
    if nested != 0 :
      error_line  = full_file_contents[position - 50:position].split('\n')[0]
      error_line += full_file_contents[position:position + 50].split('\n')[0]
      message = [
          'Missing closing wrapper in ', filename, ' at position ', str(position), '\n',
          error_line, '\n', ' ' * len(error_line), '^'
          ]
      message = ''.join(message)
      self.log_item(message)
      return self.remove_file(filename) 
    
    ### Handle the root node:
    if nested_levels == {} or nested_levels[0] == []:
      nested_levels[0]=[[0, length]] # no inline nodes
    else:
      nested_levels[0].append([last_start+1,length])
    
    root_node_contents=''
    for file_range in nested_levels[0]:
      root_node_contents += full_file_contents[file_range[0]:file_range[1]] 
    root_node = UrtextNode(
        os.path.join(self.path,filename), 
        contents=root_node_contents, 
        root=True)
    if root_node.id == None or not re.match(node_id_regex, root_node.id):
      if import_project == True:
        if filename not in self.to_import:
          self.to_import.append(filename)
          return self.remove_file(filename)
      else:
        self.log_item('Root node without ID: '+ filename)
        return self.remove_file(filename)  
    
    if self.is_duplicate_id(root_node.id, filename):
      return
    
    self.add_node(root_node, nested_levels[0])
    root_node_id = root_node.id

    self.files[filename]['parsed_items'] = parsed_items
    """
    If this is not the initial load of the project, parse the timestamps in the file
    """
    if self.compiled == True:
      for node_id in self.files[filename]['nodes']:      
        self.parse_meta_dates(node_id)
    self.set_tree_elements(filename)
      
    for node_id in self.files[filename]['nodes']:
      self.rebuild_node_tag_info(node_id)
      self.nodes[node_id].set_title()
    return filename
  
  """
  Tree building
  """

  def set_tree_elements(self, filename):
    """ 
    Builds tree elements within the file, after the file is parsed.
    """
    parsed_items = self.files[filename]['parsed_items']
    positions = sorted(parsed_items.keys())

    for position in positions:
      
      node = parsed_items[position]
      
      # 
      # If the parsed item is a tree marker to another node,
      # parse the markers, positioning it within its parent node
      #
      if node[:2] == '>>':
        inserted_node_id = node[2:]
        for other_node in [node_id for node_id in self.files[filename]['nodes'] if node_id != node]: # Careful ...
          if self.is_in_node(position, other_node):
            parent_node = other_node
            alias_node = Node(inserted_node_id)
            alias_node.parent = self.nodes[parent_node].tree_node
            if alias_node not in self.alias_nodes:
              self.alias_nodes.append(alias_node)
            break
        continue


      """
      in case this node begins the file and is an an inline node,
      set the inline node's parent as the root node manually.
      """
      if position == 0 and parsed_items[0] == '{{': 
        self.nodes[node].tree_node.parent = self.nodes[root_node_id].tree_node
        continue
      """
      Otherwise, this is an inline node not at the beginning of the file.
      """
      parent = self.get_parent(node)
      self.nodes[node].tree_node.parent = self.nodes[parent].tree_node

  def build_alias_trees(self):
    """ 
    Adds copies of trees wherever there are Node Pointers (>>) 
    Must be called only when all nodes are parsed (exist) so it does not miss any

    The problem is Node Pointers pointed to by Node Pointers.
    It doesn't know that a Node pointer inside a node pointed to by a node pointer might have changed.
    Basically chaining of node Pointers is not working
    """
    
    # must use EXISTING node so it appears at the right place in the tree.
    for node in self.alias_nodes:
      node_id = node.name[-3:]
      if node_id in self.nodes:
        duplicate_node = self.nodes[node_id].duplicate_tree()
        node.children = [s for s in duplicate_node.children]
      else:
        new_node = Node('MISSING NODE '+node_id)
      
  def rewrite_recursion(self):

    for node in self.alias_nodes: 
      all_nodes = PreOrderIter(node)
      for sub_node in all_nodes:
        if sub_node.name in [ancestor.name for ancestor in sub_node.ancestors]:
          sub_node.name = 'RECURSION >'+sub_node.name
          sub_node.children = []

  """
  Parsing helpers
  """

  def add_node(self, new_node, ranges):
    """ Adds a node to the project object """

    if new_node.filename not in self.files:
      self.files[new_node.filename]['nodes'] = []

    if new_node.contains_dynamic_def == True:
      self.dynamic_defs.append(new_node.id)

    ID_tags = new_node.metadata.get_tag('ID')
    if len(ID_tags) > 1 :
      self.log_item('Multiple ID tags in >'+new_node.id+', using the first one found.')

    self.nodes[new_node.id]=new_node
    self.files[new_node.filename]['nodes'].append(new_node.id)
    self.nodes[new_node.id].ranges = ranges
    if new_node.project_settings:
      self.get_settings_from(new_node)

  def parse_meta_dates(self, node_id):
    """ Parses dates (requires that timestamp_format already be set) """

    timestamp_format = self.settings['timestamp_format']
    if isinstance(timestamp_format, str):
      timestamp_format = [timestamp_format]

    for entry in self.nodes[node_id].metadata.entries:
      if entry.dtstring:
          dt_stamp = None
          for this_format in timestamp_format:
            dt_format = '<' + this_format + '>'    
            try:
              dt_stamp = datetime.datetime.strptime(entry.dtstring, dt_format)
            except:
              continue 
          if dt_stamp:
            self.nodes[node_id].metadata.dt_stamp = dt_stamp
            if entry.tag_name == 'Timestamp': 
              self.nodes[node_id].date = dt_stamp
            continue
          else:
            self.log_item('Timestamp ' + entry.dtstring + ' not in any specified date format in >' + node_id)

  



  def show_tree_from(self, node_id, from_root_of=False): # these could both be one

    if node_id not in self.nodes:
      self.log_item(root_node_id+' is not in the project')
      return None
    
    tree_render=''

    start_point = self.nodes[node_id].tree_node
    if from_root_of == True:
      start_point = self.nodes[node_id].tree_node.root

    for pre, _, this_node in RenderTree(start_point):
      if this_node.name in self.nodes:
        tree_render += "%s%s" % (pre,
            self.nodes[this_node.name].title) + ' >' + this_node.name + '\n'
      else:
        tree_render += "%s%s" % (pre, '? (Missing Node): >'+ this_node.name + '\n')
    return tree_render

  """
  Compiling dynamic nodes
  """

  def compile(self, dynamic_node_def_id):
    """ Main method to compile dynamic nodes definitions """

    target_nodes = []

    for match in keys.findall(self.nodes[dynamic_node_def_id].contents()):
        entries=re.split(';|\n', match)
        included_nodes=[]
        excluded_nodes=[]
        compiled_node_id=None
        sort_tagname=None
        contents=''
        old_node_contents=''
        updated_contents=''
        metadata='/-- '
        show='full_contents'
        for entry in entries:
          atoms=[atom.strip() for atom in entry.split(':')]
          if atoms[0].lower() == 'id' and len(atoms) > 1:
            compiled_node_id = re.search(node_id_regex, atoms[1]).group(0)
            metadata += 'ID: ' + compiled_node_id + '\n'
          if atoms[0].lower() == 'show' and len(atoms) > 1:
            if atoms[1] == 'title':
              show='title'
            if atoms[1] == 'timeline':
              show='timeline'
              if compiled_node_id in self.nodes:
                excluded_nodes.append(self.nodes[compiled_node_id])

          if atoms[0].lower() in ['exclude', 'include'] and len(atoms) > 1:
            if atoms[0] == 'include' and atoms[1].lower() == 'all':
              included_nodes=[]
              indexed_nodes = list(self.indexed_nodes())
              for node_id in indexed_nodes:
                included_nodes.append(self.nodes[node_id])
              unindexed_nodes = list(self.unindexed_nodes())
              for node_id in unindexed_nodes:
                included_nodes.append(self.nodes[node_id])              

            if atoms[1].lower() == 'metadata' and len(atoms) > 3:
              key=atoms[2]
              value=atoms[3]
              right_value=None
              for indexed_value in self.tagnames[key]:
                if indexed_value.lower().strip() == value:
                  right_value=value
              if right_value != None:
                for targeted_node in self.tagnames[key][right_value]:
                  if atoms[0] == 'exclude':
                    excluded_nodes.append(self.nodes[targeted_node])
                  if atoms[0] == 'include':
                    included_nodes.append(self.nodes[targeted_node])
          if atoms[0].lower() == 'tree' and len(atoms) > 1 and atoms[1] in self.nodes:
              contents += self.show_tree_from(atoms[1])
          if atoms[0] == 'sort' and len(atoms) > 1:
            sort_tagname = atoms[1]
          if atoms[0].lower() == 'metadata' and len(atoms) > 2:
            if atoms[1].lower() == 'timestamp':
              metadata += atoms[1] + ': ' + ':'.join(atoms[2:]) + '\n' # use the rest of the line
            else: 
              metadata += atoms[1] + ': ' + atoms[2] + '\n'

        for excluded_node in excluded_nodes:
          if excluded_node in included_nodes:
            included_nodes.remove(excluded_node)

        if sort_tagname != None:
          included_nodes = sorted(included_nodes, key=lambda node: node.metadata.get_tag(sort_tagname))
        else:
          included_nodes = sorted(included_nodes, key=lambda node: node.date)

        #build dynamic node contents
        if show == 'timeline':
           contents += urtext.timeline.timeline(self, included_nodes)

        else: 
          for targeted_node in included_nodes:
            if show == 'title':
              show_contents = targeted_node.set_title()
            if show == 'full_contents':
              show_contents = targeted_node.content_only() 
            if targeted_node.id == None:
              self.log_item('Targeted Node has no ID')
              return None
            contents += show_contents + ' >' + targeted_node.id + '\n-\n'

        metadata += 'kind: dynamic\n'
        metadata += 'defined in: >' + dynamic_node_def_id + '\n'
        metadata += ' --/'

        if not compiled_node_id:
          return None

        """
        check if the target node exists.
        """
        if compiled_node_id not in self.nodes:
          self.log_item('Dynamic node definition >' + dynamic_node_def_id + ' points to nonexistent node >' + compiled_node_id)
          return None
          
        if self.nodes[compiled_node_id].dynamic_definition not in [ None, dynamic_node_def_id ]:
          self.log_item('Node >' + compiled_node_id + ' has duplicate definition in >' + dynamic_node_def_id+'. Keeping the definition in >'+ self.nodes[compiled_node_id].dynamic_definition+'.')
          return None

        filename = self.get_file_name(compiled_node_id)
        updated_contents = contents + metadata
              
        
        def update_file(filename):
          with open(os.path.join(self.path, filename), "w", encoding='utf-8') as theFile:
            theFile.write(updated_contents)
            theFile.close()

          compiled_node = UrtextNode(os.path.join(self.path, filename), 
            contents=updated_contents)
          compiled_node.dynamic_definition = dynamic_node_def_id
          if compiled_node.id != None: # node must already exist
            self.nodes[compiled_node_id] = compiled_node
            if compiled_node.id not in self.files[os.path.basename(filename)]['nodes']:
              self.files[os.path.basename(filename)]['nodes'].append(compiled_node_id)

        if len(self.files[os.path.basename(filename)]['nodes']) > 1:
          old_node_contents = self.nodes[compiled_node_id].contents()
          with open(os.path.join(self.path, filename), "r", encoding='utf-8') as theFile:
            full_file_contents=theFile.read()
            theFile.close()
          new_file_contents = full_file_contents.replace(old_node_contents, updated_contents)
          if new_file_contents != full_file_contents:
            with open(os.path.join(self.path, filename), "w", encoding='utf-8') as theFile:
              theFile.write(new_file_contents)
              theFile.close()

        else: # for single-node files:
          with open(os.path.join(self.path, filename), "r", encoding='utf-8') as theFile:
            current_contents = theFile.read()
            theFile.close()
          if current_contents != updated_contents:
            update_file(filename)
            
        self.parse_file(filename) 
        # necessary so that the ranges of subsequent nodes get rewritten with the updates

        target_nodes.append(compiled_node_id)

    for node_id in target_nodes:
      self.nodes[node_id].dynamic_definition = dynamic_node_def_id


  """
  Refreshers
  """
  def update_node_list(self):
    """ Refreshes the Node List file """

    node_list_file = self.settings['node_list']
    with open(os.path.join(self.path, node_list_file), 'w', encoding='utf-8') as theFile:
      theFile.write(self.list_nodes())
      metadata = '/--\nID:zzz\ntitle: Node List\n--/'
      theFile.write(metadata)
      theFile.close()

  def update_metadata_list(self):
    """ Refreshes the Metadata List file """
    
    root = Node('Metadata Keys')
    for key in [k for k in self.tagnames if k.lower() not in ['defined in','id','timestamp','index']]:
      s = Node(key)
      s.parent = root
      for value in self.tagnames[key]:
        t = Node(value)
        t.parent = s
        for node_id in self.tagnames[key][value]:
          n = Node(self.nodes[node_id].title +' >'+node_id)
          n.parent = t
    
    with open(os.path.join(self.path, 'metadata.txt'), 'w', encoding='utf-8') as theFile:
      for pre, _, node in RenderTree(root):
        theFile.write("%s%s\n" % (pre, node.name))
      metadata = '/--\nID:zzy\ntitle: Metadata List\n--/'
      theFile.write(metadata)
      theFile.close()

  
  """
  Metadata
  """
  def tag_node(self, node_id, tag_contents):
    """adds a metadata tag to a node programmatically"""

    # might also need to add in checking for Sublime (only) to make sure the file
    # is not open and unsaved.
    timestamp = self.timestamp(datetime.datetime.now())
    territory = self.nodes[node_id].ranges
    with open(os.path.join(self.path, self.nodes[node_id].filename), 'r') as theFile:
      full_file_contents = theFile.read()
      theFile.close()
    tag_position = territory[-1][1]
    new_contents = full_file_contents[:tag_position] + tag_contents + full_file_contents[tag_position:]
    with open(os.path.join(self.path, self.nodes[node_id].filename), 'w') as theFile:
      theFile.write(new_contents)
      theFile.close()
    self.parse_file(os.path.join(self.path, self.nodes[node_id].filename))


  def consolidate_metadata(self, node_id, one_line=False):

    def adjust_ranges(filename, position, length):
      for node_id in self.files[os.path.basename(filename)]['nodes']:
        for index in range(len(self.nodes[node_id].ranges)):
          this_range = self.nodes[node_id].ranges[index]    
          if position >= this_range[0]:
            self.nodes[node_id].ranges[index][0] -= length
            self.nodes[node_id].ranges[index][1] -= length

    self.log_item (node_id)
    consolidated_metadata = self.nodes[node_id].consolidate_metadata(one_line=one_line)

    filename = self.get_file_name(node_id)
    with open(os.path.join(self.path,filename),'r',encoding='utf-8') as theFile:
      file_contents = theFile.read()
      theFile.close()

    length = len(file_contents)
    ranges = self.nodes[node_id].ranges
    meta = re.compile(r'(\/--(?:(?!\/--).)*?--\/)', re.DOTALL) # \/--((?!\/--).)*--\/
    for single_range in ranges:
     
      for section in meta.finditer(file_contents[single_range[0]:single_range[1]]):
        start = section.start()+single_range[0]
        end = start + len(section.group())
        first_splice = file_contents[:start]
        second_splice = file_contents[end:]
        file_contents = first_splice
        file_contents += second_splice 
        adjust_ranges(filename, start, len(section.group()))
    
    new_file_contents = file_contents[0:ranges[-1][1]-2]
    new_file_contents += consolidated_metadata
    new_file_contents += file_contents[ranges[-1][1]:]
    with open(os.path.join(self.path,filename),'w', encoding='utf-8') as theFile:
      theFile.write(new_file_contents)
      theFile.close()
    return(consolidated_metadata)

  def build_tag_info(self):
    """ Rebuilds metadata for the entire project """
    
    self.tagnames={}
    for node in self.nodes:
      self.rebuild_node_tag_info(node)

  def rebuild_node_tag_info(self, node):
    """ Rebuilds metadata info for a single node """

    for entry in self.nodes[node].metadata.entries:
      if entry.tag_name.lower() != 'title':
        if entry.tag_name not in self.tagnames:
          self.tagnames[entry.tag_name]={}
        if not isinstance(entry.value, list):
          entryvalues=[entry.value]
        else:
          entryvalues=entry.value
        for value in entryvalues:
          if value not in self.tagnames[entry.tag_name]:
            self.tagnames[entry.tag_name][value]=[]
          self.tagnames[entry.tag_name][value].append(node)  

  
 
  

  def import_file(self, filename):
     with open(os.path.join(self.path, filename),'r',encoding='utf-8',) as theFile:
          full_file_contents = theFile.read()
          theFile.close()

     date = creation_date(os.path.join(self.path, filename))
     now = datetime.datetime.now()
     contents = '\n\n'
     contents += "/-- ID:" + self.next_index()  + '\n'
     contents += 'timestamp:'+self.timestamp(date) + '\n'
     contents += 'imported:'+self.timestamp(now) + '\n'
     contents += " --/"
    
     full_file_contents += contents

     with open(os.path.join(self.path, filename),'w',encoding='utf-8',) as theFile:
          full_file_contents = theFile.write(full_file_contents)
          theFile.close()

     return self.parse_file(filename)


  def get_node_relationships(self, node_id):
    return interlinks.Interlinks(self, node_id).render

  def compile_all(self):
    for node_id in list(self.dynamic_defs):
      self.compile(node_id)

  
  """
  Removing and renaming files
  """

  def remove_file(self, filename):
    """ 
    removes the file from the project object 
    """
    filename = os.path.basename(filename)
    if filename in self.files:
      for node_id in self.files[filename]['nodes']:
        if node_id in self.dynamic_defs:
          self.dynamic_defs.remove(node_id)

        # REFACTOR
        # delete it from the self.tagnames array -- duplicated from delete_file()
        for tagname in list(self.tagnames):
          for value in list(self.tagnames[tagname]):
            if node_id in self.tagnames[tagname][value]:
              self.tagnames[tagname][value].remove(node_id)
            if len(self.tagnames[tagname][value]) == 0:
              del self.tagnames[tagname][value]
        del self.nodes[node_id]
      del self.files[filename]
    return None

  def handle_renamed(self, old_filename, new_filename):
    new_filename = os.path.basename(new_filename)
    old_filename = os.path.basename(old_filename)
    self.files[new_filename] = self.files[old_filename]
    for node_id in self.files[new_filename]['nodes']:
      self.nodes[node_id].filename = new_filename
      self.nodes[node_id].full_path = os.path.join(self.path, new_filename)
    if new_filename != old_filename:
      del self.files[old_filename]  

  """ 
  Methods for filtering unwanted files 
  """

  def filter_filenames(self, filename):
    """ Filters out files to skip altogether """
    skip_files = [
        '.gitignore',
        '.DS_Store', 
        'urtext_log 2.txt', 
        self.settings['logfile']
        ]
    skip_filename_fragments = ['.icloud']
    if filename in skip_files:
        return
    for fragment in skip_filename_fragments:
        if fragment in filename:
          return None
    return filename

  def get_file_contents(self, filename):
    """ returns the file contents, filtering out Unicode Errors, directories, other errors """   

    try:
      with open(os.path.join(self.path, filename),'r',encoding='utf-8',) as theFile:
        full_file_contents = theFile.read()
        theFile.close()
    except IsADirectoryError:
      return None
    except UnicodeDecodeError:
      self.log_item('UnicodeDecode Error: ' + filename)
      return None
    except:
      self.log_item('Urtext not including ' + filename)
      return None

    return full_file_contents

  def new_file_node(self, date=None):
    """ 
    add a new FILE-level node programatically 
    """
    if date == None:
      date = datetime.datetime.now()
    node_id = self.next_index()
    contents = "\n\n\n"
    contents += "/-- ID:" + node_id + '\n'
    contents += 'Timestamp:'+self.timestamp(date) + '\n'
    contents += " --/"

    filename = node_id + '.txt'

    with open(os.path.join(self.path, filename), "w") as theFile:
      theFile.write(contents)
      theFile.close()

    self.files[filename] = {}
    self.files[filename]['nodes']=[node_id]
    self.nodes[node_id] = UrtextNode(os.path.join(self.path, filename), contents)
    return filename

  def add_inline_node(self, datestamp, filename, contents):
    if filename == None:
      return None
    if os.path.basename(filename) not in self.files: 
      if self.parse_file(os.path.basename(filename)) == None:
        return None
    filename = os.path.basename(filename)
    node_id = self.next_index()
    self.nodes[node_id] = UrtextNode(os.path.join(self.path, filename), contents)
    
    self.files[filename]['nodes'].append(node_id)
    return node_id


  

  """ 
  Reindexing (renaming) Files 
  """
  def reindex_files(self):
    # Indexes all file-level nodes in the project

    # Calculate the zero-padded digit length of the file prefix:
    prefix = 0
    remaining_root_nodes = list(self.root_nodes())
    indexed_nodes = list(self.indexed_nodes())
    for node_id in indexed_nodes:
      if node_id in remaining_root_nodes:
        self.nodes[node_id].prefix = prefix
        remaining_root_nodes.remove(node_id)
        prefix += 1

    unindexed_root_nodes = [ self.nodes[node_id] for node_id in remaining_root_nodes ]
    date_sorted_nodes = sorted(unindexed_root_nodes, key=lambda r: r.date, reverse=True)

    for node in date_sorted_nodes:
      node.prefix = prefix
      prefix += 1
    return self.rename_file_nodes(list(self.files), reindex=True)
  

  def rename_file_nodes(self, filenames, reindex=False):

    if isinstance(filenames, str):
      filenames = [filenames]
    used_names = []

    indexed_nodes = list(self.indexed_nodes())
    filename_template = list(self.settings['filenames'])
    renamed_files = {}
    date_template = None

    for index in range(0,len(filename_template)):
      if 'DATE' in filename_template[index]:
        date_template = filename_template[index].replace('DATE','').strip()
        filename_template[index] = 'DATE'

    for filename in filenames:
      old_filename = os.path.basename(filename)
      root_node_id = self.get_root_node_id(old_filename)
      root_node = self.nodes[root_node_id]   

      new_filename = ' | '.join(filename_template)
      new_filename = new_filename.replace('TITLE', root_node.title)
      if root_node_id not in indexed_nodes and date_template != None:
        new_filename = new_filename.replace('DATE', datetime.datetime.strftime(root_node.date, date_template))
      else: 
        new_filename = new_filename.replace('DATE |','')
      if reindex == True:
        padded_prefix = '{number:0{width}d}'.format(
            width=self.prefix_length(), 
            number=int(root_node.prefix))
        new_filename = new_filename.replace('PREFIX', padded_prefix)
      else:
        old_prefix = old_filename.split('|')[0].strip()
        new_filename = new_filename.replace('PREFIX', old_prefix)      
      new_filename = new_filename.replace('/','-')
      new_filename = new_filename.replace('.',' ')
      new_filename = new_filename.replace('’',"'")
      new_filename += '.txt'
      if new_filename not in used_names:
        renamed_files[old_filename] = new_filename 
        used_names.append(new_filename)

      else:
        self.log_item('Renaming ' + old_filename + ' results in duplicate filename: '+new_filename)

    for filename in renamed_files:
      old_filename = filename
      new_filename = renamed_files[old_filename]
      self.log_item('renaming '+old_filename+' to '+new_filename)
      os.rename(os.path.join(self.path, old_filename), os.path.join(self.path, new_filename))
      self.handle_renamed(old_filename, new_filename)

    return renamed_files

  def prefix_length(self):
    """ Determines the prefix length for indexing files (requires an already-compiled project) """ 

    prefix_length = 0
    num_files = len(self.files)
    while num_files > 1:
      prefix_length += 1
      num_files /= 10
    return prefix_length

  """ 
  Cataloguing Nodes
  """
  def list_nodes(self):
    """returns a list of all nodes in the project, in plain text"""
    output=''
    for node_id in list(self.indexed_nodes()):
      title = self.nodes[node_id].title
      output += title + ' >' + node_id + '\n'
    for node_id in list(self.unindexed_nodes()):
      title=self.nodes[node_id].title
      output += title + ' >' + node_id + '\n'
    return output

  def unindexed_nodes(self):
    """ 
    returns an array of node IDs of unindexed nodes, 
    in reverse order (most recent) by date 
    """
    unindexed_nodes = [ ]
    for node_id in list(self.nodes):
      if self.nodes[node_id].metadata.get_tag('index') == []:
        unindexed_nodes.append(node_id)
    sorted_unindexed_nodes = sorted(unindexed_nodes, key=lambda node_id: self.nodes[node_id].date, reverse=True)
    return sorted_unindexed_nodes

  def indexed_nodes(self):
    """ returns an array of node IDs of indexed nodes, in indexed order """

    indexed_nodes_list = []
    node_list = list(self.nodes)
    for node in node_list:
      if self.nodes[node].metadata.get_tag('index') != []:
          indexed_nodes_list.append([node, int((self.nodes[node].metadata.get_tag('index')[0]))])
    sorted_indexed_nodes=sorted(indexed_nodes_list, key=lambda item: item[1])
    for i in range(len(sorted_indexed_nodes)):
      sorted_indexed_nodes[i]=sorted_indexed_nodes[i][0]
    return sorted_indexed_nodes

  def root_nodes(self):
    """
    Returns the IDs of all the root (file level) nodes
    """
    root_nodes = []
    for node_id in self.nodes:
      if self.nodes[node_id].root_node == True:
        root_nodes.append(node_id)
    return root_nodes


  

  """ 
  Full Text search implementation using Whoosh (unfinished) 
  These methods are currently unused
  """

  def build_search_index(self):
    schema = Schema(title=TEXT(stored=True), path=ID(stored=True), content=TEXT)
    if not exists_in(os.path.join(self.path,"index"), indexname="urtext"):
      self.ix = create_in(os.path.join(self.path,"index"), schema, indexname="urtext")
    else:
      self.ix = open_dir(os.path.join(self.path,"index"), indexname="urtext") 
    writer = self.ix.writer()
    for node_id in self.nodes:
      writer.add_document(
        title = self.nodes[node_id].title,
        content = self.nodes[node_id].contents,
        path = node_id)
    writer.commit()
    
  def search(self, string):
   
    final_results=''
    with self.ix.searcher() as searcher:
      query = QueryParser("content", self.ix.schema).parse(string)
      results = searcher.search(query, limit=1000)  
      results.formatter = UppercaseFormatter()
      final_results += 'TOTAL RESULTS: '+ str(len(results)) + '\n\n'      
      for result in results:
        final_results += '\n\n---- in >' + result['path'] +'\n\n'
        test = self.nodes[result['path']].contents()
        final_results += result.highlights("content", test)

    return final_results

  """ 
  Other Features, Utilities
  """
  def get_parent(self, child_node_id):
    """ Given a node ID, returns its parent, if any """
    filename = self.nodes[child_node_id].filename
    start = self.nodes[child_node_id].ranges[0][0]
    for other_node in [other_id for other_id in self.files[filename]['nodes'] if other_id != child_node_id]:
      if self.is_in_node(start-2, other_node):
        return other_node
    return None

  def is_in_node(self, position, node_id):
    """ Given a position, and node_id, returns whether the position is in the node """
    for this_range in self.nodes[node_id].ranges:
      if position > this_range[0] - 2 and position < this_range[1] + 2:
        return True
    return False

  def get_node_id_from_position(self, filename, position):
    """ Given a position, returns the Node ID it's in """

    for node_id in self.files[os.path.basename(filename)]['nodes']:        
        if self.is_in_node(position, node_id):
          return node_id
    return None


  def get_link(self, string, position=None):
    """ Given a line of text passed from an editorm, returns finds a node or web link """

    url_scheme=re.compile('https?://[-\w.\/#]+')
    if re.search(url_scheme, string):
      url=re.search(url_scheme, string).group(0)
      return ['HTTP', url]

    link = None
    # first try looking where the cursor is positioned
    if position:
      for index in range(0, 3):
        if re.search(node_link_regex, string[position-index:position-index+5]):
          link = re.search(node_link_regex, string[position-index:position-index+5]).group(0)

    # next try looking ahead:
    if not link:
      after_cursor = string[position:]
      if re.search(node_link_regex, after_cursor):
        link =  re.search(node_link_regex, after_cursor).group(0)

    if not link:
      before_cursor = string[:position]
      if re.search(node_link_regex, before_cursor):
        link = re.search(node_link_regex, before_cursor).group(0)

    if not link:
      return None
      
    node_id = link.split(':')[0].strip('>')
    if node_id.strip() in self.nodes:
      position = self.nodes[node_id].ranges[0][0]
      return ['NODE', node_id, position]
    else:
      self.log_item('Node ' + node_id + ' is not in the project')
      return None
    self.log_item('No node ID found on this line.')
    return None

  def timeline(self, nodes):
    """ Given a list of nodes, returns a timeline """

    return urtext.timeline.timeline(self, nodes)
    
  def is_duplicate_id(self, node_id, filename):
    if node_id in self.nodes:
      self.log_item('Duplicate node ID ' +  node_id + ' in ' +  filename + ' -- already used in '+self.nodes[node_id].filename+' (>'+node_id+')')
      self.remove_file(filename)
      return True
    return False

  def log_item(self,item): # Urtext logger
    self.log.info(item)
    self.build_response += item + '\n'
  
  def timestamp(self, date):
    """ Given a datetime object, returns a timestamp in the format set in project_settings, or the default """

    timestamp_format = '<'+ self.settings['timestamp_format'][0] + '>'
    return date.strftime(timestamp_format)

  def get_settings_from(self, node):
    for entry in node.metadata.entries:
        self.settings[entry.tag_name.lower()] = entry.value

  def next_index(self):
    for index in self.indexes:
      if ''.join(index) not in self.nodes:
        return ''.join(index)

  def dynamic_nodes(self):

    self.dynamic_nodes={}
    for node_id in self.nodes:
      if node[node_id].dynamic == True:
        self.dynamic_nodes.append(node_id)

  def get_file_name(self, node_id):

    for node in self.nodes:
      if node == node_id:
        return self.nodes[node].filename
    return None # if no node found

  def get_root_node_id(self, filename):
    """
    Given a filename, returns the root Node's ID
    """
    for node_id in self.files[filename]['nodes']:
      if self.nodes[node_id].root_node == True:
        return node_id
    return None

  def get_all_files(self):

    all_files=[]
    for node in self.nodes:
      all_files.append(self.nodes[node].filename)
    return all_files

""" 
Helpers 
"""

def setup_logger(name, log_file, level=logging.INFO):
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    if not os.path.exists(log_file):
      with open(log_file,'w',encoding='utf-8') as theFile:
        theFile.close()
    handler = logging.FileHandler(log_file, mode='a')
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    return logger


def creation_date(path_to_file):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return datetime.datetime.fromtimestamp(os.path.getctime(path_to_file))
    else:
        stat = os.stat(path_to_file)
        try:
            return datetime.datetime.fromtimestamp(stat.st_birthtime)
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return datetime.datetime.fromtimestamp(stat.st_mtime)


