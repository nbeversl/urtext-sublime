import re
from anytree import Node, PreOrderIter
from urtext.metadata import MetadataEntry
from urtext.metadata import NodeMetadata, MetadataValue
from anytree.exporter import JsonExporter
from urtext.dynamic_definition import UrtextDynamicDefinition
import urtext.utils as utils
import urtext.syntax as syntax

class UrtextNode:

    urtext_metadata = NodeMetadata

    def __init__(self, 
        contents,
        project,
        root=False,
        compact=False,
        nested=None):

        self.project = project
        self.ranges = []
        self.is_tree = False
        self.is_node = True
        self.is_meta = False
        self.meta_key = None
        self.export_points = {}
        self.dynamic = False
        self.id = None
        self.pointers = []
        self.display_detail = ''
        self.links = []
        self.root_node = root
        self.compact = compact
        self.dynamic_definitions = []
        self.target_nodes = []
        self.untitled = False
        self.title_only = False
        self.title = ''
        self.parent = None
        self.children = []
        self.first_line_title = False
        self.title_from_marker = False
        self.nested = nested
        self.resolved = False
        self.filename = None
        self.embedded_syntax_ranges = []
        self.dd_ranges = []
        
        contents = strip_errors(contents)
        self.full_contents = contents
        self.embedded_syntax_ranges, stripped_contents, replaced_contents = strip_embedded_syntaxes(contents)
        self._get_links(replaced_contents)
        self.dd_ranges, stripped_contents, replaced_contents = self.parse_dynamic_definitions(replaced_contents)
        self.metadata = self.urtext_metadata(self, self.project)        
        stripped_contents, replaced_contents = self.metadata.parse_contents(replaced_contents)
        for link in self.links:
            stripped_contents = stripped_contents.replace(link.matching_string, '', 1)        
        self.title = self.set_title(stripped_contents)
        if not stripped_contents.strip().replace(self.title,'').replace(' _',''):
            self.title_only = True
        self.id = self.title
        for d in self.dynamic_definitions:
            d.source_node = self
        for entry in self.metadata.entries():
            entry.from_node = self
        self.stripped_contents = stripped_contents   
        self.text = utils.make_node_link(self.id)

    def get_file_position(self, node_position): 
        node_length = 0
        offset_position = node_position
        for r in self.ranges:
            range_length = r[1] - r[0]
            node_length += range_length
            if node_position <= node_length:
                return r[0] + offset_position
            offset_position -= range_length

    def get_date(self, date_keyword):
        return self.metadata.get_date(date_keyword)

    def contents(self,
        stripped=True,
        strip_first_line_title=False):

        if stripped:
            contents = self.stripped_contents
        else:
            contents = self.full_contents

        if strip_first_line_title:
            return self.strip_first_line_title(contents)
        
        return contents

    def links_ids(self):
        return [link.node_id for link in self.links]

    def date(self):
        return self.metadata.get_date(self.project.get_setting('node_date_keyname'))

    def resolve_id(self, allocated_ids=None):
        return_value = {
            'resolved_id': None,
            'method': None,
            'reason': None,
        }
        if self.resolved:
            return_value = {
                'resolved_id': self.id,
                'method': "already resolved",
            }
        if allocated_ids is None:
            allocated_ids = self.project.nodes
        timestamp = self.metadata.get_oldest_timestamp()
        if self.parent:
            if self.is_meta:
                resolved_id = ''.join([
                        self.meta_key,
                        syntax.resolution_identifier,
                        self.parent.title
                    ])
                if resolved_id not in allocated_ids:
                    self.resolved = True
                    return_value['resolved_id'] = resolved_id
                    return_value['method'] = 'meta key'
                    return return_value
                if timestamp:
                    resolved_id = ''.join([
                        self.meta_key,
                        syntax.resolution_identifier,
                        timestamp.unwrapped_string
                    ])
                    if resolved_id not in allocated_ids:
                        self.resolved = True
                        return_value['resolved_id'] = resolved_id
                        return_value['method'] = 'meta key and timestamp'
                        return return_value

            if self.parent.title != '(untitled)':
                resolved_id = ''.join([
                        self.title,
                        syntax.resolution_identifier,
                        self.parent.title
                    ])
                if resolved_id not in allocated_ids:
                    self.resolved = True
                    return_value['resolved_id'] = resolved_id
                    return_value['method'] = 'parent title'
                    return return_value

            parent_oldest_timestamp = self.parent.metadata.get_oldest_timestamp()
            if parent_oldest_timestamp:
                resolved_id = ''.join([
                        self.title,
                        syntax.resolution_identifier,
                        parent_oldest_timestamp.unwrapped_string
                    ])
                if resolved_id not in allocated_ids:
                    self.resolved = True
                    return_value['resolved_id'] = resolved_id
                    return_value['method'] = 'parent timestamp'
                    return_value['reason'] = 'parent is untitled'
                    return return_value
        if timestamp:
            resolved_id = ''.join([
                self.title,
                syntax.resolution_identifier,
                timestamp.unwrapped_string, 
                ])
            if resolved_id not in allocated_ids:
                self.resolved = True
                self.id = resolved_id
                return_value['resolved_id'] = resolved_id
                return_value['method'] = 'own timestamp'
                return_value['reason'] = 'parent is untitled and parent timestamp not available'
                return return_value
            else:
                return_value['reason'] = 'timestamp is used to resolve %s' % utils.make_node_link(resolved_id)
                return return_value

        return_value['reason'] = 'no title or timestamp in parent, no timestamp in node'
        return return_value

    def _get_links(self, positioned_contents):
        urtext_links, replaced_contents = utils.get_all_links_from_string(positioned_contents)
        for urtext_link in urtext_links:
            urtext_link.containing_node = self
            self.links.append(urtext_link)

    def set_title(self, contents):
        """
        - `title` metadata key overrides any _ marker.
        - Then the first ` _` marker overrides any subsequent one.
            - If it is on the first line, 
            we need to remember this for dynamic nodes.
        - if nothing else found, title is the first non-blank line
        """
        t = self.metadata.get_first_value('title')
        if t:
            return t.text

        first_non_blank_line = None
        contents_lines = contents.strip().split('\n')
        for line in contents_lines:
            first_non_blank_line = line.strip()
            first_non_blank_line = strip_nested_links(first_non_blank_line).strip()
            if first_non_blank_line and first_non_blank_line != '_':
                break

        title = syntax.node_title_c.search(contents)
        if title:
            title = title.group().strip()
            title = title.strip(syntax.title_marker).strip()
        if title:
            self.title_from_marker = True
            if title in first_non_blank_line:
                self.first_line_title = True 
        elif first_non_blank_line:
            title = first_non_blank_line
            for character in syntax.disallowed_title_characters:
                title = re.sub(character, ' ', title)
            title = title.strip()
            self.first_line_title = True
        if not title:
            title = '(untitled)'
            self.untitled = True
        if len(title) > 255:
            title = title[:255].strip()
        self.metadata.add_entry('title', [MetadataValue(title)], self)
        return title
   
    def log(self):
        print(self.id)
        print(self.filename)
        self.metadata.log()

    def consolidate_metadata(self, one_line=True, separator='::'):
        
        keynames = {}
        for entry in self.metadata.entries():
            if entry.keyname in [
                '_newest_timestamp',
                '_oldest_timestamp', 
                'inline_timestamp']:
                continue
            if entry.is_node:
                continue
            if entry.keyname not in keynames:
                keynames[entry.keyname] = []
            keynames[entry.keyname] = [v.unparsed_text for v in entry.meta_values]

        return self.build_metadata(keynames, one_line=one_line, separator=separator)

    @classmethod
    def build_metadata(self, 
        metadata, 
        one_line=None, 
        separator=syntax.metadata_assignment_operator
        ):

        if not metadata:
            return ''

        line_separator = '\n'
        if one_line:
            line_separator = syntax.metadata_closing_marker + ' '
        new_metadata = ''

        for keyname in metadata:
            new_metadata += keyname + separator
            if isinstance(metadata[keyname], list):
                new_metadata += ' - '.join(metadata[keyname])
            else:
                new_metadata += str(metadata[keyname])
            new_metadata += line_separator
        return new_metadata.strip()

    def _set_contents(self, new_contents, preserve_title=True):
        """
        use project._set_node_contents() method instead of using this directly.

        potential issues:

        1. file should be parsed before this, in case the content
        has been modified manually by a directive

        2. Appears that dynamnic nodes in node.replace_links() cannot
        be filtered out if the dynamic node itself is in the midst of being updated
    
        """
        node_contents = self.strip_first_line_title(self.full_contents)
        file_contents = self.file._get_contents()        
        if preserve_title and self.first_line_title:
            new_node_contents = ''.join([ 
                ' ',
                self.title,
                new_contents,
                node_contents,
                ])
        else: 
            new_node_contents = ''.join([
                new_contents,
                node_contents
                ])
        new_file_contents = ''.join([
            file_contents[:self.start_position],
            new_contents,
            file_contents[self.end_position:]])
        self.file.set_buffer_contents(new_file_contents, parse_into_project=True)

    def replace_range(self, 
        range_to_replace, 
        replacement_contents):

        self.project._parse_file(self.filename)
        file_contents = self.file._get_contents()
        file_range_to_replace = [
            self.get_file_position(range_to_replace[0]),
            self.get_file_position(range_to_replace[1])
            ]

        new_file_contents = ''.join([
            file_contents[0:file_range_to_replace[0]],
            replacement_contents,
            file_contents[file_range_to_replace[1]:]])
        self.file.set_buffer_contents(new_file_contents)

    def append_content(self, appended_content):
        file_contents = self.file._get_contents()
        new_file_contents = ''.join([
            file_contents[0:start_position],
            contents,
            appended_content,
            file_contents[self.end_position:]])         
        return self.file.set_buffer_contents(new_file_contents)

    def prepend_content(self, prepended_content, preserve_title=True):
        node_contents = self.strip_first_line_title(self.full_contents)
        file_contents = self.file._get_contents()
        
        if preserve_title and self.first_line_title:
            new_node_contents = ''.join([ 
                ' ',
                self.title,
                prepended_content,
                node_contents,
                ])
        else: 
            new_node_contents = ''.join([
                prepended_content,
                node_contents
                ])
        new_file_contents = ''.join([
            file_contents[:self.start_position], # omit opening
            new_node_contents,
            file_contents[self.end_position:]]) 
        return self.file.set_buffer_contents(new_file_contents)

    def parse_dynamic_definitions(self, contents): 
        dd_ranges = []
        stripped_contents = contents
        replaced_contents = contents
        for d in syntax.dynamic_def_c.finditer(contents):
            dd_ranges.append([d.start(),d.end()])
            param_string = d.group(0)[2:-2]
            self.dynamic_definitions.append(
                UrtextDynamicDefinition(
                    param_string, 
                    self.project, 
                    d.start()))
            stripped_contents = stripped_contents.replace(
                d.group(), 
                ' '*len(d.group()), 
                1)
            replaced_contents = replaced_contents.replace(
                d.group(), 
                '', 
                1)

        return dd_ranges, stripped_contents, replaced_contents

    def strip_first_line_title(self, contents):
        if self.first_line_title:
            contents = contents.replace(self.title,'',1)
        if self.title_from_marker:
            contents = contents.replace(syntax.title_marker,'',1)
        return contents

    def ancestors(self):
        return node_ancestors(self)

    def descendants(self):
        return node_descendants(self)

    def replace_links(self, original_id, new_id='', new_project=''):
        if self.dynamic:
            return
        if not new_id and not new_project:
            return None
        if not new_id:
            new_id = original_id
        pattern_to_replace = re.escape(utils.make_node_link(original_id))
        if new_id:
            replacement = utils.make_node_link(new_id)
        if new_project:
            replacement = replacement = utils.make_project_link(new_project) + replacement
        new_contents = self.contents(stripped=False)
        for link in re.finditer(pattern_to_replace, new_contents):
            new_contents = new_contents.replace(link.group(), replacement, 1)
        self._set_contents(new_contents)

    def link(self, include_project=False):
        project_link = ''
        if include_project:
            project_link = utils.make_project_link(self.project.title())
        return ''.join([
            project_link,
            utils.make_node_link(self.id)])

    def pointer(self):
        return utils.make_node_pointer(self.id)

    def ranges_with_embedded_syntaxes(self):
        ranges_with_embedded_syntaxes = {}
        for r in self.ranges:
            for embedded in self.embedded_syntax_ranges:                
                if embedded[0] in range(r[0],r[1]):
                    ranges_with_embedded_syntaxes[r[0]] = {
                        'start' : r[0],
                        'kind': 'urtext',
                        'end' : embedded[0]
                     }
                    ranges_with_embedded_syntaxes[embedded[0]] = {
                        'start' : embedded[0],
                        'kind': 'embedded',
                        'end' : embedded[1]
                     }
                    ranges_with_embedded_syntaxes[embedded[1]] = {
                        'start' : embedded[1],
                        'kind': 'urtext',
                        'end' : r[1]
                     }
            if r[0] not in ranges_with_embedded_syntaxes:
                ranges_with_embedded_syntaxes[r[0]] = {
                    'start' : r[0],
                    'starts_node' : r == self.ranges[0],
                    'ends_node' : r == self.ranges[-1],
                    'kind': 'urtext',
                    'end' : r[1]
                 }

        return ranges_with_embedded_syntaxes


