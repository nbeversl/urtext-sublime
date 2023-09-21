# -*- coding: utf-8 -*-
"""
This file is part of Urtext.

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
import os
import re

if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    from .project import UrtextProject
    import Urtext.urtext.syntax as syntax
else:
    from urtext.project import UrtextProject
    import urtext.syntax as syntax

project_link_r = re.compile(r'(=>\"(.*?)\")?.*?(\|.+>([0-9,a-z,A-Z,\s]+)\b)?')

class ProjectList():

    def __init__(self, 
        entry_point,
        editor_methods=None):
   
        if editor_methods == None:
            editor_methods = {} 
        self.entry_point = entry_point
        self.projects = []
        self.extensions = {}
        self.current_project = None
        self.editor_methods = editor_methods
        self.add_project(entry_point)

    def add_project(self, path):
        """ recursively add folders """
        paths = []
        for p in self.projects:
            paths.extend([entry['path'] for entry in p.settings['paths']])
        if path not in paths:
            if os.path.basename(path) not in ['urtext_files']:
                project = UrtextProject(path, 
                    project_list=self,
                    editor_methods=self.editor_methods)
                self.projects.append(project)

    def handle_link(self, 
            string, 
            filename, 
            col_pos=0,
            file_pos=0,
            return_target_only=False):

        """
        Given a line of text, looks for a link to a node or project
        with node, sets the current project to the containing project,
        and returns the link information. Does not update navigation,
        this should be done by the calling method.
        """
        node_id = None
        link = project_link_r.search(string)
        project_name = link.group(2)
        node_id = link.group(4)

        """ If a project name has been specified, locate the project and node """
        if project_name:
            if not self.set_current_project(project_name): return None
            return self.current_project.handle_link(
                string, 
                col_pos=col_pos,
                file_pos=file_pos,
                return_target_only=return_target_only)
         
        """ Otherwise, set the project, search the link for a link in the current project """
        if filename:
            self.set_current_project(os.path.dirname(filename))
            if self.current_project:
                return self.current_project.handle_link( 
                    string,
                    col_pos=col_pos,
                    file_pos=file_pos,
                    return_target_only=return_target_only)

    def on_modified(self, filename):
        project = self._get_project_from_path(
            os.path.dirname(filename))
        if project:
            future = project.on_modified(filename)
            return future

    def _get_project_from_path(self, path):
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        for project in self.projects:
            if path in [entry['path'] for entry in project.settings['paths']]:
                return project
        return None

    def _get_project_from_title(self, title):
        for project in self.projects:
            if title == project.settings['project_title']:
                return project
        return None

    def get_project(self, title_or_path):
        project = self._get_project_from_title(title_or_path) 
        if not project:
            project = self._get_project_from_path(title_or_path) 
        return project

    def set_current_project(self, title_or_path):
        project = self.get_project(title_or_path) 
        if not project:
            return
        if ( not self.current_project ) or ( 
            project.settings['project_title'] != self.current_project.settings['project_title'] ) :
           self.current_project = project
           print('Switched to project: ' + self.current_project.settings['project_title'])
        return project

    def build_contextual_link(self, 
        node_id,
        project_title=None, 
        pointer=False,
        include_project=False):

        if node_id:
            if project_title == None:
                project = self.current_project
            else:
                project = self.get_project(project_title)
            link = ''.join([
                syntax.link_opening_wrapper,
                node_id,
                syntax.link_closing_wrapper])
            if pointer:
                link = link.replace(
                    syntax.link_closing_wrapper, 
                    syntax.pointer_closing_wrapper)
            if include_project or project != self.current_project:
                link = ''.join([
                    syntax.other_project_link_prefix,
                    '"',
                    project.settings['project_title'],
                    '"',
                    link])
            return link
        
    def project_titles(self):
        titles = []
        for project in self.projects:
            titles.append(project.settings['project_title'])
        return titles

    def get_current_project(self, path):
        for project in self.projects:
            if project.path in project.settings['paths']:
                return project
        return None

    def visit_file(self, filename):
        self.set_current_project(filename)
        return self.current_project.visit_file(filename)

    def visit_node(self, filename, node_id):
        self.set_current_project(filename)
        return self.current_project.visit_node(node_id)

    def new_project_in_path(self, path):
        if os.path.exists(path):
            new_project = UrtextProject(path, project_list=self)
            self.set_current_project(path)
        else:
            print('%s does not exist' % path) 

    def move_file(self, 
        filename, 
        destination_project_name_or_path,
        replace_links=True):

        """
        Move a file from one project to another, checking for
        node ID duplication in the new project location, and 
        optionally replacing links to every affected node.
        """
        destination_project = self.get_project(
            destination_project_name_or_path)

        if not destination_project:
            print('Destination project `'+ destination_project_name_or_path +'` was not found.')
            return None

        if filename not in self.current_project.files:
            print('File '+ filename +' not included in the current project.')
            return None

        affected_nodes = list(self.current_project.files[filename].nodes)        
        self.current_project.drop_file(filename)
        os.rename(
            filename,
            os.path.join(
                destination_project.settings['paths'][0]['path'],
                os.path.basename(filename))
            )
        """
        add_file() will raise an exception if the file makes
        duplicate nodes in the destination project
        """
        try:
            destination_project.add_file(filename)    
        except:
            #TODO handle
            return None
 
        if replace_links:
            for node in affected_nodes:
                self.replace_links(
                    self.current_project.settings['project_title'],
                    destination_project.settings['project_title'],                   
                    node.id)

        return True

    def get_all_meta_pairs(self):
        meta_values = []
        for project in self.projects:
            meta_pairs = project.get_all_meta_pairs()
            for pair in meta_pairs:
                if pair not in meta_values:
                    meta_values.append(pair)
        return meta_values

    def replace_links(self, old_project_path_or_title, new_project_path_or_title, node_id):
        old_project = self.get_project(old_project_path_or_title)
        new_project = self.get_project(new_project_path_or_title)
        old_project.replace_links(node_id, new_project=new_project.settings['project_title'])
    
    def titles(self):
        title_list = {}
        for project in self.projects:
            for node_id in project.nodes:
                title_list[project.nodes[node_id].title] = (project.settings['project_title'], node_id)
        return title_list

    def is_in_export(self, filename, position):
        if not self.current_project:
            return None
        return self.current_project.is_in_export(filename, position)

    def editor_insert_link_to_node(self, node, project_title=None):
        if project_title == None:
            project_title = self.current_project.title
        if project_title:
            link = self.build_contextual_link(
                node.id,
                project_title=project_title)
            self.current_project.run_editor_method('insert_text', link)

    def delete_file(self, file_name, project=None, open_files=[]):
        if not project:
            project = self.current_project
        project.delete_file(
            file_name, 
            open_files=open_files)
