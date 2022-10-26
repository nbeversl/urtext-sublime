import re

#
# Main Patterns

title_pattern =                         "[\w \^\.\,\?\-\/\:’'\"\)\()]"
action_regex = re.compile(              r'>>>([A-Z_]+)\((.*?)\)', re.DOTALL)
dynamic_definition_regex = re.compile(  '(?:\[\[)([^\]]*?)(?:\]\])', re.DOTALL)
dynamic_def_regexp = re.compile(        r'\[\[[^\]]*?\]\]', re.DOTALL)
editor_file_link_regex = re.compile(    '(f>{1,2})([^;]+)')
embedded_syntax_open = re.compile(      '(%%-[A-Z-]+?)', flags=re.DOTALL)
embedded_syntax = re.compile(           '%%-[A-Z-]*.*?%%-[A-Z-]*-END', flags=re.DOTALL)
embedded_syntax_close = re.compile(     '%%-[A-Z-]+?-END', flags=re.DOTALL)
error_messages =                        '<!{1,2}.*?!{1,2}>\n?'
metadata_entry = re.compile(            '\w+\:\:[^\n;]+[\n;]?',re.DOTALL)
file_link_regex = re.compile(           'f>.*?')
flag_regx = re.compile(                 r'((^|\s)(-[\w|_]+)|((^|\s)\*))(?=\s|$)')
format_key_regex = re.compile(          '\$_?[\.A-Za-z0-9_-]*', re.DOTALL)
function_regex = re.compile(            '([A-Z_\-\+]+)\((.*?)\)', re.DOTALL)
hash_meta = re.compile(                 r'(?:^|\s)#[A-Z,a-z].*?\b')
meta_separator = re.compile(            r'\s-\s|$')
node_title_regex = re.compile(          '^[^\n_]*?(?= _)[\s|\r]', re.MULTILINE)
node_link_regex =                       r'(\|\s)([A-Z,a-z,1-9,\',\s,\:\']+)(>){1,2}'
node_pointer_regex =                    r'(\|\s)([A-Z,a-z,1-9,\',\s,\:,\']+)\s>>'
source_info = re.compile(              r'\(\(>[0-9,a-z]{3}\:\d+\)\)')
subnode_regexp = re.compile(            r'(?<!\\){(?!.*(?<!\\){)(?:(?!}).)*}', re.DOTALL)
timestamp_match = re.compile(           '<([^-/<\s][^=<]+?)>')
title_regex = re.compile(               r"[\w \^\.\,\?\-\/\:’'\"\)\()]+")
titled_link_regex =                     r'\|\S' + title_pattern + ' [^>]>\b'
titled_node_pointer_regex =             r'\|.*?>>\b'
url_scheme = re.compile(                r'http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

#
# Metadata

metadata_replacements = re.compile("|".join([
    '(?:<)([^-/<\s`][^=<]+?)(?:>)',         # timestamp
    '\*{0,2}\w+\:\:([^\n};]+;?(?=>:})?)?',  # inline_meta
    r'(?:^|\s)#[A-Z,a-z].*?(\b|$)',         # shorthand_meta
    ]))

#
# Compilation

compiled_symbols = {
    re.compile(r'(?<!\\){') :       'opening_wrapper',
    re.compile(r'(?<!\\)}')  :      'closing_wrapper',
    re.compile(node_pointer_regex) : 'pointer',
    re.compile(r'%%-[A-Z]*')       : 'push_syntax', 
    re.compile(r'%%-[A-Z]*-END')   : 'pop_syntax',
    re.compile(r'^([^\S\n]*?)•([^\n]*)[\n]', re.MULTILINE) : 'compact_node'
    }