def node_descendants(node, known_descendants=[]):
    # differentiate between pointer and "real" descendants
    all_descendants = [n for n in node.children if n not in known_descendants]
    for descendant in all_descendants:
        all_descendants.extend(
            node_descendants(descendant, known_descendants=all_descendants))
    return all_descendants

def node_ancestors(node, known_ancestors=[]):
    # differentiate between pointer and "real" descendants
    if node.parent:
        known_ancestors.extend(node.parent)
        return node_ancestors(node.parent, known_ancestors)
    return known_ancestors



def strip_contents(contents, 
    preserve_length=False, 
    include_backtick=True,
    reformat_and_keep_embedded_syntaxes=False,
    embedded_syntaxes=True,
    metadata=True,
    dynamic_definitions=True
    ):
    if embedded_syntaxes:
        ranges, stripped_contents, contents = strip_embedded_syntaxes(contents, 
            preserve_length=preserve_length, 
            include_backtick=include_backtick,
            reformat_and_keep_contents=reformat_and_keep_embedded_syntaxes)
    if metadata:
        contents = strip_metadata(
            contents=contents,
            preserve_length=preserve_length)
    if dynamic_definitions:
        contents = strip_dynamic_definitions(
            contents=contents, 
            preserve_length=preserve_length)
    contents = contents.strip().strip('{}').strip()
    return contents

