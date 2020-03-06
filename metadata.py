import sublime
import sublime_plugin
import os

from .sublime_urtext import show_panel,UrtextTextCommand,refresh_project_text_command ,node_id_regex, NodeBrowserMenu, open_urtext_node


class FindByMetaCommand(UrtextTextCommand):
    
    @refresh_project_text_command
    def run(self):
        self.tagnames = [value for value in self._UrtextProjectList.current_project.tagnames]
        self.view.window().show_quick_panel(self.tagnames, self.list_values)

    def list_values(self, index):
        self.selected_tag = self.tagnames[index]
        self.values = [
            value for value in self._UrtextProjectList.current_project.tagnames[self.selected_tag]
        ]
        self.values.insert(0, '< all >')
        self.view.window().show_quick_panel(self.values, self.display_files)

    def display_files(self, index):

        self.selected_value = self.values[index]
        if self.selected_value == '< all >':
            pass  # fix this
        self.menu = NodeBrowserMenu(
            self._UrtextProjectList,
            nodes=self._UrtextProjectList.current_project.tagnames[self.selected_tag][self.selected_value]
            )
        show_panel(self.view.window(), self.menu.display_menu,
                   self.open_the_file)

    def open_the_file(self, selected_option): 
        # TODO refactor from below
        if selected_option == -1:
            return
        new_view = self.view.window().open_file(
            os.path.join(
                self._UrtextProjectList.current_project.path,
                self.menu.get_values_from_index(selected_option).filename))
        if len(selected_option) > 3 and selected_option[3] != None:
            self.locate_node(selected_option[3], new_view)

    def list_files(self, index):
        self.selected_value = self.values[index]
        new_view = self.view.window().new_file()
        new_view.set_scratch(True)
        if self.selected_value == '< all >':
            new_view.run_command("insert_snippet", {
                "contents":
                '\nFiles found for tag: %s\n\n' % self.selected_value
            })
            for value in self._UrtextProjectList.current_project.tagnames[self.selected_tag]:
                new_view.run_command("insert_snippet",
                                     {"contents": value + "\n"})
                for node in self._UrtextProjectList.current_project.tagnames[self.selected_tag][value]:
                    new_view.run_command("insert_snippet",
                                         {"contents": " -> " + node + "\n"})
                new_view.run_command("insert_snippet", {"contents": "\n"})

        else:
            new_view.run_command(
                "insert_snippet", {
                    "contents":
                    '\nFiles found for tag: %s with value %s\n\n' %
                    (self.selected_tag, self.selected_value)
                })
            for node in self._UrtextProjectList.current_project.tagnames[self.selected_tag][
                    self.selected_value]:
                new_view.run_command("insert_snippet",
                                     {"contents": " -> " + node + "\n"})

class ShowTagsCommand(sublime_plugin.TextCommand):
    
    @refresh_project_text_command
    def run(self):
        self.tag_values = [value for value in self._UrtextProjectList.current_project.tagnames['tags']]
        self.tag_values.insert(0, '< all >')
        self.view.window().show_quick_panel(self.tag_values,
                                            self.display_files)

    def display_files(self, index):

        self.selected_value = self.tag_values[index]
        if self.selected_value == '< all >':
            pass  # fix this
        self.menu = NodeBrowserMenu(
           self._UrtextProjectList, 
           project=self._UrtextProjectList.current_project,
           nodes=self._UrtextProjectList.current_project.tagnames['tags'][self.selected_value])
        show_panel(self.view.window(), self.menu.display_menu,
                   self.open_the_file)

    def open_the_file(self,
                      selected_option):  # copied from below, refactor later.
        if selected_option == -1:
            return
        path = get_path(self.view)
        new_view = self.view.window().open_file(
            os.path.join(
                path,
                self.menu.get_values_from_index(selected_option).filename))
        #if selected_option[3] and selected_option[3] != None:
        #self.locate_node(selected_option[3], new_view)

    def list_files(self, index):
        self.selected_value = self.values[index]
        new_view = self.view.window().new_file()
        new_view.set_scratch(True)
        if self.selected_value == '< all >':
            new_view.run_command("insert_snippet", {
                "contents":
                '\nFiles found for tag: %s\n\n' % self.selected_value
            })
            for value in self._UrtextProjectList.current_project.tagnames[self.selected_tag]:
                new_view.run_command("insert_snippet",
                                     {"contents": value + "\n"})
                for node in _UrtextProjectList.current_project.tagnames[self.selected_tag][value]:
                    new_view.run_command("insert_snippet",
                                         {"contents": " -> " + node + "\n"})
                new_view.run_command("insert_snippet", {"contents": "\n"})

        else:
            new_view.run_command(
                "insert_snippet", {
                    "contents":
                    '\nFiles found for tag: %s with value %s\n\n' %
                    (self.selected_tag, self.selected_value)
                })
            for node in self._UrtextProjectList.current_project.tagnames[self.selected_tag][
                    self.selected_value]:
                new_view.run_command("insert_snippet",
                                     {"contents": " -> " + node + "\n"})


class UrtextMetadataListCommand(sublime_plugin.TextCommand):

    @refresh_project_text_command
    def run(self):
        self._UrtextProjectList.current_project.nav_new('zzy')
        open_urtext_node(self.view, 'zzy', 0)
        
