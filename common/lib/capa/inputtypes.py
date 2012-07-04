#
# File:   courseware/capa/inputtypes.py
#

'''
Module containing the problem elements which render into input objects

- textline
- textbox     (change this to textarea?)
- schemmatic
- choicegroup (for multiplechoice: checkbox, radio, or select option)
- imageinput  (for clickable image)
- optioninput (for option list)

These are matched by *.html files templates/*.html which are mako templates with the actual html.

Each input type takes the xml tree as 'element', the previous answer as 'value', and the graded status as 'status'

'''

# TODO: rename "state" to "status" for all below
# status is currently the answer for the problem ID for the input element,
# but it will turn into a dict containing both the answer and any associated message for the problem ID for the input element.

import logging
import re
import shlex # for splitting quoted strings

from lxml import etree
import xml.sax.saxutils as saxutils

log = logging.getLogger('mitx.' + __name__)

def get_input_xml_tags():
    ''' Eventually, this will be for all registered input types '''
    return SimpleInput.get_xml_tags()

class SimpleInput():# XModule
    '''
    Type for simple inputs -- plain HTML with a form element
    '''

    xml_tags = {} ## Maps tags to functions

    def __init__(self, system, xml, item_id = None, track_url=None, state=None, use = 'capa_input'):
        '''
        Instantiate a SimpleInput class.  Arguments:

        - system    : I4xSystem instance which provides OS, rendering, and user context 
        - xml       : Element tree of this Input element
        - item_id   : id for this input element (assigned by capa_problem.LoncapProblem) - string
        - track_url : URL used for tracking - string
        - state     : a dictionary with optional keys: 
                      * Value
                      * ID
                      * Status (answered, unanswered, unsubmitted)
                      * Feedback (dictionary containing keys for hints, errors, or other 
                        feedback from previous attempt)
        - use        :
        '''

        self.xml = xml
        self.tag = xml.tag
        self.system = system
        if not state: state = {}

        ## ID should only come from one place. 
        ## If it comes from multiple, we use state first, XML second, and parameter
        ## third. Since we don't make this guarantee, we can swap this around in 
        ## the future if there's a more logical order. 
        if item_id:       self.id = item_id
        if xml.get('id'): self.id = xml.get('id')
        if 'id' in state: self.id = state['id']

        self.value = ''
        if 'value' in state:
            self.value = state['value']

        self.msg = ''
        feedback = state.get('feedback')
        if feedback is not None:
            self.msg = feedback.get('message','')
            self.hint = feedback.get('hint','')
            self.hintmode = feedback.get('hintmode',None)
            
            # put hint above msg if to be displayed
            if self.hintmode == 'always':
                self.msg = self.hint + ('<br/.>' if self.msg else '') + self.msg
 
        self.status = 'unanswered'
        if 'status' in state:
            self.status = state['status']

    @classmethod
    def get_xml_tags(c):
        return c.xml_tags.keys()

    @classmethod
    def get_uses(c):
        return ['capa_input', 'capa_transform']

    def get_html(self):
        return self.xml_tags[self.tag](self.xml, self.value, self.status, self.system.render_template, self.msg)

def register_render_function(fn, names=None, cls=SimpleInput):
    if names is None:
        SimpleInput.xml_tags[fn.__name__] = fn
    else:
        raise NotImplementedError
    def wrapped():
        return fn
    return wrapped

#-----------------------------------------------------------------------------

@register_render_function
def optioninput(element, value, status, render_template, msg=''):
    '''
    Select option input type.

    Example:

    <optioninput options="('Up','Down')" correct="Up"/><text>The location of the sky</text>
    '''
    eid=element.get('id')
    options = element.get('options')
    if not options:
        raise Exception("[courseware.capa.inputtypes.optioninput] Missing options specification in " + etree.tostring(element))
    oset = shlex.shlex(options[1:-1])
    oset.quotes = "'"
    oset.whitespace = ","
    oset = [x[1:-1] for x  in list(oset)]

    # osetdict = dict([('option_%s_%s' % (eid,x),oset[x]) for x in range(len(oset)) ])	# make dict with IDs
    osetdict = dict([(oset[x],oset[x]) for x in range(len(oset)) ])	# make dict with key,value same
    
    context={'id':eid,
             'value':value,
             'state':status,
             'msg':msg,
             'options':osetdict,
             }

    html = render_template("optioninput.html", context)
    return etree.XML(html)

