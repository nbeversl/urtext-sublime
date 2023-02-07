"""
This file is part of Urtext for Sublime Text.

Urtext is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Urtext is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Urtext.  If not, see <https://www.gnu.org/licenses/>.

"""
import sublime
import sublime_plugin
import os
import re
import time
import concurrent.futures
import subprocess
import webbrowser
import Urtext.urtext.syntax as syntax
from Urtext.urtext.project_list import ProjectList
from sublime_plugin import EventListener
from Urtext.urtext.project import match_compact_node

_SublimeUrtextWindows = {}
_UrtextProjectList = None

class UrtextTextCommand(sublime_plugin.TextCommand):

    def __init__(self, view):
        self.view = view
        self.window = view.window()

def refresh_project_text_command(import_project=False, change_project=True):
    """ 
    Determine which project we are in based on the Sublime window.
    Used as a decorator in every command class.
    """    
    def middle(function):

        def wrapper(*args, **kwargs):
            
            view = args[0].view
            edit = args[1]

            _UrtextProjectList = initialize_project_list(view)
            if not _UrtextProjectList:
                return None

            if not change_project:
                args[0].edit = edit
                args[0]._UrtextProjectList = _UrtextProjectList
                return function(args[0])
                
            window = sublime.active_window()
            if not window:
                print('NO ACTIVE WINDOW')
                return

            view = window.active_view()
            window_id = window.id()

            # get the current project first from the view
            if view.file_name():
                current_path = os.path.dirname(view.file_name())
                _UrtextProjectList.set_current_project(current_path)
                if import_project :
                    _UrtextProjectList.import_project(current_path)
            
            # then try the window
            elif window_id in _SublimeUrtextWindows:
                current_path = _SublimeUrtextWindows[window_id]
                _UrtextProjectList.set_current_project(current_path)
                if import_project :
                    _UrtextProjectList.import_project(current_path)

            # otherwise assign the current window to the current project
            elif _UrtextProjectList.current_project:
                _SublimeUrtextWindows[window_id] = _UrtextProjectList.current_project.path
                
            # If there is a current project, return it
            if _UrtextProjectList.current_project:
                args[0].edit = edit
                args[0]._UrtextProjectList = _UrtextProjectList
                return function(args[0])

            elif import_project:
                current_paths = window.folders()
                for path in current_paths:
                    _UrtextProjectList.import_project(path)
            return None

        return wrapper

    return middle

def refresh_project_event_listener(function):

    def wrapper(*args):
        view = args[1]

        #  only run if Urtext project list is initialized
        if not _UrtextProjectList:
            return None
        
        window = sublime.active_window()
        if not window:
            return
        
        view = window.active_view()
        window_id = window.id()

        if view and view.file_name():
            current_path = os.path.dirname(view.file_name())
            _UrtextProjectList.set_current_project(current_path)
            args[0]._UrtextProjectList = _UrtextProjectList
            return function(args[0], view)

        if window_id in _SublimeUrtextWindows:
            current_path = _SublimeUrtextWindows[window_id]
            _UrtextProjectList.set_current_project(current_path)
            args[0]._UrtextProjectList = _UrtextProjectList
            return function(args[0], view)

        if _UrtextProjectList.current_project:
            _SublimeUrtextWindows[window_id] = _UrtextProjectList.current_project.path
            args[0]._UrtextProjectList = _UrtextProjectList
            return function(args[0], view)

        return None

    return wrapper

def initialize_project_list(view, reload_projects=False):

    global _UrtextProjectList

    if reload_projects:
        _UrtextProjectList = None

    folders = view.window().folders()          
    urtext_settings_file = None
    urtext_settings_obj = sublime.load_settings("Urtext.sublime-settings")
    if urtext_settings_obj.has("urtext_settings_file") and urtext_settings_obj.get("urtext_settings_file"):
        urtext_settings_file = urtext_settings_obj.get("urtext_settings_file")

    if urtext_settings_file:
        _UrtextProjectList = ProjectList(urtext_settings_file)

    elif not folders and view.file_name():
        folder = os.path.dirname(view.file_name())
        if _UrtextProjectList:
            _UrtextProjectList.add_project(folder)
        else:
            _UrtextProjectList = ProjectList({ 'project_paths' : [folder] })    
    elif folders:
        current_path = folders[0]
        if _UrtextProjectList:
            _UrtextProjectList.add_project({'path': current_path})
        else:
            _UrtextProjectList = ProjectList({ 'project_paths' : [current_path] }) 
    return _UrtextProjectList

