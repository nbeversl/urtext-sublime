import re

# Units

pattern_break =                         r'($|(?=[\s|\r|]))'

# Base Patterns

action =                                r'>>>([A-Z_\-\+]+)\((.*)\)'
bullet =                                r'^([^\S\n]*?)•'
closing_wrapper =                       r'(?<!\\)}'
dd_flag =                               r'((^|\s)(-[\w|_]+)|((^|\s)\*))(?=\s|$)'
dd_key =                                r'(^|\s)[\w_]+(\s|$)'
dynamic_def =                           r'(?:\[\[)([^\]]*?)(?:\]\])'
editor_file_link =                      r'(f>{1,2})([^;]+)'
embedded_syntax_open =                  r'(%%-[A-Z-]+?)'
embedded_syntax_full =                  r'(%%-[A-Z-]+?)'
embedded_syntax_close =                 r'%%-[A-Z-]+?-END'
error_messages =                        r'<!{1,2}.*?!{1,2}>\n?'
function =                              r'([A-Z_\-\+]+)\((.*?)\)'
format_key =                            r'\$_?[\.A-Za-z0-9_-]*'
hash_key =                              r'#'
metadata_arg_delimiter =                r';|\r'
metadata_op_before =                    r'before'
metadata_op_after =                     r'after'
metadata_op_equals =                    r'='
metadata_op_not_equals =                r'!='
metadata_op_contains =                  r'\?'
metadata_op_is_like =                   r'~'
metadata_ops_or =                       r'\|'
metadata_assigner =                     r'::'
metadata_end_marker =                   r';'
metadata_entry =                        r'[+]?\*{0,2}\w+\:\:[^\n;]+[\n;]?'
metadata_separator =                    r'\s-\s|$'
metadata_tag_self =                     r'\+'
metadata_tag_desc =                     r'\*'
opening_wrapper =                       r'(?<!\\){'
pop_syntax =                            r'%%-[A-Z]+-END'
preformat =                             r'\`.*?\`'
push_syntax =                           r'%%-([A-Z]+)'+pattern_break
sub_node =                              r'(?<!\\){(?!.*(?<!\\){)(?:(?!}).)*}'
timestamp =                             r'<([^-/<\s][^=<]+?)>'
title_pattern =                         r'([^>\n\r])+'
url =                                   r'http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

# Currently used for syntax highlighting only:

metadata_key =                          r'\w+?(?=' + metadata_assigner + ')'
metadata_values =                       r'(?<=::)[^\n};@]+;?'

metadata_key_c =                        re.compile(metadata_key)
metadata_values_c =                     re.compile(metadata_values)

metadata_flags =                        r'\+?\*{1,2}(?=' + metadata_key + ')' 
metadata_flags_c =                      re.compile(metadata_flags)

# Composite patterns

compact_node =                          bullet + r'([^\r\n]*)(\n|$)'
hash_meta =                             r'(?:^|\s)'+ hash_key + r'[A-Z,a-z].*?\b'
node_link =                             r'(\|\s)(' + title_pattern + ')\s>(?!>)'
node_link_or_pointer =                  r'(\|\s)(' + title_pattern + ')\s>{1,2}(?!>)'
node_pointer =                          r'(\|\s)(' + title_pattern + ')\s>>(?!>)'
node_title =                            r'^'+ title_pattern +r'(?=\s_(\s|$))'

# Compiled Patterns

action_c =                      re.compile(action, re.DOTALL)
bullet_c =                      re.compile(bullet)
compact_node_c =                re.compile(compact_node, re.MULTILINE)
closing_wrapper_c =             re.compile(closing_wrapper)
dd_flag_c =                     re.compile(dd_flag)
dd_key_c =                      re.compile(dd_key)
dynamic_def_c =                 re.compile(dynamic_def, re.DOTALL)
editor_file_link_c =            re.compile(editor_file_link)
embedded_syntax_open_c =        re.compile(embedded_syntax_open, flags=re.DOTALL)
embedded_syntax_c =             re.compile(embedded_syntax_full, flags=re.DOTALL)
embedded_syntax_close_c =       re.compile(embedded_syntax_close, flags=re.DOTALL)
error_messages_c =              re.compile(error_messages, flags=re.DOTALL)
format_key_c =                  re.compile(format_key, re.DOTALL)
function_c =                    re.compile(function, re.DOTALL)
hash_key_c =                    re.compile(hash_key)
hash_meta_c =                   re.compile(hash_meta)
metadata_arg_delimiter_c =      re.compile(metadata_arg_delimiter)
metadata_entry_c =              re.compile(metadata_entry, re.DOTALL)
metadata_ops =                  re.compile(r'(' + r'|'.join([
                                        metadata_op_before,
                                        metadata_op_after,
                                        metadata_op_equals,
                                        metadata_op_not_equals,
                                        metadata_op_contains,
                                        metadata_op_is_like
                                    ]) + r')')

metadata_ops_or_c =             re.compile(metadata_ops_or)
metadata_separator_c =          re.compile(metadata_separator)
metadata_tag_self_c =           re.compile(metadata_tag_self)
metadata_tag_desc_c =           re.compile(metadata_tag_desc)
node_title_c =                  re.compile(node_title, re.MULTILINE)
metadata_assigner_c =           re.compile(metadata_assigner)
node_link_c =                   re.compile(node_link)
node_link_or_pointer_c =        re.compile(node_link_or_pointer)
opening_wrapper_c =             re.compile(opening_wrapper)
preformat_c =                   re.compile(preformat, flags=re.DOTALL)
subnode_regexp_c =              re.compile(sub_node, re.DOTALL)
timestamp_c =                   re.compile(timestamp)
title_regex_c =                 re.compile(title_pattern)
url_c =                         re.compile(url)                       

metadata_replacements = re.compile("|".join([
    r'(?:<)([^-/<\s`][^=<]+?)(?:>)',        # timestamp
    r'\*{2}\w+\:\:([^\n};]+);?',            # inline_meta
    r'(?:^|\s)#[A-Z,a-z].*?(\b|$)',         # shorthand_meta
    ]))

compiled_symbols = {
    opening_wrapper_c :                 'opening_wrapper',
    closing_wrapper_c :                 'closing_wrapper',
    re.compile(node_pointer) :          'pointer',
    re.compile(push_syntax) :           'push_syntax', 
    re.compile(pop_syntax) :            'pop_syntax',
    compact_node_c :                    'compact_node'
    }

