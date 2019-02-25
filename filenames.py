import sublime
import sublime_plugin
import Urtext.urtext as Urtext
import Urtext.meta as Meta
import os

class ManageFilenames(sublime_plugin.EventListener):
    def on_pre_save(self, view):
        path = Urtext.get_path(view.window())
        filename = view.file_name()
        metadata = Meta.NodeMetadata(os.path.join(path,filename))
        metadata.log()
        title = metadata.get_tag('title')[0].strip()
        index = metadata.get_tag('index')       
        file = Urtext.UrtextFile(filename)   
        if index != []:
            print(index)
            file.set_index(index[0])     
        file.set_title(title)
        old_filename = file.filename
        new_filename = file.rename_file()
        v = view.window().find_open_file(old_filename)
        if v:
          v.retarget(os.path.join(path,new_filename))
          #set_name(new_filename)