def get_path(view):
    """ 
    given a view or None, establishes the current active path,
    either from the view or from the current active window.
    """
    current_path = None
    if view and view.file_name():
        return os.path.dirname(view.file_name())
    window = sublime.active_window()
    if not window:
        print('No active window')
        return None
    window_variables = window.extract_variables()
    if 'folder' in window_variables:
        return window.extract_variables()['folder']
    return None

class ListProjectsCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        show_panel(
            self.view.window(), 
            self._UrtextProjectList.project_titles(), 
            self.set_window_project)

    def set_window_project(self, title):
        self._UrtextProjectList.set_current_project(title)
        _SublimeUrtextWindows[self.view.window().id()] = self._UrtextProjectList.current_project.path
        node_id = self._UrtextProjectList.nav_current()
        self._UrtextProjectList.nav_new(node_id)
        open_urtext_node(self.view, node_id)

class MoveFileToAnotherProjectCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        window = self.view.window()
        show_panel(
            window,
            self._UrtextProjectList.project_titles(), 
            self.move_file)

    def move_file(self, new_project_title):
                
        self._UrtextProjectList.move_file(
            self.view.file_name(), 
            new_project_title)

        self.view.window().run_command('close_file')

        last_node = _UrtextProjectList.nav_reverse()
        if last_node:
            open_urtext_node(self.view, last_node)

class UrtextCompletions(EventListener):

    @refresh_project_event_listener
    def on_post_save_async(self, view):
        urtext_on_modified(view)

    def on_query_completions(self, view, prefix, locations):
        
        if not _UrtextProjectList or not _UrtextProjectList.current_project:
            return

        current_path = os.path.dirname(view.file_name())
        if _UrtextProjectList.get_project(current_path):
            subl_completions = []
            proj_completions = _UrtextProjectList.get_all_meta_pairs()
            for c in proj_completions:
                t = c.split('::')
                if len(t) > 1:
                    subl_completions.append([t[1]+'\t'+c, c])
            for t in _UrtextProjectList.current_project.title_completions():
                subl_completions.append([t[0],t[1]])

            file_pos = view.sel()[0].a
            full_line = view.substr(view.line(view.sel()[0]))

            related_nodes=_UrtextProjectList.current_project.extensions['RAKE_KEYWORDS'].get_assoc_nodes(
                    full_line, 
                    view.file_name(), 
                    file_pos)
            for n in list(set(related_nodes)):
                subl_completions.append([
                    _UrtextProjectList.current_project.nodes[n].get_title(), 
                    _UrtextProjectList.current_project.nodes[n].get_title()])

            completions = (subl_completions, sublime.INHIBIT_WORD_COMPLETIONS)

            return completions
        return []

    def on_hover(self, view, point, hover_zone):
        
        if _UrtextProjectList:

            #TODO refactor
            region = view.line(point)
            file_pos = region.a
            full_line_region = view.full_line(region)
            full_line = view.substr(full_line_region) 
            link = _UrtextProjectList.get_link_and_set_project(full_line, view.file_name())
            if link and 'node_id' in link:

                contents = _UrtextProjectList.current_project.get_node_contents(link['node_id'])
                if contents:

                    contents = contents.replace('<','&lt;')
                    contents = contents.replace('>','&gt;')
                    contents = contents.replace('\n','<br>')

                    

                    html = """
                        <body id=linked_node_contents>
                            <style>
                                h1 {
                                    font-size: 1.1rem;
                                    font-weight: 500;
                                    margin: 0 0 0.5em 0;
                                    font-family: system;
                                }
                                p {
                                    margin-top: 0;
                                }
                                a {
                                    font-weight: normal;
                                    font-style: italic;
                                    padding-left: 1em;
                                    font-size: 1.0rem;
                                }
                                span.nums {
                                    display: inline-block;
                                    text-align: right;
                                    color: color(var(--foreground) a(0.8))
                                }
                                span.context {
                                    padding-left: 0.5em;
                                }
                            </style>
                            <p>%s</p>
                            <a href="%s">open</a>
                        </body>
                    """ % (contents, link['node_id'])
                    view.show_popup(html,
                        max_width=800, 
                        max_height=512, 
                        location=file_pos,
                        on_navigate=open_node_from_this_view)
                    return

            region = sublime.Region(point, point)
            if view.is_folded(region):
                for r in view.folded_regions():
                    if point in [r.a, r.b]:
                        contents = (view.substr(r))

                def unfold_region(href_region):
                    points = href_region.split('-')
                    region = sublime.Region(int(points[0]), int(points[1]))
                    view.unfold(region)
                    view.hide_popup()

                html = """
                    <body id=show-scope>
                        <style>
                            h1 {
                                font-size: 1.1rem;
                                font-weight: 500;
                                margin: 0 0 0.5em 0;
                                font-family: system;
                            }
                            p {
                                margin-top: 0;
                            }
                            a {
                                font-weight: normal;
                                font-style: italic;
                                padding-left: 1em;
                                font-size: 1.0rem;
                            }
                            span.nums {
                                display: inline-block;
                                text-align: right;
                                color: color(var(--foreground) a(0.8))
                            }
                            span.context {
                                padding-left: 0.5em;
                            }
                        </style>
                        <p>%s</p>
                        <a href="%s-%s">unfold</a>
                    </body>
                """ % (contents, r.a, r.b)

                view.show_popup(html, 
                    max_width=512, 
                    max_height=512, 
                    on_navigate=unfold_region)

