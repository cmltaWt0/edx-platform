import json

from lxml import etree

from mitxmako.shortcuts import render_to_string

from x_module import XModule

# HACK: This shouldn't be hard-coded to two types
# OBSOLETE: This obsoletes 'type'
class_priority = ['video', 'problem']

class Module(XModule):
    ''' Layout module which lays out content in a temporal sequence
    '''
    id_attribute = 'id'

    def get_state(self):
        return json.dumps({ 'position':self.position })

    @classmethod
    def get_xml_tags(c):
        obsolete_tags = ["sequential", 'tab']
        modern_tags = ["problemset", "videosequence"]
        return obsolete_tags + modern_tags
        
    def get_html(self):
        self.render()
        return self.content

    def get_init_js(self):
        self.render()
        return self.init_js

    def get_destroy_js(self):
        self.render()
        return self.destroy_js

    def handle_ajax(self, dispatch, get):
        if dispatch=='goto_position':
            self.position = int(get['position'])
            return json.dumps({'success':True})
        raise self.system.exception404

    def render(self):
        if self.rendered:
            return
        def j(m): 
            ''' jsonify contents so it can be embedded in a js array
            We also need to split </script> tags so they don't break
            mid-string'''
            if 'init_js' not in m: m['init_js']=""
            if 'type' not in m: m['init_js']=""
            content=json.dumps(m['content']) 
            content=content.replace('</script>', '<"+"/script>') 

            return {'content':content, 
                    "destroy_js":m['destroy_js'], 
                    'init_js':m['init_js'], 
                    'type': m['type']}


        ## Returns a set of all types of all sub-children
        child_classes = [set([i.tag for i in e.iter()]) for e in self.xmltree]

        self.titles = json.dumps(["\n".join([i.get("name").strip() for i in e.iter() if i.get("name") != None]) \
                           for e in self.xmltree])

        self.contents = [j(self.render_function(e)) \
                             for e in self.xmltree]

        print self.titles

        for (content, element_class) in zip(self.contents, child_classes):
            new_class = 'other'
            for c in class_priority:
                if c in element_class: 
                    new_class = c
            content['type'] = new_class
     
        js=""

        params={'items':self.contents,
                'id':self.item_id,
                'position': self.position,
                'titles':self.titles}

        # TODO/BUG: Destroy JavaScript should only be called for the active view
        # This calls it for all the views
        # 
        # To fix this, we'd probably want to have some way of assigning unique
        # IDs to sequences. 
        destroy_js="".join([e['destroy_js'] for e in self.contents if 'destroy_js' in e])

        if self.xmltree.tag == 'sequential':
            self.init_js=js+render_to_string('seq_module.js',params)
            self.destroy_js=destroy_js
            self.content=render_to_string('seq_module.html',params)
        if self.xmltree.tag == 'tab':
            params['id'] = 'tab'
            self.init_js=js+render_to_string('tab_module.js',params)
            self.destroy_js=destroy_js
            self.content=render_to_string('tab_module.html',params)
        self.rendered = True
        

    def __init__(self, system, xml, item_id, state=None):
        XModule.__init__(self, system, xml, item_id, state)
        self.xmltree = etree.fromstring(xml)

        self.position = 1

        if state != None:
            state = json.loads(state)
            if 'position' in state: self.position = int(state['position'])

        self.rendered = False
