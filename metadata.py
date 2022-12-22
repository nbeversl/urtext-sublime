import sublime
import sublime_plugin
import os

from .sublime_urtext import show_panel,UrtextTextCommand,refresh_project_text_command, NodeBrowserMenu, open_urtext_node

class FindByMetaCommand(UrtextTextCommand):
    
    @refresh_project_text_command
    def run(self):
        self.keynames = [value for value in self._UrtextProjectList.current_project.keynames]
        self.view.window().show_quick_panel(self.keynames, self.list_values)

    def list_values(self, index):
        self.selected_tag = self.keynames[index]
        self.values = [
            value for value in self._UrtextProjectList.current_project.keynames[self.selected_tag]
        ]
        self.values.insert(0, '< all >')
        self.view.window().show_quick_panel(self.values, self.display_files)

    def display_files(self, index):

        self.selected_value = self.values[index]
        if self.selected_value == '< all >':
            pass  # fix this
        self.menu = NodeBrowserMenu(
            self._UrtextProjectList,
            nodes=self._UrtextProjectList.current_project.keynames[self.selected_tag][self.selected_value]
            )
        show_panel(self.view.window(), self.menu.display_menu,
                   self.open_the_file)

    def open_the_file(self, selected_option): 
        # TODO refactor from below
        if selected_option == -1:
            return
        new_view = self.view.window().open_file(
                self.menu.get_selection_from_index(selected_option).filename)
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
            for value in self._UrtextProjectList.current_project.keynames[self.selected_tag]:
                new_view.run_command("insert_snippet",
                                     {"contents": value + "\n"})
                for node in self._UrtextProjectList.current_project.keynames[self.selected_tag][value]:
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
            for node in self._UrtextProjectList.current_project.keynames[self.selected_tag][
                    self.selected_value]:
                new_view.run_command("insert_snippet",
                                     {"contents": " -> " + node + "\n"})