#-----------------------------------------------------------------------------
@register_render_function
def choicegroup(element, value, status, render_template, msg=''):
    '''
    Radio button inputs: multiple choice or true/false

    TODO: allow order of choices to be randomized, following lon-capa spec.  Use "location" attribute,
    ie random, top, bottom.
    '''
    eid=element.get('id')
    if element.get('type') == "MultipleChoice":
        type="radio"
    elif element.get('type') == "TrueFalse":
        type="checkbox"
    else:
        type="radio"
    choices={}
    for choice in element:
        if not choice.tag=='choice':
            raise Exception("[courseware.capa.inputtypes.choicegroup] Error only <choice> tags should be immediate children of a <choicegroup>, found %s instead" % choice.tag)
        ctext = ""
        ctext += ''.join([etree.tostring(x) for x in choice])	# TODO: what if choice[0] has math tags in it?
        ctext += choice.text		# TODO: fix order?
        choices[choice.get("name")] = ctext
    context={'id':eid, 'value':value, 'state':status, 'type':type, 'choices':choices}
    html = render_template("choicegroup.html", context)
    return etree.XML(html)

@register_render_function
def textline(element, value, status, render_template, msg=""):
    '''
    Simple text line input, with optional size specification.
    '''
    if element.get('math') or element.get('dojs'):		# 'dojs' flag is temporary, for backwards compatibility with 8.02x
        return SimpleInput.xml_tags['textline_dynamath'](element,value,status,render_template,msg)
    eid=element.get('id')
    if eid is None:
        msg = 'textline has no id: it probably appears outside of a known response type'
        msg += "\nSee problem XML source line %s" % getattr(element,'sourceline','<unavailable>')
        raise Exception(msg)
    count = int(eid.split('_')[-2])-1 # HACK
    size = element.get('size')
    hidden = element.get('hidden','')	# if specified, then textline is hidden and id is stored in div of name given by hidden
    context = {'id':eid, 'value':value, 'state':status, 'count':count, 'size': size, 'msg': msg, 'hidden': hidden}
    html = render_template("textinput.html", context)
    return etree.XML(html)

#-----------------------------------------------------------------------------

@register_render_function
def textline_dynamath(element, value, status, render_template, msg=''):
    '''
    Text line input with dynamic math display (equation rendered on client in real time during input).
    '''
    # TODO: Make a wrapper for <formulainput>
    # TODO: Make an AJAX loop to confirm equation is okay in real-time as user types
    '''
    textline is used for simple one-line inputs, like formularesponse and symbolicresponse.
    uses a <span id=display_eid>`{::}`</span>
    and a hidden textarea with id=input_eid_fromjs for the mathjax rendering and return.
    '''
    eid=element.get('id')
    count = int(eid.split('_')[-2])-1 # HACK
    size = element.get('size')
    hidden = element.get('hidden','')	# if specified, then textline is hidden and id is stored in div of name given by hidden
    context = {'id':eid, 'value':value, 'state':status, 'count':count, 'size': size,
               'msg':msg, 'hidden' : hidden,
               }
    html = render_template("textinput_dynamath.html", context)
    return etree.XML(html)

#-----------------------------------------------------------------------------
## TODO: Make a wrapper for <codeinput>
@register_render_function
def textbox(element, value, status, render_template, msg=''):
    '''
    The textbox is used for code input.  The message is the return HTML string from
    evaluating the code, eg error messages, and output from the code tests.

    '''
    eid=element.get('id')
    count = int(eid.split('_')[-2])-1 # HACK
    size = element.get('size')
    rows = element.get('rows') or '30'
    cols = element.get('cols') or '80'
    mode = element.get('mode')	or 'python' 	# mode for CodeMirror, eg "python" or "xml"
    hidden = element.get('hidden','')	# if specified, then textline is hidden and id is stored in div of name given by hidden
    linenumbers = element.get('linenumbers')	# for CodeMirror
    if not value: value = element.text	# if no student input yet, then use the default input given by the problem
    context = {'id':eid, 'value':value, 'state':status, 'count':count, 'size': size, 'msg':msg,
               'mode':mode, 'linenumbers':linenumbers,
               'rows':rows, 'cols':cols,
               'hidden' : hidden,
               }
    html = render_template("textbox.html", context)
    try:
        xhtml = etree.XML(html)
    except Exception as err:
        newmsg = 'error %s in rendering message' % (str(err).replace('<','&lt;'))
        newmsg += '<br/>Original message: %s' % msg.replace('<','&lt;')
        context['msg'] = newmsg
        html = render_template("textbox.html", context)
        xhtml = etree.XML(html)
    return xhtml

