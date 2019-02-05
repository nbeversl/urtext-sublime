import sublime
import sublime_plugin
import datetime
import Urtext.meta
import Urtext.urtext
import os
import re

class CompileTodoCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        found_stuff = []
        view = self.view
        self.window = view.window()
        #if self.window.project_data():
            # always save in the current project path if there is one
        #    main_path = self.window.extract_variables()['project_path'][0]['path']
        #else:
        #    main_path = '.'
        print(view.window().extract_variables())
        path = view.window().extract_variables()['project_path']
        files = os.listdir(path)
        print(files)
        for file in files:
            with open(path + '/' + file, 'r', encoding='utf-8') as theFile:
                full_contents = theFile.read()
                marker_regex = '\<TODO\>'
                markers = re.findall(marker_regex, full_contents)
                for marker in markers:
                    contents = full_contents  # reset the contents
                    found_thing = {}
                    position = contents.find(marker)
                    theFile.seek(0)
                    for num, line in enumerate(theFile, 1):
                        if marker in line:
                            foundstuff.append(line)
        new_view = self.window.new_file()
        new_view.set_name('Found Stuff')
        sublime.set_timeout(lambda: self.show_stuff(new_view, found_stuff), 10)

        def show_stuff(self, view, stuff):
            if not view.is_loading():
                self.build_timeline(view, stuff)
            else:
                sublime.set_timeout(lambda: self.show_stuff(view, stuff), 10)
                # https://forum.sublimetext.com/t/how-to-print-text-on-the-output-panel/35226/2
