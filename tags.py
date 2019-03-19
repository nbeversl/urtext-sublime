import sublime_plugin
import sublime_urtext
import Urtext.meta

class ShowTags(sublime_plugin.WindowCommand):
    def run(self):
        def clear_white_space(text):
          text = text.strip()
          text = " ".join(text.split()) #https://stackoverflow.com/questions/8270092/remove-all-whitespace-in-a-string-in-python
          return text
        files = sublime_urtext.get_files(self.window)
        tags = []
        for filename in files:
          try:
            with open(os.path.join(Urtext.get_path(self.view.window()), file),'r',encoding='utf-8') as this_file:
              contents = this_file.read()
              metadata = Urtext.meta.get_meta(contents)
              for entry in metadata:
                if 'tags' in entry:
                  for tag in entry['tags']:
                    tags.append(tag)              
            menu.append(item)
          except:
            pass
        self.sorted_menu = sorted(menu,key=lambda item: item[1] )
        def open_the_file(index):
          if index != -1:
            self.window.open_file(path+"/"+self.sorted_menu[index][1])
        self.window.show_quick_panel(self.sorted_menu, open_the_file)

