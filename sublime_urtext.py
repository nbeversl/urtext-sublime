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
import subprocess
import webbrowser
import Urtext.urtext.syntax as syntax
from Urtext.urtext.project_list import ProjectList
from sublime_plugin import EventListener
from Urtext.urtext.project import match_compact_node
_UrtextProjectList = None

class UrtextTextCommand(sublime_plugin.TextCommand):

    def __init__(self, view):
        self.view = view
        self.window = view.window()

def open_file_to_position(filename, position):

    if sublime.active_window():
        new_view = sublime.active_window().open_file(filename)

        def focus_position(focus_view, position):
            if not focus_view.is_loading():
                if focus_view.window():
                    focus_view.window().focus_view(focus_view)
                    position_node(position, view=focus_view)
            else:
                sublime.set_timeout(lambda: focus_position(focus_view, position), 50) 

        focus_position(new_view, position)

        return new_view

def insert_text(text):
    if sublime.active_window() and sublime.active_window().active_view():
        view = sublime.active_window().active_view()
        view.run_command("insert", {"characters": text})

def save_current():
    if sublime.active_window() and sublime.active_window().active_view():
        view = sublime.active_window().active_view()
        view.run_command('save')

def set_clipboard(text):
    sublime.set_clipboard(text)
    if sublime.active_window() and sublime.active_window().active_view():
        view = sublime.active_window().active_view()
        view.show_popup(text + '\ncopied to the clipboard', 
            max_width=1800, 
            max_height=1000)

def get_buffer(node_id):
    global _UrtextProjectList
    if _UrtextProjectList:
        if node_id in _UrtextProjectList.current_project.nodes:
            filename = _UrtextProjectList.current_project.nodes[node_id].filename
            target_view = None
            for view in sublime.active_window().views():
                if view.file_name() == filename:
                    target_view = view
                    break
            if target_view:
                return target_view.substr(sublime.Region(0, view.size()))

def set_buffer(filename):    
    if sublime.active_window() and sublime.active_window().active_view():
        view = sublime.active_window().active_view()
        return view.substr(sublime.Region(0, view.size()))

def replace(filename='', start=0, end=0, replacement_text=''):
    target_view = None
    for view in sublime.active_window().views():
        if view.file_name() == filename:
            target_view = view
            break
    if target_view:
        target_view.run_command('urtext_replace', {
            'start' : start,
            'end' :end,
            'replacement_text' : replacement_text
            })

def open_external_file(filepath):
    if sublime.platform() == "osx":
        subprocess.Popen(('open', filepath))
    elif sublime.platform() == "windows":
        os.startfile(filepath)
    elif sublime.platform() == "linux":
        subprocess.Popen(('xdg-open', filepath))

def open_file_in_editor(filepath):
    if sublime.active_window():
        sublime.active_window().open_file(filepath)

def open_http_link(link):
    success = webbrowser.get().open(link)
    if not success:
        self.log('Could not open tab using your "web_browser_path" setting')       

def insert_at_next_line(contents):
    pass

def popup(contents):
    pass

editor_methods = {
    'open_file_to_position' : open_file_to_position,
    'error_message' : sublime.error_message,
    'insert_text' : insert_text,
    'save_current' : save_current,
    'set_clipboard' : set_clipboard,
    'open_external_file' : open_external_file,
    'open_file_in_editor' : open_file_in_editor,
    'open_http_link' : open_http_link,
    'get_buffer' : get_buffer,
    'replace' : replace,
    'insert_at_next_line' : insert_at_next_line,
    'popup' : popup,
}

def refresh_project_text_command(change_project=True):
    """ 
    Determine which project we are in based on the Sublime window.
    Used as a decorator in every command class.
    """    
    def middle(function):

        def wrapper(*args, **kwargs):
            
            view = args[0].view
            edit = args[1]

            _UrtextProjectList = initialize_project_list(view)
            if not _UrtextProjectList: return None
            
            if not change_project:
                args[0].edit = edit
                args[0]._UrtextProjectList = _UrtextProjectList
                return function(args[0])
            
            window = sublime.active_window()
            if not window: return print('NO ACTIVE WINDOW')
            
            view = window.active_view()
            window_id = window.id()

            # get the current project first from the view
            if view.file_name():
                _UrtextProjectList.set_current_project(os.path.dirname(view.file_name()))
           
            # then try the window
            for folder in window.folders():
                if _UrtextProjectList.set_current_project(folder): break
            
            # If there is a current project, return it
            if _UrtextProjectList.current_project:
                args[0].edit = edit
                args[0]._UrtextProjectList = _UrtextProjectList
                return function(args[0])

            return None

        return wrapper

    return middle

