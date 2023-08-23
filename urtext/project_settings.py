single_values_settings = [
    'home',
    'project_title',
    'node_date_keyname',
    'timestamp_format',
    'device_keyname',
    'breadcrumb_key',
    'title',
    'new_file_node_format',
    'hash_key',
    'filename_datestamp_format',
    'new_file_line_pos',
    'title_length',
    'filename_title_length' ]

single_boolean_values_settings = [
    'always_oneline_meta',
    'preformat',
    'console_log',
    'import',
    'atomic_rename',
    'keyless_timestamp',
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
        'always_oneline_meta': False,
        'atomic_rename' : False,
        'breadcrumb_key' : '',
        'case_sensitive': [
            'title',
            'notes',
            'comments',
            'project_title',
            'timestamp_format',
            'filenames',
            'weblink',
            'timestamp',],
        'console_log': False,
        'contents_strip_internal_whitespace' : True,
        'contents_strip_outer_whitespace' : True,
        'device_keyname' : '',
        'exclude_files': [],
        'exclude_from_star': [
            'title', 
            '_newest_timestamp', 
            '_oldest_timestamp', 
            '_breadcrumb',
            'def'],        
        'filenames': ['title'],
        'file_extensions' : ['.urtext'],
        'file_index_sort': ['_oldest_timestamp'],
        'filename_datestamp_format':'%m-%d-%Y',
        'file_node_timestamp' : True,
        'filename_title_length': 100,
        'hash_key': '#',
        'home': None,
        'import': False,
        'initial_project': None,
        'keyless_timestamp' : True,
        'new_file_node_format' : '$timestamp\n$cursor',
        'new_file_line_pos' : 2,
        'node_browser_sort' : ['_oldest_timestamp'],
        'node_date_keyname' : 'timestamp',
        'numerical_keys': ['_index' ,'index','title_length'],
        'open_with_system' : ['pdf'],
        'other_projects' : [],
        'paths': [],
        'project_title' : None,
        'recurse_folders': False,
        'tag_other': [],
        'timestamp_format':'%a., %b. %d, %Y, %I:%M %p %Z', 
        'title_length':255,
        'use_timestamp': [ 
            'updated', 
            'timestamp', 
            'inline_timestamp', 
            '_oldest_timestamp', 
            '_newest_timestamp'],
    }