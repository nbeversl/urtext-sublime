evaluated_only_at_compile = [
    'paths',
    'file_extensions'
]

not_cleared = [
    'other_entry_points'
]

single_boolean_values_settings = [
    'always_oneline_meta',
    'preformat',
    'console_log',
    'atomic_rename',
    'contents_strip_outer_whitespace',
    'contents_strip_internal_whitespace'
]

single_values_settings = [
    'home',
    'filename_datestamp_format',
    'filename_title_length',
    'node_date_keyname',
    'timestamp_format',
    'device_keyname',
    'breadcrumb_key',
    'title',
    'new_file_node_format',
    'hash_key',
    'meta_browser_key',
    'meta_browser_sort_keys_by',
    'meta_browser_sort_values_by',
    'project_title',
    'title_length',
    ] + single_boolean_values_settings

replace_settings = [
    #i.e. can be array, but replace, don't extend
    'filenames',
    'node_browser_sort',
    'meta_browser_sort',
    'filename_datestamp_format',
    'exclude_files' 
]

integers_settings = [
    'title_length',
    'filename_title_length',
]

def default_project_settings(): 

    return {  
        'always_oneline_meta': False,
        'atomic_rename' : False,
        'breadcrumb_key' : 'popped_from',
        'case_sensitive': [
            'title',
            'project_title',
            'timestamp_format',
            'filenames',
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
            '_inline_timestamp', 
            ],
        'filenames': ['title'],
        'file_extensions' : ['.urtext'],
        'filename_datestamp_format':'%m-%d-%Y %I-%M %p',
        'filename_title_length': 100,
        'hash_key': 'keyword',
        'home': None,
        'new_file_node_format' : '$timestamp\n$cursor ',
        'meta_browser_key': None,
        'meta_browser_sort_keys_by': 'alpha', # or 'frequency'
        'meta_browser_sort_values_by' : 'alpha', # 'or 'frequency'
        'meta_browser_sort' : ['_oldest_timestamp'],
        'node_browser_sort' : ['_oldest_timestamp'],
        'node_date_keyname' : '_oldest_timestamp',
        'numerical_keys': ['_index' ,'index','title_length'],
        'other_project_entry_points' : [],
        'paths': [],
        'project_title' : None,
        'timestamp_format':'%a., %b. %d, %Y, %I:%M %p %Z', 
        'title_length':255,
        'use_timestamp': [ 
            'timestamp', 
            '_inline_timestamp', 
            '_oldest_timestamp', 
            '_newest_timestamp'],
    }