def refresh_project_event_listener(function):

    def wrapper(*args):
        view = args[1]

        #  only run if Urtext project list is initialized
        if not _UrtextProjectList: return None
        
        window = sublime.active_window()
        if not window: return
        
        view = window.active_view()
        window_id = window.id()

        if view and view.file_name():
            current_path = os.path.dirname(view.file_name())
            _UrtextProjectList.set_current_project(current_path)
            args[0]._UrtextProjectList = _UrtextProjectList
            return function(args[0], view)

        for folder in window.folders():
            if _UrtextProjectList.set_current_project(folder): break

        if _UrtextProjectList.current_project:
            args[0]._UrtextProjectList = _UrtextProjectList
            return function(args[0], view)

        return None

    return wrapper

def initialize_project_list(view, reload_projects=False):

    global _UrtextProjectList

    if reload_projects:
        _UrtextProjectList = None

    folders = view.window().folders()
    if not folders and view.file_name():
        folder = os.path.dirname(view.file_name())
        if _UrtextProjectList:
            _UrtextProjectList.add_project(folder)
        else:
            _UrtextProjectList = ProjectList(
                folder,
                editor_methods=editor_methods)    
    elif folders:
        current_path = folders[0]
        if _UrtextProjectList:
            _UrtextProjectList.add_project(current_path)
        else:
            _UrtextProjectList = ProjectList(
                current_path,
                editor_methods=editor_methods) 
    return _UrtextProjectList


class UrtextReplace(sublime_plugin.TextCommand):

    def run(self, edit, start=0, end=0, replacement_text=''):
        self.view.replace(edit, sublime.Region(start, end), replacement_text)
        
        
class ListProjectsCommand(UrtextTextCommand):
    
    @refresh_project_text_command()
    def run(self):
        show_panel(
            self.view.window(), 
            self._UrtextProjectList.project_titles(), 
            self.set_window_project)

    def set_window_project(self, index):
        title = self._UrtextProjectList.project_titles()[index]
        self._UrtextProjectList.set_current_project(title)        
        self._UrtextProjectList.current_project.open_home()

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
        _UrtextProjectList.nav_reverse()

class UrtextCompletions(EventListener):

    @refresh_project_event_listener
    def on_post_save_async(self, view):
        urtext_on_modified(view)

    def on_query_completions(self, view, prefix, locations):
        
        if _UrtextProjectList and _UrtextProjectList.current_project:
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

                related_nodes =_UrtextProjectList.current_project.extensions['RAKE_KEYWORDS'].get_assoc_nodes(
                    full_line, 
                    view.file_name(), 
                    file_pos)
                if related_nodes:
                    for n in list(set(related_nodes)):
                        subl_completions.append([
                            _UrtextProjectList.current_project.nodes[n].id, 
                            _UrtextProjectList.current_project.nodes[n].id])
                return (subl_completions, 
                    sublime.INHIBIT_WORD_COMPLETIONS,
                    sublime.DYNAMIC_COMPLETIONS
                    )

    def on_hover(self, view, point, hover_zone):
        
        if _UrtextProjectList:
            region = sublime.Region(point, point)
            if view.is_folded(region):
                for r in view.folded_regions():
                    if point in [r.a, r.b]:
                        contents = view.export_to_html(
                            sublime.Region(r.a,r.b))

                def unfold_region(href_region):
                    points = href_region.split('-')
                    region = sublime.Region(int(points[0]), int(points[1]))
                    view.unfold(region)
                    view.hide_popup()

                contents += '<a href="%s-%s">unfold</a>' % (r.a, r.b)

                view.show_popup(contents, 
                    max_width=512, 
                    max_height=512, 
                    location=file_pos,
                    on_navigate=unfold_region)