def urtext_on_modified(view):
    
    if view.file_name() and view.window() and view.window().views():
        other_open_files = [v.file_name() for v in view.window().views() if v.file_name() != view.file_name()]
        modified_file = _UrtextProjectList.on_modified(view.file_name())
        for f in other_open_files:
            _UrtextProjectList.visit_file(f)
        if modified_file:
                for f in modified_file:
                   if _UrtextProjectList.current_project.is_async:
                        f = f.result()



class OpenUrtextLinkCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):     
        link = get_urtext_link(self.view)

        if link == None:   
            if not _UrtextProjectList.current_project.compiled:
                   sublime.error_message("Project is still compiling")
            else:
                print('NO LINK') 
            return
        
        if link['kind'] == 'SYSTEM':
            open_external_file(link['link'])

        if link['kind'] == 'EDITOR_LINK':
            file_view = self.view.window().open_file(link['link'])

        if link['kind'] in ['NODE','OTHER_PROJECT']:
            _UrtextProjectList.nav_new(link['link'])   
            open_urtext_node(self.view, link['link'], position=link['dest_position'])
        
        if link['kind'] == 'HTTP':
            success = webbrowser.get().open(link['link'])
            if not success:
                self.log('Could not open tab using your "web_browser_path" setting')       

class MouseOpenUrtextLinkCommand(sublime_plugin.TextCommand):

    def run(self, edit, **kwargs):
        if not _UrtextProjectList:
            return
        click_position = self.view.window_to_text((kwargs['event']['x'],kwargs['event']['y']))
        region = self.view.line(click_position)
        file_pos = region.a
        full_line_region = self.view.full_line(region)
        row, col_pos = self.view.rowcol(click_position)
        contents = self.view.substr(sublime.Region(full_line_region.a -1, full_line_region.b))

        link = _UrtextProjectList.get_link_and_set_project(
            contents, 
            self.view.file_name(), 
            col_pos=col_pos,
            file_pos=file_pos)

        if link == None:   
            if not _UrtextProjectList.current_project.compiled:
                return sublime.error_message("Project is still compiling")
            else:
                return print('NO LINK') 
            return

        if link['kind'] == 'EDITOR_LINK':
            file_view = self.view.window().open_file(link['link'])
        if link['kind'] in ['NODE','OTHER_PROJECT']:
            _UrtextProjectList.nav_new(link['link'])   
            open_urtext_node(self.view, link['link'], position=link['dest_position'])
        if link['kind'] == 'HTTP':
            success = webbrowser.get().open(link['link'])
            if not success:
                self.log('Could not open tab using your "web_browser_path" setting')       
        if link['kind'] == 'SYSTEM':
            open_external_file(link['link'])

    def want_event(self):
        return True

