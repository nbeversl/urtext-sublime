# Urtext - Main
import sublime
import sublime_plugin
import os
import re
import Urtext.datestimes
import Urtext.meta
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))
from anytree import Node, RenderTree
import anytree
import codecs
import logging
import datetime

# note -> https://forum.sublimetext.com/t/an-odd-problem-about-sublime-load-settings/30335

_UrtextProject = None

class Project:

  def __init__(self, window):
    self.path = get_path(window)
    self.window = window
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

      except UnicodeDecodeError:
        print("Urtext Skipping %s, invalid utf-8" % file) 
        continue
      except IsADirectoryError:
        continue
      #except:
      #  print('Urtext Skipping %s' % file)   
      #  continue
      self.files[file] = []
      self.build_sub_nodes(file)
      

    print('URtext has %d files, %d nodes' % (num_files, len(self.nodes)))
    self.build_tag_info()

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
 
    for node in self.nodes:
      if self.nodes[node].filename == filename:
        return node
    return None

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
          print(title)
          new_node = Node(child, parent=parent)
          add_children(new_node)
      add_children(root)
      if root_node_id == '79810920003751':
        print(RenderTree(root))
  
def refresh_nodes(window):

  global _UrtextProject
  if _UrtextProject == None:
    print('_UrtextProject rebuilt')
    _UrtextProject = Project(window)  

def get_path(window):

  """ Returns the Urtext path from settings """
  if window.project_data():
    path = window.project_data()['urtext_path'] # ? 
  else:
    path = '.'
  return path


class InsertNodeCommand(sublime_plugin.TextCommand):

  def run(self, edit):
    node_id = Urtext.datestimes.make_reverse_date_filename(datetime.datetime.now())
    for region in self.view.sel():
      selection = self.view.substr(region)

    node_wrapper = '{{ '+selection+'\n\n /- ID:'+node_id+' -/ \n\n}}'

    self.view.run_command("insert_snippet", {
                             "contents": node_wrapper})  # (whitespace)
    self.view.run_command("save")

class UrtextNode:
  """ Takes contents, filename. If contents is unspecified, the node is the entire file. """

  def __init__(self, filename, contents=''):
    self.filename = os.path.basename(filename)
    self.position = None
    self.contents = contents
    self.metadata = Urtext.meta.NodeMetadata(self.contents)
    self.nested_nodes = []
    if contents == '':
      with open(filename,'r',encoding='utf-8') as theFile:
        self.contents = theFile.read()
        theFile.close()
        self.node_number = re.search(r'(\d{14})',filename).group(0)
    else:
      try:
        self.node_number = self.metadata.get_tag('ID')[0]
      except:
        print('There is is probably a node wrapper without an ID in %s' % self.filename)
    
    self.metadata = Urtext.meta.NodeMetadata(self.contents)
    #self.title = 'test' #re.search(r'[^\d]+|$',filename).group(0)
    
    self.index = self.metadata.get_tag('index')
    

  def set_index(self, new_index):
    self.index = new_index
  
  def set_title(self, new_title):
    self.title = new_title

  def log(self):
    logging.info(self.node_number)
    #logging.info(self.title)
    logging.info(self.index)
    logging.info(self.filename)
    logging.info(self.metadata.log())

  def rename_file(self):
    old_filename = self.filename
    if len(self.index) > 0:
      new_filename = self.index + ' '+ self.title + ' ' + self.node_number + '.txt'
    elif self.title != 'Untitled':
      new_filename = self.node_number + ' ' + self.title + '.txt'
    else:
      new_filename = old_filename
    os.rename(os.path.join(self.path, old_filename), os.path.join(self.path, new_filename))
    self.filename = new_filename
    return new_filename


class UrtextSave(sublime_plugin.EventListener):

  def on_post_save(self, view):    
    global _UrtextProject
  
    try: # not a new file
      file = UrtextNode(view.file_name())
      _UrtextProject.nodes[file.node_number] = file
      for node_number in _UrtextProject.files[os.path.basename(view.file_name())]:
        del _UrtextProject.nodes[node_number]
      _UrtextProject.build_sub_nodes(view.file_name())

    except KeyError: # new file
      print('making new file=')
      file = Urtext.urtext.UrtextNode(view.file_name())
      _UrtextProject.nodes[file.node_number] = file
      _UrtextProject.files[os.path.basename(view.file_name())] = [file.node_number]
 
class RenameFileCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    global _UrtextProject
    path = Urtext.urtext.get_path(self.view.window())
    filename = self.view.file_name()
    node = _UrtextProject.get_node_id(os.path.basename(filename))
    title = _UrtextProject.nodes[node].metadata.get_tag('title')[0].strip()
    index = _UrtextProject.nodes[node].metadata.get_tag('index')
    if index != []:
       _UrtextProject.nodes[node].set_index(index)     
    _UrtextProject.nodes[node].set_title(title)
    old_filename = filename
    new_filename = _UrtextProject.nodes[node].rename_file()
    v = self.view.window().find_open_file(old_filename)
    if v:
      v.retarget(os.path.join(path,new_filename))
      v.set_name(new_filename)

