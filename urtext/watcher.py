import time
from urtext.node import UrtextNode
import os
from watchdog.events import FileSystemEventHandler

class UrtextWatcher(FileSystemEventHandler):

    def __init__(self, project):
        self.project = project
        
    def on_modified(self, event):
        print('MODIFIED!')
        print(event)
        filename = event.src_path
        print(filename)
        file = UrtextNode(filename)
        self.project.nodes[file.node_number] = file
        for node_number in self.project.files[os.path.basename(filename)]:
          del self.project.nodes[node_number]
        self.project.build_sub_nodes(filename)

        if '[[' in self.project.nodes[file.node_number].contents:
          self.project.compile(file.node_number)
          self.project.compile(file.node_number)

        self.project.build_tag_info()

    def on_created(self, event):
        print('CREATED!')
        print(event)  
        filename = event.src_path
        file = UrtextNode(filename)
        node_id = self.project.get_node_id(os.path.basename(filename))

        if '[[' in self.project.nodes[file.node_number].contents:
          self.project.compile(file.node_number)

        # not yet working
        #if node_id+'TREE' in [view.name() for view in view.window().views()]:  
        #  ShowInlineNodeTree.run(view)

        # too much, revise later.
        for node in list(self.project.nodes):
          self.project.compile(node)
        
        self.project.build_tag_info()