# TODO update/fix
def urtext_on_modified(view):
    
    if view.file_name() and view.window() and view.window().views():
        other_open_files = [v.file_name() for v in view.window().views() if v.file_name() != view.file_name()]
        if _UrtextProjectList: 
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
        line, cursor = get_line_and_cursor(self.view)
        link = _UrtextProjectList.handle_link(line, self.view.file_name(), col_pos=cursor)
                            
class MouseOpenUrtextLinkCommand(sublime_plugin.TextCommand):

    def run(self, edit, **kwargs):

        if not _UrtextProjectList: return
        click_position = self.view.window_to_text((kwargs['event']['x'],kwargs['event']['y']))
        region = self.view.line(click_position)
        file_pos = region.a
        full_line_region = self.view.full_line(region)
        row, col_pos = self.view.rowcol(click_position)
        full_line = self.view.substr(sublime.Region(full_line_region.a-1, full_line_region.b))

        link = _UrtextProjectList.handle_link(
            full_line,
            self.view.file_name(),
            col_pos=col_pos,
            file_pos=file_pos)

    def want_event(self):
        return True

class NodeBrowserCommand(UrtextTextCommand):
    
    @refresh_project_text_command(change_project=False)
    def run(self):
                
        self.window = self.view.window()
        self.menu = NodeBrowserMenu(
            _UrtextProjectList, 
            project=_UrtextProjectList.current_project)

        self.selection_has_changed = False
        show_panel(
            self.view.window(), 
            self.menu.display_menu, 
            self.open_the_file,
            on_highlight=self.on_highlight)

    def on_highlight(self, index):
        if self.selection_has_changed:
            preview_urtext_node(self.menu.menu[index].id)
        else:
            self.selection_has_changed = True
            #workaround for Sublime text bug

    def open_the_file(self, index):
        node = self.menu.menu[index]
        self._UrtextProjectList.set_current_project(node.project.title())
        self._UrtextProjectList.current_project.open_node(node.id)   

class BacklinksBrowser(NodeBrowserCommand):

    @refresh_project_text_command()
    def run(self):
        backlinks = self._UrtextProjectList.current_project.get_links_to(
            get_node_id(self.view))

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

class WrapSelectionCommand(sublime_plugin.TextCommand):
    @refresh_project_text_command()
    def run(self):
        region = self.view.sel()[0]
        selection = self.view.substr(region)
        self.view.replace(self.edit, region, ''.join(['{ ',selection, ' }']))
        self.view.sel().clear()
        self.view.sel().add(region)

class NodeBrowserMenu:

    def __init__(self, 
        project_list, 
        project=None, 
        nodes=None):

        # rough estimate of character width
        view = sublime.active_window().active_view()
        characters = int(view.viewport_extent()[0] / view.em_width())

        self.menu = []
        self.display_menu = []

        projects = project_list.projects
        if project:
            projects = [project]

        if nodes != None:
            self.menu = [project.nodes[node_id] for node_id in nodes]
        else:
            for single_project in projects:
                self.menu.extend(single_project.nodes.values())

        for node in self.menu:  # there is probably a better way to copy this list.
            timestamp = node.metadata.get_oldest_timestamp()
            if timestamp:
                timestamp = timestamp.wrapped_string
            else:
                timestamp = ''
            self.display_menu.append(
                (node.id[:characters],
                ' - '.join([node.project.title(),timestamp])))

def show_panel(window, menu, main_callback, on_highlight=None):
    """ shows a quick panel with an option to cancel if -1 """
    def on_selected(index):
        if index == -1:
            return
        main_callback(index)
    
    window.show_quick_panel(menu, 
        on_selected, 
        selected_index=-1, # doesn't work; Sublime Text Bug
        on_highlight=on_highlight)

class LinkToNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        self.menu = NodeBrowserMenu(self._UrtextProjectList, project=None)
        show_panel(
            self.view.window(), 
            self.menu.display_menu,
            self.link_to_the_node)

    def link_to_the_node(self, selected_option):
        self._UrtextProjectList.editor_insert_link_to_node(
            self.menu.menu[selected_option],
            project_title=node.project.title()
            )

class CopyLinkToHereCommand(UrtextTextCommand):
    """
    Copy a link to the node containing the cursor to the clipboard.
    Does not include project title.
    """
    @refresh_project_text_command()
    def run(self):

        if not self.window:
            self.window = self.view.window()
        node_id = get_node_id(self.window.active_view())
        self._UrtextProjectList.current_project.editor_copy_link_to_node(node_id)

