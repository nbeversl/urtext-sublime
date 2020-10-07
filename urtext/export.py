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
from .node import UrtextNode

node_link_regex = r'[^>]>[0-9,a-z]{3}\b'
OPENING_BRACKETS = '<span class="urtext-open-brackets">&#123</span>'
node_pointer_regex = r'>>[0-9,a-z]{3}\b'
titled_link_regex = r'\|.*?[^>]>[0-9,a-z]{3}\b'
titled_node_pointer_regex =r'\|.*?>>[0-9,a-z]{3}\b'
file_link_regex = re.compile('f>.*')

class UrtextExport:

    def __init__(self, project):
        self.project = project
        self.extensions  = {
            '-plaintext':'.txt',
            '-html' : '.html',
            '-markdown' :'.md',
            '-md' :'.md'
        }
   
    def export_from(self, 
        root_node_id, 
        as_single_file=False,
        strip_urtext_syntax=True,
        style_titles=True,
        exclude=None, 
        clean_whitespace=None,
        kind='plaintext',
        preformat=False,
        ):
 
        if exclude == None:
            exclude = []

        visited_nodes = []
        points = {}

        """
        Bootstrap _add_node_content() with a root node ID and then 
        return contents, recursively if specified.
        """
        # if kind in ['-markdown', '-md']:
        #     clean_whitespace = True
        
        exported_content, points, visited_nodes = self._add_node_content(
            root_node_id,
            as_single_file=as_single_file,
            strip_urtext_syntax=strip_urtext_syntax,
            style_titles=style_titles,
            exclude=exclude,
            kind=kind,
            clean_whitespace=clean_whitespace,
            visited_nodes=visited_nodes, # why won't this get set as default?
            preformat=preformat,
            points=points,
            )
        exported_content = preformat_embedded_syntaxes(exported_content)
        return exported_content, points

    def _add_node_content(self, 
            root_node_id,                               # node to start from
            added_contents = None,
            as_single_file=False,                       # Recursively add contents from node pointers?
            strip_urtext_syntax=True,                   # for HTML, strip Urtext syntax?
            style_titles=True,                          # style titles ????
            exclude=None,                                 # specify any nodes to exclude
            kind='-plaintext',                           # format
            nested=None,
            points = None,                               
            single_node_only=False,                      # stop at this node, no inline nodes
            clean_whitespace=False,
            visited_nodes=None,
            preformat=False,
            ):     
       
        if exclude == None:
            exclude = []
        
        if not root_node_id:
            self.project._log_item('Root node ID is None')
            return
            
        if root_node_id not in self.project.nodes:
            self.project._log_item('EXPORT: Root node ID ' + root_node_id +' not in the project.')
            return '','',''    

        """
        Recursively add nodes, its inline nodes and node pointers, in order
        from a given starting node, keeping track of nesting level, and wrapping in markup.        
        """    
       
        """
        Get and set up initial values
        """
        if points == None:
            points = {}
        if added_contents == None:
            added_contents = ''
        if visited_nodes == None:
            visited_nodes = []
        if exclude == None:
            exclude = []
        if nested == None:
            nested = 1

        ranges = self.project.nodes[root_node_id].ranges
        filename = self.project.nodes[root_node_id].filename
        file_contents = self.project._full_file_contents(filename)        
        title = self.project.nodes[root_node_id].title
        meta_title = True if self.project.nodes[root_node_id].metadata.get_first_value('title') else False
        title_found = False

        if root_node_id in exclude or root_node_id in visited_nodes:
            return added_contents, points, visited_nodes
        
        visited_nodes.append(root_node_id)
        
        """ get all the node pointers and their locations"""
        locations = []
        for single_range in ranges:
            locations.extend(self.get_node_pointers_with_locations(file_contents[single_range[0]:single_range[1]]))
            """ locations contain tuple of (location, matched_text)"""

        """sort the node pointers in order of occurrence and remember the node_ids"""
        node_pointer_locations = {}

        for location in locations:
            node_pointer_locations[location[0]] = location[1]
            if location[1] not in visited_nodes:
                visited_nodes.append(location[1])

        for single_range in ranges:

            """
            Get and add the range's contents
            """
            range_contents = file_contents[single_range[0]:single_range[1]]

            if 'keep_syntax' not in self.project.nodes[root_node_id].metadata.get_values('_settings'):
                range_contents = self._strip_urtext_syntax(range_contents)
            
            """
            If this is the node's first range:
            """
            if single_range == ranges[0]:
    
                ## Replace and Format Title
                if 'c' not in self.project.nodes[root_node_id].metadata.get_values('flags'):
                    if not meta_title: 
                        range_contents = range_contents.replace(title,'',1)
                    range_contents = self._wrap_title(kind, root_node_id, nested) + range_contents
                else:
                    nested -=1
                
                if 'n' in self.project.nodes[root_node_id].metadata.get_values('flags'):
                    range_contents += '  \n'
                    
                if kind == '-html' and not strip_urtext_syntax:
                    added_contents += OPENING_BRACKETS

            if kind == '-html':
                """
                Insert special HTML wrappers
                """
                lines = [line.strip() for line in range_contents.split('\n') if line.strip() != '']
                index = 0
                while index < len(lines):
                    line = lines[index]

                    """
                    Insert HTML <ul><li><li></ul> tags for lists
                    """
                    if line[0] == '-':
                        range_contents += '<ul class="urtext-list">'
                        while index < len(lines) - 1:
                            range_contents += '<li>'+line[1:]+'</li>'
                            index += 1
                            line = lines[index]
                            if line[0] != '-':
                                break
                        range_contents += '</ul>'

                    """
                    For non-list items, wrap them in a <div>
                    """
                    range_contents += '<div class="urtext_line">' + line.strip()
                    if range_contents == ranges[-1] and line == lines[-1] and not strip_urtext_syntax:
                        range_contents += '<span class="urtext-close-brackets">&#125;&#125;</span>'                
                    range_contents += '</div>\n'     
                    index += 1           

            """
            Add the range contents only after the title, if any.
            """
            if kind in ['-markdown', '-md']:
                range_contents = strip_leading_space(range_contents)
                    
            if not self.project.nodes[root_node_id].is_tree or not preformat:
                ## Only replace node links if this is not a tree
                ## or it is a tree and preformat was not selected
                range_contents = self.replace_node_links(range_contents, kind)
            
            if kind in ['-markdown', '-md']:
                range_contents = self.replace_file_links(range_contents)

            if clean_whitespace:
                range_contents = range_contents.strip()
                if range_contents:
                    range_contents = range_contents + '\n'

            if single_range != ranges[0] and kind == '-html':    
 
                """
                Otherwise, only for HTML, wrap all important elements
                """
        
                heading_tag = 'h'+str(nested)
                range_contents = range_contents.replace(  
                    title,
                    '<'+heading_tag+'>'+title+'</'+heading_tag+'>',
                    1)

            """
            If this is end of the node, mark it complete
            """
            if single_range[1] == ranges[-1][1]:
                range_contents += self._closing_wrapper(kind)

            """
            map the exported content to the source content.
            (returns node ID and exact FILE location)
            Note each point will be relative to the beginning of the 
            containing node, not the beginning of the file containing the export.
            """
            
            points[ (len(added_contents), len(added_contents) + len(range_contents) ) ] = ( root_node_id, single_range[0] )

            added_contents += range_contents
            
            """
            If we are adding subnodes, find the node_id of the node immediately following this range
            and add it, assuming we are including all sub-nodes.
            TODO: Add checking in here for excluded nodes
            """
        
            if not single_node_only and single_range[1] < ranges[-1][1]:

                # get the node in the space immediately following this RANGE
                next_node = self.project.get_node_id_from_position(filename, single_range[1] + 1)
                
                if next_node and next_node not in visited_nodes:

                    """ for HTML, if this is a dynamic node and contains a tree, add the tree"""
                    if kind == '-html' and next_node in self.project.dynamic_nodes and self.project.dynamic_nodes[next_node].tree:
                        exported_contents += self._render_tree_as_html(self.project.dynamic_nodes[next_node].tree)

                    else:

                        next_nested = nested + 1

                        """
                        recursively add the node in the next range and its subnodes
                        """
                        added_contents, points, visited_nodes = self._add_node_content(
                            next_node,
                            added_contents=added_contents,
                            points=points,       
                            as_single_file=as_single_file,
                            strip_urtext_syntax=strip_urtext_syntax,
                            style_titles=style_titles,
                            exclude=exclude,
                            kind=kind,
                            nested=next_nested,
                            clean_whitespace=clean_whitespace,
                            visited_nodes=visited_nodes,
                            preformat=preformat,
                            )
                   
        """
        For this single range of text, replace node pointers with their contents,
        which cals this function recursively.
        """
        if not self.project.nodes[root_node_id].dynamic :  
            if as_single_file:

                added_contents, points, visited_nodes = self.replace_node_pointers(
                    nested,
                    kind,
                    node_pointer_locations,
                    added_contents=added_contents,
                    points=points,
                    as_single_file=True,
                    strip_urtext_syntax=strip_urtext_syntax,
                    style_titles=style_titles,
                    exclude=exclude,
                    clean_whitespace=clean_whitespace,
                    visited_nodes=visited_nodes,
                    preformat=preformat
                   )

        
        return added_contents, points, visited_nodes


    def get_node_pointers_with_locations(self, text):

        patterns = [titled_node_pointer_regex, node_pointer_regex]
        matches = []
        locations = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                locations.append((text.find(match), match))
        return locations

    def replace_node_pointers(self,     
        nested, 
        kind,
        node_pointer_locations, # dict
        added_contents=None,
        points=None,
        as_single_file=False,                       
        strip_urtext_syntax=True,                   
        style_titles=True,                          
        exclude=[],
        clean_whitespace=False,
        visited_nodes=None,
        preformat=False
        ):
    
        if visited_nodes == None:
            visited_nodes = []
        if points == None:
            points = {}
        if added_contents == None:
            added_contents = ''

        locations = sorted(node_pointer_locations)

        for location in locations:

            match = node_pointer_locations[location]
            node_id = match[-3:]

            pointer_length = len(match)

            first_contents = added_contents.split(match)[0]
              
            remaining_contents = ''.join(added_contents.split(match)[1:])
          
            """
            Avoid recursion
            """
            if node_id in visited_nodes:
                inserted_contents = '\n' + '#' * nested + ' ! RECURSION : '+ node_id
                continue       
            
            if node_id not in self.project.nodes:                    
                visited_nodes.append(node_id)
                print('SKIPPING '+node_id)
                continue                            


            # split points here:
            points_so_far = {}
            points_after_that = {}

            length_up_to_pointer = len(first_contents)
            
            for export_range in points:
                if length_up_to_pointer in range(export_range[0], export_range[1]):
                    # need to adjust ranges here since we took out the pointer

                    points_so_far[ (export_range[0], length_up_to_pointer) ] = points[export_range]
                    points_after_that[ (length_up_to_pointer, export_range[1] - pointer_length) ] = points[export_range]
                    continue

                if length_up_to_pointer > export_range[1]:
                    points_so_far[export_range] = points[export_range]
                    continue

                if length_up_to_pointer < export_range[0]:
                    points_after_that[(export_range[0]- pointer_length, export_range[1]-pointer_length)] = points[export_range]
                    continue
                    
            added_contents, points_so_far, visited_nodes = self._add_node_content(
                node_id, 
                added_contents=first_contents,
                points=points_so_far,
                nested=nested+1,
                as_single_file=True,
                kind=kind,
                exclude=exclude,
                strip_urtext_syntax=strip_urtext_syntax,
                style_titles=style_titles,
                clean_whitespace=clean_whitespace,
                visited_nodes=visited_nodes,
                preformat=preformat
                )

            length_after = len(added_contents)
            amount_added = length_after - length_up_to_pointer

            for export_range in points_after_that:
                points_so_far[ (export_range[0] + amount_added, export_range[1] + amount_added)  ] = points_after_that[export_range]

            added_contents += remaining_contents
           
            visited_nodes.append(node_id)
            
            points = points_so_far
            
        return added_contents, points, visited_nodes


    def replace_node_links(self, contents, kind):
        """ replace node links, including titled ones, with exported versions """

        for pattern in [titled_link_regex,  node_link_regex]:

            node_links = re.findall(pattern, contents)

            for match in node_links:

                node_link = re.search(node_link_regex, match)            

                node_id = node_link.group(0)[-3:]

                if node_id not in self.project.nodes:
                    
                    contents = contents.replace(match, '[ MISSING LINK : '+node_id+' ] ')
                    continue

                title = self.project.nodes[node_id].title

                if kind == '-html':

                    filename = self.project.nodes[node_id].filename
                    
                    if node_id in self.project.files[filename].nodes:
                        link = '#'+node_id

                    else: 
                        base_filename = self.project.nodes[node_id].filename
                        this_root_node = self.project.files[base_filename].root_nodes[0]
                        link = this_root_node+'.html#'+ node_id
                
                    contents = contents.replace(match, '<a href="'+link+'">'+title+'</a>')

                if kind in ['-plaintext','-txt']:

                    contents = contents.replace(match, '"'+title+'"')
                     # TODO - make quote wrapper optional
        
                if kind in ['-markdown','-md']:

                    link = '#' + title.lower().replace(' ','-');
                    link = link.replace(')','')
                    link = link.replace('(','')

                    contents = contents.replace(match, '['+title+']('+link+')') 
                    # TODO - make quote wrapper optional

        return contents

    def replace_file_links(self, contents):
        file_links = re.findall(file_link_regex, contents)
        for link in file_links:
            contents = contents.replace(link, '!['+link[2:]+']('+link[2:]+')')
        return contents

    def _strip_urtext_syntax(self, contents):
        contents = UrtextNode.strip_contents(contents)
        if contents and contents[0] in ['}','{']:
            contents = contents[1:]
        if contents and contents[-1] == '{':
            contents = contents[:-1]
            
        contents = re.sub(r'^[^\S\n]*\^', '', contents, flags=re.MULTILINE)
        return contents
 
    def _opening_wrapper(self, kind, node_id, nested):
        wrappers = { 
            '-html': '<div class="urtext_nested_'+str(nested)+'"><a name="'+ node_id + '"></a>',
            '-markdown': '',
            '-plaintext': '',
            '-md': ''
            }
        return wrappers[kind]
    def _closing_wrapper(self, kind):
        wrappers = { 
            '-html': '</div>',
            '-markdown': '',
            '-plaintext': '',
            '-md': '',
            }
        return wrappers[kind]

    def _wrap_title(self, kind, node_id, nested):
        title = self.project.nodes[node_id].title
        wrappers = {
            '-markdown': '\n\n' + '#' * nested + ' ' + title.strip(),
            '-md': '\n\n' + '#' * nested + ' ' + title.strip(),
            '-html' : '<h'+str(nested)+'>' + title + '</h'+str(nested)+'>\n',
            '-plaintext' : title,
        }
        return wrappers[kind]

def insert_format_character(text):
    return '`' + text + '`'

def preformat_embedded_syntaxes(text):
    
    text = re.sub('[^`]%%-DOC','',text )
    text = re.sub('[^`]%%-END-DOC','',text )

    text = re.sub('%%-[^E][A-Z-]*','```',text )
    text = re.sub('%%-END-[A-Z-]*','```',text )
    return text

def strip_leading_space(text):
    result = []
    for line in text.split('\n'):
        if '├' not in line and '└' and '─' not in line:
            line = line.lstrip()
        result.append(line)
    return '\n'.join(result)