class NodeBrowserCommand(UrtextTextCommand):
    
    @refresh_project_text_command(change_project=False)
    def run(self):
        
        #rough estimate of how many characters wide the viewport is
        characters_wide = int(self.view.viewport_extent()[0] / self.view.em_width())

        self.menu = NodeBrowserMenu(
            _UrtextProjectList, 
            project=_UrtextProjectList.current_project,
            characters=characters_wide)
        show_panel(
            self.view.window(), 
            self.menu.display_menu, 
            self.open_the_file)

    def open_the_file(self, selected_option):        
        selected_item = self.menu.get_selection_from_index(selected_option)
        self._UrtextProjectList.set_current_project(selected_item.project_title)
        self._UrtextProjectList.nav_new(selected_item.node_id)   
        open_urtext_node(self.view, selected_item.node_id)

class BacklinksBrowser(NodeBrowserCommand):

    @refresh_project_text_command()
    def run(self):
        backlinks = self._UrtextProjectList.current_project.get_links_to(get_node_id(self.view))

        if backlinks:
            self.menu = NodeBrowserMenu(
                self._UrtextProjectList, 
                project=self._UrtextProjectList.current_project,
                nodes=backlinks)

            show_panel(
                self.view.window(), 
                self.menu.display_menu, 
                self.open_the_file)

class ForwardlinksBrowser(NodeBrowserCommand):

    @refresh_project_text_command()
    def run(self):
        forward_links = self._UrtextProjectList.current_project.get_links_from(get_node_id(self.view))
        self.menu = NodeBrowserMenu(
            self._UrtextProjectList, 
            project=self._UrtextProjectList.current_project,
            nodes=forward_links,
            )
        show_panel(
            self.view.window(), 
            self.menu.display_menu, 
            self.open_the_file)

class AllProjectsNodeBrowser(NodeBrowserCommand):
    
    @refresh_project_text_command()
    def run(self):
        self.menu = NodeBrowserMenu(
            self._UrtextProjectList, 
            project=None
            )
        show_panel(
            self.view.window(), 
            self.menu.display_menu, 
            self.open_the_file)

class FindByMetaCommand(sublime_plugin.TextCommand):

    @refresh_project_text_command()
    def run(self):
        self.tagnames = _UrtextProjectList.current_project.get_all_keys()
        self.view.window().show_quick_panel(self.tagnames, self.list_values)

    def list_values(self, index):
        self.selected_tag = self.tagnames[index]
        self.values =  _UrtextProjectList.current_project.get_all_values_for_key(self.selected_tag)        
        self.values.insert(0, '< all >')
        self.view.window().show_quick_panel(self.values, self.display_files)

    def display_files(self, index):

        self.selected_value = self.values[index]
        if self.selected_value == '< all >':
            pass  # fix this
        self.menu = NodeBrowserMenu(
            self._UrtextProjectList,
            nodes = _UrtextProjectList.current_project.get_by_meta(self.selected_tag, self.selected_value, '='))
        show_panel(self.view.window(), self.menu.display_menu,
                   self.open_the_file)

    def open_the_file(self, selected_option): 
        # TODO refactor from below
        if selected_option == -1:
            return
        path = get_path(self.view)
        new_view = self.view.window().open_file(
            os.path.join(
                path,
                self.menu.get_selection_from_index(selected_option).filename))
        if len(selected_option) > 3 and selected_option[3] != None:
            self.locate_node(selected_option[3], new_view)

class WrapSelectionCommand(sublime_plugin.TextCommand):
    @refresh_project_text_command()
    def run(self):
        region = self.view.sel()[0]
        selection = self.view.substr(region)
        self.view.replace(self.edit, region, ''.join(['{ ',selection, ' }']))
        self.view.sel().clear()
        self.view.sel().add(region)

