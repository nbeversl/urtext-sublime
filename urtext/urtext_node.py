from urtext.metadata import NodeMetadata
import os
import re

class UrtextNode:
  """ Takes contents, filename. If contents is unspecified, the node is the entire file. """

  def __init__(self, filename, contents=''):
    self.filename = os.path.basename(filename)
    self.position = None
    self.tree = None
    self.contents = contents
    self.metadata = NodeMetadata(self.contents)
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
    
    self.metadata = NodeMetadata(self.contents)
    #self.title = 'test' #re.search(r'[^\d]+|$',filename).group(0)
    
    self.index = self.metadata.get_tag('index')
    

  def set_index(self, new_index):
    self.index = new_index
  
  def set_title(self, new_title):
    self.title = new_title

  def log(self):
    logging.info(self.node_number)
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
