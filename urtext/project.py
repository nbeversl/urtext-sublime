import codecs
import re
import datetime
import itertools
import platform
import logging
import operator
import difflib
import json
import os 

from urtext_sublime.anytree import Node
from urtext_sublime.anytree import RenderTree
from urtext_sublime.anytree import PreOrderIter
from urtext_sublime.urtext.timeline import timeline
from urtext_sublime.urtext.node import UrtextNode
import interlinks

#rom urtext_sublime.whoosh.fields import Schema, TEXT, ID
#from urtext_sublime.whoosh.index import create_in, exists_in, open_dir
#from urtext_sublime.whoosh.query import *
#from urtext_sublime.whoosh.qparser import QueryParser
#from urtext_sublime.whoosh.highlight import UppercaseFormatter
#from urtext_sublime import whoosh
node_id_regex = r'\b[0-9,a-z]{3}\b'
node_link_regex = r'>[0-9,a-z]{3}\b'

class NoProject(Exception):
  """ Raised when no Urtext nodes are in the folder """
  pass

class UrtextProject:
  """ Urtext project object """

  def __init__(self, path, 
        make_new_files=True, 
        rename=False, 
        recursive=False, 
        import_project=False,
        init_project=False):

    self.path = path
    self.build_response = []
    self.conflicting_files = []
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
      'node_list': 'zzz.txt',
      'metadata_list': 'zzy.txt'
      }
    self.to_import = []
    self.settings_initialized = False
    self.dynamic_nodes = {} # { target : definition, etc.}
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

    if self.nodes == {}:
      if init_project == True:
        self.log_item('Initalizing a new Urtext project in '+path)
      else:
        raise NoProject('No Urtext nodes in this folder.')       

    for node_id in list(self.nodes): # needs do be done once manually on project init
      self.parse_meta_dates(node_id) 

    self.compile()

    self.compiled = True    

    self.update()

  def update(self):
    """ 
    Main method to keep the project updated. 
    Should be called whenever file or directory content changes
    """      
    self.build_alias_trees() # Build copies of trees wherever there are Node Pointers (>>)
    self.rewrite_recursion()
    self.compile()
      
    # Update lists:
    self.update_node_list()
    self.update_metadata_list()
    self.write_log()
  
  """ 
  Parsing
  """

  def parse_file(self, filename, add=True, import_project=False):
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
        full_file_contents.find(symbol, loc+2) 
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

    """
    pass the node's dynamic definitions up into the project object
    self.dynamic_nodes = { target_id : definition }

    """    
    for target_id in new_node.dynamic_definitions.keys():
      if target_id in self.dynamic_nodes and self.dynamic_definitions[target].source_id != new_node.id:
        self.log_item('Node >' + target_id + ' has duplicate definition in >' + new_node.id +'. Keeping the definition in >'+self.dynamic_nodes[target_id].source_id + '.')
      else:
        self.dynamic_nodes[target_id] = new_node.dynamic_definitions[target_id]

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
            self.nodes[this_node.name].get_title()) + ' >' + this_node.name + '\n'
      else:
        tree_render += "%s%s" % (pre, '? (Missing Node): >'+ this_node.name + '\n')
    return tree_render

  """
  Compiling dynamic nodes
  """  

  def compile(self):
    """ Main method to compile dynamic nodes definitions """
    
    files_to_modify = {}

    for target_id in self.dynamic_nodes:
      """
      Make sure the target node exists.
      """
      source_id = self.dynamic_nodes[target_id].source_id
      if target_id not in self.nodes:        
        self.log_item('Dynamic node definition >' + source_id + ' points to nonexistent node >' + target_id)
        continue      
      filename = self.nodes[target_id].filename
      if filename not in files_to_modify:
        files_to_modify[filename] = []
      files_to_modify[filename].append(target_id) 

    # rebuid the text for each file all at once
    for file in files_to_modify:
      """
      Get current file contents
      """
      with open(os.path.join(self.path, file), "r", encoding='utf-8') as theFile:
        old_file_contents = theFile.read()
        theFile.close()

      updated_file_contents = old_file_contents

      for target_id in files_to_modify[file]:
        old_node_contents = self.nodes[target_id].contents()
        dynamic_definition = self.dynamic_nodes[target_id]

        contents = ''
        metadata = '/--\n'
        
        
        if dynamic_definition.tree and dynamic_definition.tree in self.nodes:
          contents += self.show_tree_from(dynamic_definition.tree)
 
        else:
          included_nodes = []
          excluded_nodes = []
          
          for item in dynamic_definition.include:
            key, value = item[0],item[1]
            included_nodes.extend(self.tagnames[key][value])

          for item in dynamic_definition.exclude:
            key, value = item[0],item[1]
            excluded_nodes.extend(self.tagnames[key][value])

          for node in excluded_nodes:
            if node in included_nodes:
              included_nodes.remove(node)

          """
          Assemble the node collection from the list
          """
          included_nodes = [self.nodes[node_id] for node_id in included_nodes]

          """
          build timeline if specified
          """
          if dynamic_definition.show == 'timeline':
            contents += urtext.timeline.timeline(self, included_nodes)

          else:
            """
            otherwise this is a list, so sort the nodes
            """
            if dynamic_definition.sort_tagname != None:
              included_nodes = sorted(included_nodes, key=lambda node: node.metadata.get_tag( dynamic_definition.sort_tagname))
            else:
              included_nodes = sorted(included_nodes, key=lambda node: node.date)
            
            for targeted_node in included_nodes:
              if dynamic_definition.show == 'title':
                show_contents = targeted_node.set_title()
              if dynamic_definition.show == 'full_contents':
                show_contents = targeted_node.content_only().strip('\n').strip()
              contents += show_contents + ' >' + targeted_node.id + '\n-\n'

        """
        add metadata to dynamic node
        """
        metadata += 'ID:'+target_id+'\n'
        metadata += 'kind: dynamic\n'
        metadata += 'defined in: >' + dynamic_definition.source_id + '\n'
        metadata += '--/'
    
        updated_node_contents = contents + metadata
        
        """
        add indentation if specified
        """
        
        if dynamic_definition.spaces:
          updated_node_contents = indent(updated_node_contents, dynamic_definition.spaces)
        
        updated_file_contents = updated_file_contents.replace(old_node_contents, updated_node_contents)
        
      """
      Update this file if it has changed
      """
      if updated_file_contents != old_file_contents:
      
        with open(os.path.join(self.path, file), "w", encoding='utf-8') as theFile:
          theFile.write(updated_file_contents)
          theFile.close()   
        self.parse_file(os.path.join(self.path,file))  

  """
  Refreshers
  """
  def update_node_list(self):
    """ Refreshes the Node List file """
    if 'zzz' in self.nodes:
      node_list_file = self.nodes['zzz'].filename
    else:
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
          n = Node(self.nodes[node_id].get_title() +' >'+node_id)
          n.parent = t
    if 'zzy' in self.nodes:
      metadata_file = self.nodes['zzy'].filename
    else:
      metadata_file = self.settings['metadata_list']

    with open(os.path.join(self.path, metadata_file), 'w', encoding='utf-8') as theFile:
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

    filename = self.nodes[node_id].filename
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
        for target_id in list(self.dynamic_nodes):
          if self.dynamic_nodes[target_id].source_id == node_id:
            del self.dynamic_nodes[target_id]

        # REFACTOR
        # delete it from the self.tagnames array -- duplicated from delete_file()
        for tagname in list(self.tagnames):
          for value in list(self.tagnames[tagname]):
            if value in self.tagnames[tagname]: # in case it's been removed              
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
  Methods for filtering files to skip 
  """

  def filter_filenames(self, filename):
    """ Filters out files to skip altogether """

    """ Omit system files """
    if filename[0] == '.':
      return None

    """ Omit the log file """
    skip_files = [
        self.settings['logfile']
        ]
    if filename in skip_files:
        return

    """ Omit files containing these fragments """
    conflict_filename_fragments = [ 
      'conflicted copy', # Dropbox 
     ]
    for fragment in conflict_filename_fragments:
      if fragment in filename:
        self.conflicting_files.append(filename)
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

      new_filename = ' - '.join(filename_template)
      new_filename = new_filename.replace('TITLE', root_node.get_title())
      if root_node_id not in indexed_nodes and date_template != None:
        new_filename = new_filename.replace('DATE', datetime.datetime.strftime(root_node.date, date_template))
      else: 
        new_filename = new_filename.replace('DATE -','')
      if reindex == True:
        padded_prefix = '{number:0{width}d}'.format(
            width=self.prefix_length(), 
            number=int(root_node.prefix))
        new_filename = new_filename.replace('PREFIX', padded_prefix)
      else:
        old_prefix = old_filename.split('-')[0].strip()
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
      title = self.nodes[node_id].get_title()
      output += title + ' >' + node_id + '\n-\n'
    for node_id in list(self.unindexed_nodes()):
      title=self.nodes[node_id].get_title()
      output += title + ' >' + node_id + '\n-\n'
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
        title = self.nodes[node_id].get_title(),
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

    return timeline.timeline(self, nodes)
    
  def is_duplicate_id(self, node_id, filename):
    if node_id in self.nodes:
      self.log_item('Duplicate node ID ' +  node_id + ' in ' +  filename + ' -- already used in '+self.nodes[node_id].filename+' (>'+node_id+')')
      self.remove_file(filename)
      return True
    return False

  def log_item(self,item): # Urtext logger
    self.build_response.append(item)

  def write_log(self):
    for item in self.build_response:
      self.log.info(item + '\n')
    self.build_response = []

  def timestamp(self, date):
    """ Given a datetime object, returns a timestamp in the format set in project_settings, or the default """

    timestamp_format = '<'+ self.settings['timestamp_format'][0] + '>'
    return date.strftime(timestamp_format)

  def get_settings_from(self, node):
    for entry in node.metadata.entries:
        self.settings[entry.tag_name.lower()] = entry.value

  def get_file_name(self, node_id):
    return self.nodes[node_id].filename
    
  def next_index(self):
    for index in self.indexes:
      if ''.join(index) not in self.nodes:
        return ''.join(index)

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

def indent(contents, spaces=4):
  content_lines = contents.split('\n')
  for index in range(len(content_lines)):
      if content_lines[index].strip() != '':
        content_lines[index] = ' ' * spaces + content_lines[index] 
  return '\n'.join(content_lines)  

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


