import os
import re
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'sublime.txt')):
    import Urtext.urtext.syntax as syntax
else:
    import urtext.syntax as syntax

def strip_backtick_escape(contents):
    for e in syntax.preformat_c.findall(contents):
        contents = contents.replace(e,' '*len(e))
    return contents

def force_list(thing):
	if not isinstance(thing, list):
		thing = [thing]
	return thing

def get_id_from_link(target):
    target = re.sub(syntax.node_link_opening_wrapper_match, '', target)
    target = target.strip(syntax.link_closing_wrapper)
    target = target.replace('\\(', '(')
    target = target.replace('\\)', ')')
    return target.strip()
