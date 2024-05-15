import os
import re
import urtext.syntax as syntax
from urtext.url import url_match_c
from urtext.link import UrtextLink

def strip_backtick_escape(contents):
    for e in syntax.preformat_c.findall(contents):
        contents = contents.replace(e,' '*len(e))
    return contents

def force_list(thing):
	if not isinstance(thing, list):
		thing = [thing]
	return thing

def match_compact_node(selection):
    return True if syntax.compact_node_c.match(selection) else False

def strip_illegal_file_characters(filename):
    for c in [
        '<', '>', '\:', '"', '/', '\\', '|', '?','*', '.', ';', '%']:
        filename = filename.replace(c,' ')
    return filename

def get_id_from_link(target):
    match = syntax.node_link_or_pointer_c.search(target)
    if match:
        return match.group(5)
    return target

def make_project_link(project_name):
    return ''.join([
        syntax.other_project_link_prefix,
        '"%s"' % project_name
        ])

def write_file_contents(filename, contents):
    if os.path.exists(filename):
        os.remove(filename)    
    with open(filename, 'w', encoding='utf-8' ) as f:
        f.write(contents)    

def get_path_from_link(link):
    match = syntax.file_link_c.match(link)
    if match:
        return match.group(1)
    return link

def make_node_link(node_id):
    return ''.join([
        syntax.link_opening_wrapper,
        node_id,
        syntax.link_closing_wrapper])

def make_node_pointer(node_id):
    return ''.join([
        syntax.link_opening_wrapper,
        node_id,
        syntax.pointer_closing_wrapper])

def get_all_links_from_string(string, include_http=False):
    links = []
    replaced_contents = string

    if include_http:
        for match in url_match_c.finditer(replaced_contents):
            if match.group(1):
                http_link = match.group(1)
            else:
                http_link = match.group(3)
            link = UrtextLink(http_link)          
            link.is_http = True
            link.url = http_link
            link.position_in_string = match.start()
            links.append(link)
            replaced_contents = replaced_contents.replace(http_link,' ', 1)

    for match in syntax.cross_project_link_with_node_c.finditer(replaced_contents):
        link = UrtextLink(match.group())        
        link.project_name = match.group(2)
        link.node_id = match.group(7)
        link.is_node = True
        if match.group(10):
            link.dest_node_position = match.group(10)[1:]
        link.position_in_string = match.start()
        links.append(link)
        replaced_contents = replaced_contents.replace(match.group(),' ', 1)

    for match in syntax.node_link_or_pointer_c.finditer(replaced_contents):
        link = UrtextLink(match.group())
        kind = None
        if match.group(1) in syntax.link_modifiers.values():
            for kind in syntax.link_modifiers:
                if match.group(1) == syntax.link_modifiers[kind]:
                    kind = kind.upper()
                    break

        if kind == 'FILE':
            link.is_file = True
            path = match.group(5).strip()
            if path and path[0] == '~':
                path = os.path.expanduser(path)
            link.path = path

        if kind == 'ACTION':
            link.is_action = True

        if kind == 'MISSING':
            link.is_missing = True

        if match.group(5):
            link.node_id = match.group(5).strip()
            link.is_node = True
            if match.group(8):
                link.dest_node_position = int(match.group(8)[1:])

        if match.group(8) == syntax.pointer_closing_wrapper:
            link.is_pointer = True  
        link.position_in_string = match.start()
        links.append(link)
        replaced_contents = replaced_contents.replace(match.group(),' ', 1)
    
    for match in syntax.project_link_c.finditer(replaced_contents):
        link = UrtextLink(match.group())        
        link.project_name = match.group(2)      
        link.position_in_string = match.start()
        links.append(link)
        replaced_contents = replaced_contents.replace(match.group(),' ', 1)

    return links, replaced_contents

def get_link_from_position_in_string(string, position, include_http=True):
    if not string.strip():
        return None
    links, r = get_all_links_from_string(string, include_http=include_http)
    if links:
        links = sorted(links, key=lambda l: l.position_in_string)
        for link in links:
            if position in range(link.position_in_string, link.position_in_string+len(link.matching_string)):
                return link
        return link