def strip_metadata(contents, preserve_length=False):
    r = ' ' if preserve_length else ''
    for e in syntax.metadata_replacements.finditer(contents):
        contents = contents.replace(e.group(), r*len(e.group()))       
    contents = contents.replace('• ',r*2)
    return contents

def strip_dynamic_definitions(contents, preserve_length=False):
    r = ' ' if preserve_length else ''
    if not contents:
        return contents
    stripped_contents = contents
  
    for dynamic_definition in syntax.dynamic_def_c.finditer(stripped_contents):
        stripped_contents = stripped_contents.replace(dynamic_definition.group(), r*len(dynamic_definition.group()))
    return stripped_contents

def strip_nested_links(title):
    stripped_title = title
    for nested_link in syntax.node_link_or_pointer_c.finditer(title):
        stripped_title = title.replace(nested_link.group(), '')
    return stripped_title

def strip_errors(contents):
    return re.sub('<!.*?!>', '', contents, flags=re.DOTALL)

#TODO refactor
def strip_embedded_syntaxes(
    stripped_contents, 
    preserve_length=False,
    reformat_and_keep_contents=False,
    include_backtick=True):

    ranges = []
    if include_backtick:
        stripped_contents = utils.strip_backtick_escape(stripped_contents)
    replaced_contents = stripped_contents
    for e in syntax.embedded_syntax_c.finditer(stripped_contents):
        contents = e.group()
        if reformat_and_keep_contents:
            unwrapped_contents = contents
            for opening_wrapper in syntax.embedded_syntax_open_c.findall(unwrapped_contents):
                unwrapped_contents = unwrapped_contents.replace(opening_wrapper,'`',1)   
            for closing_wrapper in syntax.embedded_syntax_close_c.findall(unwrapped_contents):
                unwrapped_contents = unwrapped_contents.replace(closing_wrapper,'`',1)
            unwrapped_contents = unwrapped_contents.strip()
            unwrapped_contents = unwrapped_contents.split('\n')
            unwrapped_contents = [line.strip() for line in unwrapped_contents if line.strip() != '']
            unwrapped_contents = '\t\t\n'.join(unwrapped_contents)
            stripped_contents = stripped_contents.replace(e, unwrapped_contents)
        else:
            stripped_contents = stripped_contents.replace(contents, '')
            replaced_contents = replaced_contents.replace(contents, ' '*len(contents))
        ranges.append([e.start(), e.end()])
    return ranges, stripped_contents, replaced_contents