#-----------------------------------------------------------------------------
@register_render_function
def schematic(element, value, status, render_template, msg=''):
    eid = element.get('id')
    height = element.get('height')
    width = element.get('width')
    parts = element.get('parts')
    analyses = element.get('analyses')
    initial_value = element.get('initial_value')
    submit_analyses = element.get('submit_analyses')
    context = {
        'id':eid,
        'value':value,
        'initial_value':initial_value,
        'state':status,
        'width':width,
        'height':height,
        'parts':parts,
        'analyses':analyses,
        'submit_analyses':submit_analyses,
        }
    html = render_template("schematicinput.html", context)
    return etree.XML(html)

#-----------------------------------------------------------------------------
### TODO: Move out of inputtypes
@register_render_function
def math(element, value, status, render_template, msg=''):
    '''
    This is not really an input type.  It is a convention from Lon-CAPA, used for
    displaying a math equation.

    Examples:

    <m display="jsmath">$\displaystyle U(r)=4 U_0 </m>
    <m>$r_0$</m>     

    We convert these to [mathjax]...[/mathjax] and [mathjaxinline]...[/mathjaxinline]

    TODO: use shorter tags (but this will require converting problem XML files!)
    '''
    mathstr = re.sub('\$(.*)\$','[mathjaxinline]\\1[/mathjaxinline]',element.text)
    mtag = 'mathjax'
    if not '\\displaystyle' in mathstr: mtag += 'inline'
    else: mathstr = mathstr.replace('\\displaystyle','')
    mathstr = mathstr.replace('mathjaxinline]','%s]'%mtag)

    #if '\\displaystyle' in mathstr:
    #    isinline = False
    #    mathstr = mathstr.replace('\\displaystyle','')
    #else:
    #    isinline = True
    # html = render_template("mathstring.html",{'mathstr':mathstr,'isinline':isinline,'tail':element.tail})

    html = '<html><html>%s</html><html>%s</html></html>' % (mathstr,saxutils.escape(element.tail))
    try:
        xhtml = etree.XML(html)
    except Exception as err:
        if False: # TODO needs to be self.system.DEBUG - but can't access system 
            msg = "<html><font color='red'><p>Error %s</p>" % str(err).replace('<','&lt;')
            msg += '<p>Failed to construct math expression from <pre>%s</pre></p>' % html.replace('<','&lt;')
            msg += "</font></html>"
            log.error(msg)
            return etree.XML(msg)
        else:
            raise
    # xhtml.tail = element.tail	# don't forget to include the tail!
    return xhtml

#-----------------------------------------------------------------------------

@register_render_function
def solution(element, value, status, render_template, msg=''):
    '''
    This is not really an input type.  It is just a <span>...</span> which is given an ID,
    that is used for displaying an extended answer (a problem "solution") after "show answers"
    is pressed.  Note that the solution content is NOT sent with the HTML. It is obtained
    by a JSON call.
    '''
    eid=element.get('id')
    size = element.get('size')
    context = {'id':eid,
               'value':value,
               'state':status,
               'size': size,
               'msg':msg,
               }
    html = render_template("solutionspan.html", context)
    return etree.XML(html)

#-----------------------------------------------------------------------------

@register_render_function
def imageinput(element, value, status, render_template, msg=''):
    '''
    Clickable image as an input field.  Element should specify the image source, height, and width, eg
    <imageinput src="/static/Physics801/Figures/Skier-conservation of energy.jpg"  width="388" height="560" />

    TODO: showanswer for imageimput does not work yet - need javascript to put rectangle over acceptable area of image.

    '''
    eid = element.get('id')
    src = element.get('src')
    height = element.get('height')
    width = element.get('width')

    # if value is of the form [x,y] then parse it and send along coordinates of previous answer
    m = re.match('\[([0-9]+),([0-9]+)]',value.strip().replace(' ',''))
    if m:
        (gx,gy) = [int(x)-15 for x in m.groups()]
    else:
        (gx,gy) = (0,0)
    
    context = {
        'id': eid,
        'value': value,
        'height': height,
        'width': width,
        'src': src,
        'gx': gx,
        'gy': gy,
        'state': status,	# to change
        'msg': msg,			# to change
        }
    html = render_template("imageinput.html", context)
    return etree.XML(html)