class NodeBrowserMenu:
    """ custom class to store more information on menu items than is displayed """

    def __init__(self, 
        project_list, 
        project=None, 
        nodes=None,
        characters=255):

        menu = []

        projects = project_list.projects
        if project:
            projects = [project]

        if nodes != None:
            for node_id in nodes:
                menu.append(
                      NodeInfo(
                        node_id,
                        project_list))
        else:
            for single_project in projects:
                for node_id in single_project.all_nodes():
                    menu.append(
                        NodeInfo(
                            node_id, 
                            project_list, 
                            project=single_project))
        self.menu = menu
        self.display_menu = []
        for item in menu:  # there is probably a better way to copy this list.
            display_meta = item.display_meta
            if display_meta:
                display_meta = ' - ' + str(display_meta)
            new_item = [
                item.title[:characters],
                item.project_title + display_meta,            
            ]
            self.display_menu.append(new_item)

    def get_selection_from_index(self, selected_option):
        index = self.display_menu.index(selected_option)
        return self.menu[index]

class NodeInfo():

    def __init__(self, node_id, project_list, project=None):    
        if not project:
            project = project_list.current_project
        self.title = node_id
        if self.title.strip() == '':
            self.title = '(no title)'
        self.date = project.nodes[node_id].date
        self.filename = project.nodes[node_id].filename
        self.node_id = node_id
        self.project_title = project.title
        self.display_meta = project.nodes[node_id].display_meta

def show_panel(window, menu, main_callback, return_index=False):
    """ shows a quick panel with an option to cancel if -1 """
    def private_callback(index):
        if index == -1:
            return
        # otherwise return the main callback with the index of the selected item
        if return_index:
            return main_callback(index)
        
        main_callback(menu[index])
    window.show_quick_panel(menu, private_callback)

class LinkToNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.menu = NodeBrowserMenu(self._UrtextProjectList, project=None)
        show_panel(self.view.window(), self.menu.display_menu, self.link_to_the_node)

    def link_to_the_node(self, selected_option):
        selected_option = self.menu.get_selection_from_index(selected_option)
        link = self._UrtextProjectList.build_contextual_link(
            selected_option.node_id,
            project_title=selected_option.project_title)    
        self.view.run_command("insert", {"characters": link})

class CopyLinkToHereCommand(UrtextTextCommand):
    """
    Copy a link to the node containing the cursor to the clipboard.
    Does not include project title.
    """
    @refresh_project_text_command()
    def run(self):

        if not self.window:
            self.window = self.view.window()

        link = self.get_link(get_node_id(
            self.window.active_view(), use_buffer=True))
        if link:
            sublime.set_clipboard(link)
            self.view.show_popup(link + '\ncopied to the clipboard', 
                max_width=1800, 
                max_height=1000 
                    # max_height does not work correctly. 
                    # workaround for now using max_width
                    # FUTURE: Could also hard wrap.
                    # https://github.com/sublimehq/sublime_text/issues/2854
                    # https://github.com/SublimeLinter/SublimeLinter/pull/1609
                    # https://github.com/SublimeLinter/SublimeLinter/issues/1601
                )

    def get_link(self, node_id):
        return self._UrtextProjectList.build_contextual_link(node_id)       

class CopyLinkToHereWithProjectCommand(CopyLinkToHereCommand):
    """
    Copy a link to the node containing the cursor to the clipboard.
    Does not include project title.
    """
    def get_link(self, node_id):
        return self._UrtextProjectList.build_contextual_link(
            node_id, 
            include_project=True)

class NewFileNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        path = self._UrtextProjectList.current_project.path
        new_node = self._UrtextProjectList.current_project.new_file_node()
        new_view = self.view.window().open_file(os.path.join(path, new_node['filename']))

        def set_cursor(new_view):
            if not new_view.is_loading():
                new_view.sel().clear()
                new_view.sel().add(sublime.Region(int(new_node['cursor_pos']),int(new_node['cursor_pos'])))
            else:
                sublime.set_timeout(lambda: set_cursor(new_view), 50) 

        set_cursor(new_view)

class InsertLinkToNewNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        path = self._UrtextProjectList.current_project.path
        new_node = self._UrtextProjectList.current_project.new_file_node()
        self.view.run_command("insert", {"characters":'>' + new_node['id']})

class DeleteThisNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if self.view.file_name():
            open_files = [f.file_name() for f in self.view.window().views() if f.file_name() != self.view.file_name()]
            file_name = self.view.file_name()
            if self.view.is_dirty():
                self.view.set_scratch(True)
            self.view.window().run_command('close_file')            
            self._UrtextProjectList.delete_file(file_name, open_files=open_files)

class InsertTimestampCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        datestamp = self._UrtextProjectList.current_project.timestamp(as_string=True)
        for s in self.view.sel():
            if s.empty():
                self.view.insert(self.edit, s.a, datestamp)
            else:
                self.view.replace(self.edit, s, datestamp)

class ConsolidateMetadataCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.view.run_command('save')  # TODO insert notification
        node_id = get_node_id(self.view)
        if node_id:
            self._UrtextProjectList.current_project.consolidate_metadata(node_id, one_line=True)
            return True    
        print('No Urtext node or no Urtext node with ID found here.')
        return False

class GoToDynamicDefinitionCommand(UrtextTextCommand):
    @refresh_project_text_command()
    def run(self):
        target_id = get_node_id(self.view)
        source = _UrtextProjectList.current_project.get_dynamic_definition(target_id)
        if source:
            open_urtext_node(self.view, source['id'], position = source['location'])
             
class TagFromOtherNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        # save the current file first
        full_line = self.view.substr(self.view.line(self.view.sel()[0]))
        link = _UrtextProjectList.get_link_and_set_project(
            full_line,
            self.view.file_name())
        if link['kind'] != 'NODE':
            return
        node_id = link['link']
        open_files = [f.file_name() for f in self.view.window().views()]
        _UrtextProjectList.current_project.tag_other_node(node_id, open_files=open_files)
        
class ReIndexFilesCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):

        renamed_files = self._UrtextProjectList.current_project.run_action(
            "REINDEX",
            self.view.substr(self.view.line(self.view.sel()[0])),
            self.view.file_name()
            )
        if self._UrtextProjectList.current_project.is_async:
            renamed_files=renamed_files.result()
        if renamed_files:
            for view in self.view.window().views():
                if view.file_name() == None:
                    continue
                if view.file_name() in renamed_files:               
                    view.retarget(renamed_files[view.file_name()])

class RenameFileCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.view.run_command('save')
        urtext_on_modified(self.view)
        filename = self.view.file_name()
        renamed_files = self._UrtextProjectList.current_project.run_action(
            "RENAME_SINGLE_FILE",
            self.view.substr(self.view.line(self.view.sel()[0])),
            filename=filename
            )

        if self._UrtextProjectList.current_project.is_async:
            renamed_files=renamed_files.result()

        if renamed_files:
            self.view.retarget(renamed_files[filename])

class UrtextReloadProjectCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        if initialize_project_list(self.view, reload_projects=True) == None:
            print('No Urtext Project')
            return None

class ConvertToNoNodeIdsCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self._UrtextProjectList.current_project.convert_project_to_no_node_ids()

class CompactNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        region = self.view.sel()[0]
        line_region = self.view.line(region) # full line region
        line_contents = self.view.substr(line_region)

        if match_compact_node(line_contents):
            replace = False
            contents = self._UrtextProjectList.current_project.add_compact_node()
        else:
            replace = True
            contents = self._UrtextProjectList.current_project.add_compact_node(contents=line_contents)
        if replace:
            region = self.view.sel()[0]
            self.view.erase(self.edit, line_region)
            self.view.run_command("insert_snippet",{"contents": contents})
            self.view.sel().clear()
            cursor_offset = len(line_contents) - len(line_contents.strip())
            self.view.sel().add(sublime.Region(region.a + 2 - cursor_offset, region.a  +2 - cursor_offset))
        else:
            next_line_down = line_region.b + 1
            self.view.sel().clear()
            self.view.sel().add(next_line_down) 
            self.view.run_command("insert_snippet",{"contents": '\n'+contents})            
            new_cursor_position = sublime.Region(next_line_down+4, next_line_down+4) 
            self.view.sel().clear()
            self.view.sel().add(new_cursor_position) 

class PopNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.view.run_command('save')
        urtext_on_modified(self.view)
        file_pos = self.view.sel()[0].a + 1
        r = self._UrtextProjectList.current_project.run_action(
            'POP_NODE',
            self.view.substr(self.view.line(self.view.sel()[0])),
            self.view.file_name(),
            file_pos = file_pos,
            col_pos = self.view.rowcol(file_pos)[1]
            )

class PullNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.view.run_command('save')  # TODO insert notification
        urtext_on_modified(self.view)
        if self.view.file_name():
            file_pos = self.view.sel()[0].a
            file_to_close = self._UrtextProjectList.current_project.run_action(
                'PULL_NODE',
                self.view.substr(self.view.line(self.view.sel()[0])),
                self.view.file_name(),
                file_pos = file_pos,
                col_pos = self.view.rowcol(file_pos)[1]
                )
            if file_to_close:
                if self._UrtextProjectList.current_project.is_async:
                    file_to_close=file_to_close.result()
                for view in self.window.views():
                    if view.file_name() == file_to_close:
                        view.set_scratch(True)
                        view.close()
                        return

class RandomNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        node_id = self._UrtextProjectList.current_project.random_node()
        self._UrtextProjectList.nav_new(node_id)
        open_urtext_node(self.view, node_id)


class ToNextNodeCommand(UrtextTextCommand):
    @refresh_project_text_command()
    def run(self):
        next_wrapper = self.view.find(
            syntax.opening_wrapper + '|' + syntax.bullet,
            self.view.sel()[0].a + 1)
        if next_wrapper:
            self.view.sel().clear()
            self.view.sel().add(next_wrapper.a) 
            position_node(self.view, next_wrapper.a)

class ToPreviousNodeCommand(UrtextTextCommand):
    @refresh_project_text_command()
    def run(self):
        all_previous_opening_wrappers = [r.a for r in self.view.find_all(
            syntax.opening_wrapper + '|' + syntax.bullet) if r.a < self.view.sel()[0].a]
        if all_previous_opening_wrappers:
            self.view.sel().clear()
            self.view.sel().add(all_previous_opening_wrappers[-1])
            position_node(self.view, all_previous_opening_wrappers[-1])



"""
Utility functions
"""
def open_urtext_node(
    view, 
    node_id, 
    project=None, 
    position=0,
    highlight=''):
   
    if project and _UrtextProjectList: 
        _UrtextProjectList.set_current_project(project.path)
    filename, node_position = _UrtextProjectList.current_project.get_file_and_position(node_id)
    if filename and view.window():

        _UrtextProjectList.visit_file(filename)
    
        file_view = view.window().open_file(filename)

        if not position:
            position = node_position
        position = int(position)

        def focus_position(focus_view, position):
            if not focus_view.is_loading():
                if view.window():
                    view.window().focus_view(focus_view)
                    position_node(focus_view, position)
            else:
                sublime.set_timeout(lambda: focus_position(focus_view, position), 50) 
                
        focus_position(file_view, position)

        return file_view
 
    return None
    """
    Note we do not involve this function with navigation, since it is
    called from forward/backward navigation and shouldn't duplicate/override 
    any of the operations of the methods that call it.
    """

def open_node_from_this_view(node_id):
    open_urtext_node(view, node_id)

def position_node(new_view, position): 
    new_view.sel().clear()
    new_view.sel().add(sublime.Region(position, position))
    r = new_view.text_to_layout(position)
    new_view.set_viewport_position(r)
    
def refresh_open_file(changed_files, view):
    window = view.window()
    if changed_files and window:
        open_views = window.views()
        for v in open_views:
            if v.file_name() and v.file_name() in changed_files:
                view.run_command('revert') # undocumented

def get_urtext_link(view):
    file_pos = view.sel()[0].a
    col_pos = view.rowcol(file_pos)[1]
    full_line_region = view.line(view.sel()[0])
    full_line = view.substr(full_line_region)
    
    return _UrtextProjectList.get_link_and_set_project(
        full_line, 
        view.file_name(), 
        col_pos=col_pos,
        file_pos=file_pos)

def open_external_file(filepath):

    if sublime.platform() == "osx":
        subprocess.Popen(('open', filepath))
    elif sublime.platform() == "windows":
        os.startfile(filepath)
    elif sublime.platform() == "linux":
        subprocess.Popen(('xdg-open', filepath))

def get_node_id(view, use_buffer=False):
    global _UrtextProjectList
    if view.file_name():
        position = view.sel()[0].a
        if use_buffer:            
            return _UrtextProjectList.current_project.get_node_id_from_position_in_buffer(
                view.substr(sublime.Region(0,view.size())), 
                position)
        filename = view.file_name()
        position = view.sel()[0].a
        return _UrtextProjectList.current_project.get_node_id_from_position(filename,position)