class CopyLinkToHereWithProjectCommand(CopyLinkToHereCommand):

    def get_link(self, node_id):
        return self._UrtextProjectList.build_contextual_link(
            node_id, 
            include_project=True)

class NewFileNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        path = None
        if self.view and self.view.file_name():
            path = os.path.dirname(self.view.file_name())
        if not path:
            path = self.view.window().folders()[0]
        if not path:
            return
        _UrtextProjectList.set_current_project(path)
        new_node = self._UrtextProjectList.current_project.new_file_node(path=path)
        new_view = self.view.window().open_file(new_node['filename'])

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
        new_node = self._UrtextProjectList.current_project.new_file_node(
            path=os.path.dirname(self.view.file_name()))
        self.view.run_command("insert", {"characters":'| ' + new_node['id'] + ' >'})
        self.view.run_command('save')  # TODO insert notification
        
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
        self._UrtextProjectList.current_project.editor_insert_timestamp()

class GoToDynamicDefinitionCommand(UrtextTextCommand):
    @refresh_project_text_command()
    def run(self):
        target_id = get_node_id(self.view)
        source = _UrtextProjectList.current_project.go_to_dynamic_definition(target_id)

class TagFromOtherNodeCommand(UrtextTextCommand):

    @refresh_project_text_command()
    def run(self):
        # save the current file first
        line, cursor = get_line_and_cursor(self.view)
        _UrtextProjectList.current_project.tag_other_node(
            line,
            cursor,
            #open_files=open_files ?
            )            
        
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
        self._UrtextProjectList.current_project.random_node()

class ToNextNodeCommand(UrtextTextCommand):
    @refresh_project_text_command()
    def run(self):
        next_wrapper = self.view.find(
            syntax.opening_wrapper + '|' + syntax.bullet,
            self.view.sel()[0].a + 1)
        if next_wrapper:
            self.view.sel().clear()
            self.view.sel().add(next_wrapper.a) 
            position_node(next_wrapper.a)

class ToPreviousNodeCommand(UrtextTextCommand):
    @refresh_project_text_command()
    def run(self):
        all_previous_opening_wrappers = [r.a for r in self.view.find_all(
            syntax.opening_wrapper + '|' + syntax.bullet) if r.a < self.view.sel()[0].a]
        if all_previous_opening_wrappers:
            self.view.sel().clear()
            self.view.sel().add(all_previous_opening_wrappers[-1])
            position_node(all_previous_opening_wrappers[-1])

"""
Utility functions
"""

def preview_urtext_node(node_id):
    window = sublime.active_window()
    if window and window.folders() and _UrtextProjectList.set_current_project(window.folders()[0]):
        filename, node_position = _UrtextProjectList.current_project.get_file_and_position(node_id)
        if filename:
            window.open_file(filename, flags=sublime.TRANSIENT)
            preview = window.active_sheet().view()

            def focus_position(focus_view, position):
                if not focus_view.is_loading():
                    if focus_view.window():
                        position_node(position, focus=False, view=focus_view)
                else:
                    sublime.set_timeout(lambda: focus_position(focus_view, position), 50) 
            
            focus_position(preview, node_position)

def position_node(position, focus=True, view=None): 
    if not view:
        window = sublime.active_window()
        if window: view = window.active_view()
    if view:
        if focus:
            view.sel().clear()
            view.sel().add(sublime.Region(position, position))
        r = view.text_to_layout(position)
        view.set_viewport_position(r)
    
def refresh_open_file(changed_files, view):
    window = view.window()
    if changed_files and window:
        open_views = window.views()
        for v in open_views:
            if v.file_name() and v.file_name() in changed_files:
                view.run_command('revert') # undocumented

def get_line_and_cursor(view):
    file_pos = view.sel()[0].a
    col_pos = view.rowcol(file_pos)[1]
    full_line_region = view.line(view.sel()[0])
    full_line = view.substr(full_line_region)
    return full_line, col_pos

def get_node_id(view):
    global _UrtextProjectList
    if view.file_name():
        position = view.sel()[0].a
        filename = view.file_name()
        position = view.sel()[0].a
        return _UrtextProjectList.current_project.get_node_id_from_position(filename, position)
