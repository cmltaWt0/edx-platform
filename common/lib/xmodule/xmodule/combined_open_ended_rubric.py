import logging
from lxml import etree

log=logging.getLogger(__name__)

class RubricParsingError(Exception):
    pass

class CombinedOpenEndedRubric(object):

    def __init__ (self, system, view_only = False):
        self.has_score = False
        self.view_only = view_only
        self.system = system

    def render_rubric(self, rubric_xml):
        '''
        render_rubric: takes in an xml string and outputs the corresponding
            html for that xml, given the type of rubric we're generating
        Input:
            rubric_xml: an string that has not been parsed into xml that
                represents this particular rubric
        Output:
            html: the html that corresponds to the xml given
        '''
        try:
            rubric_categories = self.extract_categories(rubric_xml)
            html = self.system.render_template('open_ended_rubric.html', 
                    {'categories'  : rubric_categories,
                     'has_score': self.has_score,
                     'view_only': self.view_only})
        except:
            raise RubricParsingError("[render_rubric] Could not parse the rubric with xml: {0}".format(rubric_xml))
        return html

    def extract_categories(self, element):
        '''
        Contstruct a list of categories such that the structure looks like:
        [ { category: "Category 1 Name",
            options: [{text: "Option 1 Name", points: 0}, {text:"Option 2 Name", points: 5}]
            },
           { category: "Category 2 Name",
             options: [{text: "Option 1 Name", points: 0}, 
                         {text: "Option 2 Name", points: 1}, 
                         {text: "Option 3 Name", points: 2]}]

        '''
        if isinstance(element, basestring):
            element = etree.fromstring(element)
        categories = []
        for category in element:
            if category.tag != 'category':
                raise RubricParsingError("[extract_categories] Expected a <category> tag: got {0} instead".format(category.tag))
            else:
                categories.append(self.extract_category(category))
        return categories


    def extract_category(self, category):
        ''' 
        construct an individual category
        {category: "Category 1 Name",
         options: [{text: "Option 1 text", points: 1},
                   {text: "Option 2 text", points: 2}]}

        all sorting and auto-point generation occurs in this function
        '''
        descriptionxml = category[0]
        optionsxml = category[1:]
        scorexml = category[1]
        score = None
        if scorexml.tag == 'score':
            score_text = scorexml.text
            optionsxml = category[2:]
            score = int(score_text)
            self.has_score = True
        # if we are missing the score tag and we are expecting one
        elif self.has_score:
            raise RubricParsingError("[extract_category] Category {0} is missing a score".format(descriptionxml.text))


        # parse description
        if descriptionxml.tag != 'description':
            raise RubricParsingError("[extract_category]: expected description tag, got {0} instead".format(descriptionxml.tag))

        description = descriptionxml.text

        cur_points = 0
        options = []
        autonumbering = True
        # parse options
        for option in optionsxml:
            if option.tag != 'option': 
                raise RubricParsingError("[extract_category]: expected option tag, got {0} instead".format(option.tag))
            else:
                pointstr = option.get("points")
                if pointstr:
                    autonumbering = False
                    # try to parse this into an int
                    try:
                        points = int(pointstr)
                    except ValueError:
                        raise RubricParsingError("[extract_category]: expected points to have int, got {0} instead".format(pointstr))
                elif autonumbering:
                    # use the generated one if we're in the right mode
                    points = cur_points
                    cur_points = cur_points + 1
                else:
                    raise Exception("[extract_category]: missing points attribute. Cannot continue to auto-create points values after a points value is explicitly defined.")
                
                selected = score == points
                optiontext = option.text
                options.append({'text': option.text, 'points': points, 'selected': selected})

        # sort and check for duplicates
        options = sorted(options, key=lambda option: option['points'])
        CombinedOpenEndedRubric.validate_options(options)

        return {'description': description, 'options': options}


    @staticmethod
    def validate_options(options):
        '''
        Validates a set of options. This can and should be extended to filter out other bad edge cases
        '''
        if len(options) == 0:
            raise RubricParsingError("[extract_category]: no options associated with this category")
        if len(options) == 1:
            return
        prev = options[0]['points']
        for option in options[1:]:
            if prev == option['points']:
                raise RubricParsingError("[extract_category]: found duplicate point values between two different options")
            else:
                prev = option['points']
