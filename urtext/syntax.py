import re

#
# Main Patterns

action_regex = re.compile(              r'>>>([A-Z_]+)\((.*?)\)', re.DOTALL)
dynamic_definition_regex = re.compile(  '(?:\[\[)([^\]]*?)(?:\]\])', re.DOTALL)
dynamic_def_regexp = re.compile(        r'\[\[[^\]]*?\]\]', re.DOTALL)
editor_file_link_regex = re.compile(    '(f>{1,2})([^;]+)')
embedded_syntax_open = re.compile(      '(%%-[A-Z-]+?)', flags=re.DOTALL)
embedded_syntax = re.compile(           '%%-[A-Z-]*.*?%%-[A-Z-]*-END', flags=re.DOTALL)
embedded_syntax_close = re.compile(     '%%-[A-Z-]+?-END', flags=re.DOTALL)
error_messages =                        '<!{1,2}.*?!{1,2}>\n?'
metadata_entry = re.compile(            '[+]?\*{0,2}\w+\:\:[^\n;]+[\n;]?',re.DOTALL)
file_link_regex = re.compile(           'f>.*?')
flag_regx = re.compile(                 r'((^|\s)(-[\w|_]+)|((^|\s)\*))(?=\s|$)')
format_key_regex = re.compile(          '\$_?[\.A-Za-z0-9_-]*', re.DOTALL)
function_regex = re.compile(            '([A-Z_\-\+]+)\((.*?)\)', re.DOTALL)
hash_meta = re.compile(                 r'(?:^|\s)#[A-Z,a-z].*?\b')
meta_separator = re.compile(            r'\s-\s|$')
source_info = re.compile(               r'\(\(>[0-9,a-z]{3}\:\d+\)\)')
subnode_regexp = re.compile(            r'(?<!\\){(?!.*(?<!\\){)(?:(?!}).)*}', re.DOTALL)
timestamp_match = re.compile(           '<([^-/<\s][^=<]+?)>')

pattern_break =                         '($|(?=[\\s|\r|]))'

# Titles and links
title_pattern =                         r"(([^>\n\r_])|(?<!\s)_)+"
title_regex = re.compile(               title_pattern)
node_link_regex =                       r'(\|\s)(' + title_pattern + ')\s>(?!>)'
node_link_or_pointer_regex =            r'(\|\s)(' + title_pattern + ')\s>{1,2}(?!>)'
node_pointer_regex =                    r'(\|\s)(' + title_pattern + ')\s>>(?!>)'
node_title_regex = re.compile(          '^'+ title_pattern +'(?= _)' + pattern_break, re.MULTILINE)
url_scheme = re.compile(                r'http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

#
# Metadata

metadata_replacements = re.compile("|".join([
    r'(?:<)([^-/<\s`][^=<]+?)(?:>)',        # timestamp
    r'\*{2}\w+\:\:([^\n};]+);?',            # inline_meta
    r'(?:^|\s)#[A-Z,a-z].*?(\b|$)',         # shorthand_meta
    ]))

#
# Compilation

compiled_symbols = {
    re.compile(r'(?<!\\){') :           'opening_wrapper',
    re.compile(r'(?<!\\)}')  :          'closing_wrapper',
    re.compile(node_pointer_regex) :    'pointer',
    re.compile(r'%%-[A-Z]*')       :    'push_syntax', 
    re.compile(r'%%-[A-Z]*-END')   :    'pop_syntax',
    re.compile(r'^([^\S\n]*?)•([^\r\n]*)\n', re.MULTILINE) : 'compact_node'
    }

