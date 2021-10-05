from .sublime_urtext import refresh_project_event_listener, refresh_project_text_command, UrtextTextCommand, open_urtext_node, NodeBrowserMenu, show_panel, make_node_menu


class KeywordsCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        window = self.view.window()
        keyphrases = list(self._UrtextProjectList.current_project.extensions['RAKE_KEYWORDS'].get_keywords())
        self.chosen_keyphrase = ''

        def multiple_selections(selection):

            open_urtext_node(self.view, 
                self.second_menu.full_menu[selection].node_id,
                position=self.second_menu.full_menu[selection].position,
                highlight=self.chosen_keyphrase)

        def result(i):
            if i > -1:
                self.chosen_keyphrase = keyphrases[i]
                result = self._UrtextProjectList.current_project.extensions['RAKE_KEYWORDS'].get_by_keyword(self.chosen_keyphrase)
                if len(result) == 1:
                    open_urtext_node(
                        self.view,     
                        result[0],
                        position=self._UrtextProjectList.current_project.nodes[result[0]].position,
                        highlight=self.chosen_keyphrase)
                else:
                    self.second_menu = NodeBrowserMenu(
                        self._UrtextProjectList, 
                        nodes=self._UrtextProjectList.current_project.extensions['RAKE_KEYWORDS'].get_by_keyword(self.chosen_keyphrase))
                    show_panel(
                        window, 
                        self.second_menu.display_menu, 
                        multiple_selections,
                        return_index=True)
        
        window.show_quick_panel(keyphrases, result)

class RakeAssociateCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        window = self.view.window()
        file_pos = self.view.sel()[0].a
        full_line = self.view.substr(self.view.line(self.view.sel()[0]))

        menu = NodeBrowserMenu(
            self._UrtextProjectList,
            nodes=self._UrtextProjectList.current_project.extensions['RAKE_KEYWORDS'].get_assoc_nodes(
                full_line, self.view.file_name(), file_pos)
            )
        
        def open_selection(selection):
            open_urtext_node(self.view, 
                menu.full_menu[selection].node_id)

        show_panel(
            window, 
            menu.display_menu, 
            open_selection,
            return_index=True)