class CopyPathCoolerCommand(sublime_plugin.TextCommand):
  def run(self, edit):
    filename = self.view.window().extract_variables()['file_name']
    self.view.show_popup('`'+filename + '` copied to the clipboard')
    sublime.set_clipboard(filename)

class ShowFilesWithPreview(sublime_plugin.WindowCommand):
    def run(self):
      show_panel(self.window, self.open_the_file)

    def open_the_file(self, selected_option):
      path = get_path(self.window)
      new_view = self.window.open_file(os.path.join(path,selected_option[2])) 
      if selected_option[3] != None:
        self.locate_node(selected_option[3], new_view)

    def locate_node(self, position, view):
      if not view.is_loading(): 
        line = view.line(position)
        view.sel().add(line)
        view.show_at_center(position) 
      else:
        sublime.set_timeout(lambda: self.locate_node(position, view), 10)
         
class LinkToNodeCommand(sublime_plugin.WindowCommand): # almost the same code as show files. Refactor.
    def run(self):
      show_panel(self.window, self.link_to_the_file)

    def link_to_the_file(self, selected_option):
      view = self.window.active_view()
      filename = os.path.basename(selected_option[2])
      view.run_command("insert", {"characters": ' -> '+ filename + ' | '})

class LinkNodeFromCommand(sublime_plugin.WindowCommand): # almost the same code as show files. Refactor.
    def run(self):
      self.current_file = os.path.basename(self.window.active_view().file_name())
      show_panel(self.window, self.link_from_the_file)

    def link_from_the_file(self, selected_option):
        new_view = self.window.open_file(selected_option[2])
        sublime.set_clipboard(' -> ' + self.current_file)
        self.show_tip(new_view)

    def show_tip(self, view):
      if not view.is_loading(): 
        view.show_popup('Link to ' + self.current_file + ' copied to the clipboard')
      else:
        sublime.set_timeout(lambda: self.show_tip(view), 10)
      
def show_panel(window, main_callback):
  global _UrtextProject  
  refresh_nodes(window)
  menu = []
  for node_id in _UrtextProject.indexed_nodes():
    item = []
    metadata = _UrtextProject.nodes[node_id].metadata
    item.append(metadata.get_tag('title')[0])  # should title be a list or a string? 
    item.append(Urtext.datestimes.date_from_reverse_date(node_id))
    item.append(_UrtextProject.nodes[node_id].filename)
    item.append(_UrtextProject.nodes[node_id].position)
    menu.append(item)
  for node_id in _UrtextProject.unindexed_nodes():
    item = []
    metadata = _UrtextProject.nodes[node_id].metadata
    item.append(metadata.get_tag('title')[0])  # should title be a list or a string? 
    item.append(Urtext.datestimes.date_from_reverse_date(node_id))
    item.append(_UrtextProject.nodes[node_id].filename)
    item.append(_UrtextProject.nodes[node_id].position)
    menu.append(item)
  display_menu = []
  for item in menu: # there is probably a better way to copy this list.
    new_item = [item[0], item[1].strftime('<%a., %b. %d, %Y, %I:%M %p>')]
    display_menu.append(new_item)

  def private_callback(index):
    main_callback(menu[index])

  window.show_quick_panel(display_menu, private_callback)

def get_contents(view):
  contents = view.substr(sublime.Region(0, view.size()))
  return contents

class ShowAllNodesCommand(sublime_plugin.TextCommand):
  def run(self,edit):
    global _UrtextProject
    refresh_nodes(self.view.window())
    new_view = self.view.window().new_file()
    for node_id in _UrtextProject.indexed_nodes():
      title = _UrtextProject.nodes[node_id].metadata.get_tag('title')[0]
      new_view.run_command("insert", {"characters": '-> ' + title + ' ' + node_id + '\n'})
    for node_id in _UrtextProject.unindexed_nodes():
      title = _UrtextProject.nodes[node_id].metadata.get_tag('title')[0]
      new_view.run_command("insert", {"characters": '-> ' + title + ' ' + node_id + '\n'})
      
class DeleteThisNodeCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        global _UrtextProject
        file_name = self.view.file_name()
        if self.view.is_dirty():
            self.view.set_scratch(True)
        self.view.window().run_command('close_file')

        # delete it from the file system
        os.remove(file_name)
                
        # delete its inline nodes from the Project node array:
        for node_id in _UrtextProject.files[os.path.basename(file_name)]:
          del _UrtextProject.nodes[node_id]

        # delete it from the Project node array:
        node_id = _UrtextProject.get_node_id(os.path.basename(file_name))
        del _UrtextProject.nodes[node_id]


        # delete its filename from the Project file array:
        del _UrtextProject.files[os.path.basename(file_name)]

