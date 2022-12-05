single_values_settings = [
    'home',
    'project_title',
    'node_date_keyname',
    'timestamp_format',
    'device_keyname',
    'breadcrumb_key',
    'title',
    'id',
    'new_file_node_format',
    'new_bracket_node_format',
    'hash_key',
    'filename_datestamp_format',
    'new_file_line_pos',
    'title_length',
    'filename_title_length' ]

single_boolean_values_settings = [
    'allow_untitled_nodes',
    'always_oneline_meta',
    'preformat',
    'console_log',
    'import',
    'strict',
    'atomic_rename',
    'autoindex',
    'keyless_timestamp',
    'resolve_duplicate_ids',
    'file_node_timestamp',
    'contents_strip_outer_whitespace',
    'contents_strip_internal_whitespace',]

replace_settings = [
    'file_index_sort',
    'filenames',
    'node_browser_sort',
    'tag_other',
    'filename_datestamp_format',
    'exclude_files' ]

integers_settings = [
    'new_file_line_pos',
    'title_length',
    'filename_title_length',
    'new_file_line_pos'
]

def default_project_settings(): 

    return {  
        'home': None,
        'import': False,
        'timestamp_format':'%a., %b. %d, %Y, %I:%M %p %Z', 
        'use_timestamp': [ 
            'updated', 
            'timestamp', 
            'inline_timestamp', 
            '_oldest_timestamp', 
            '_newest_timestamp'],
        'filenames': ['PREFIX', 'title'],
        'filename_datestamp_format':'%m-%d-%Y',
        'console_log': True,
        'always_oneline_meta': False,
        'node_date_keyname' : 'timestamp',
        'numerical_keys': ['_index' ,'index','title_length'],
        'atomic_rename' : False,
        'allow_untitled_nodes':True,
        'tag_other': [],
        'title_length':255,
        'device_keyname' : '',
        'filename_title_length': 100,
        'exclude_files': [],
        'breadcrumb_key' : '',
        'new_file_node_format' : '$timestamp\n$cursor',
        'new_file_line_pos' : 2,
        'keyless_timestamp' : True,
        'file_node_timestamp' : True,
        'resolve_duplicate_ids':True,
        'hash_key': '#',
        'contents_strip_outer_whitespace' : True,
        'contents_strip_internal_whitespace' : True,
        'node_browser_sort' : ['_oldest_timestamp'],
        'open_with_system' : ['pdf'],
        'exclude_from_star': [
            'title', 
            '_newest_timestamp', 
            '_oldest_timestamp', 
            '_breadcrumb',
             'def'],
        'file_index_sort': ['_oldest_timestamp'],
        'case_sensitive': [
            'title',
            'notes',
            'comments',
            'project_title',
            'timestamp_format',
            'filenames',
            'weblink',
            'timestamp',],
    }