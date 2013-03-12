from lettuce import world, step
from common import *
import time
from terrain.steps import reload_the_page
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support import expected_conditions as EC

from nose.tools import assert_true, assert_false, assert_equal

"""
http://selenium.googlecode.com/svn/trunk/docs/api/py/webdriver/selenium.webdriver.common.keys.html
"""
from selenium.webdriver.common.keys import Keys

KEY_CSS = '.key input.policy-key'
VALUE_CSS = 'textarea.json'
DISPLAY_NAME_KEY = "display_name"
DISPLAY_NAME_VALUE = '"Robot Super Course"'

############### ACTIONS ####################
@step('I select the Advanced Settings$')
def i_select_advanced_settings(step):
    expand_icon_css = 'li.nav-course-settings i.icon-expand'
    if world.browser.is_element_present_by_css(expand_icon_css):
        css_click(expand_icon_css)
    link_css = 'li.nav-course-settings-advanced a'
    css_click(link_css)


@step('I am on the Advanced Course Settings page in Studio$')
def i_am_on_advanced_course_settings(step):
    step.given('I have opened a new course in Studio')
    step.given('I select the Advanced Settings')


@step(u'I press the "([^"]*)" notification button$')
def press_the_notification_button(step, name):
    def is_visible(driver):
        return EC.visibility_of_element_located((By.CSS_SELECTOR, css,))

    #    def is_invisible(driver):
    #        return EC.invisibility_of_element_located((By.CSS_SELECTOR,css,))

    css = 'a.%s-button' % name.lower()
    wait_for(is_visible)
    time.sleep(float(1))
    css_click_at(css)

#   is_invisible is not returning a boolean, not working
#    try:
#        css_click_at(css)
#        wait_for(is_invisible)
#    except WebDriverException, e:
#        css_click_at(css)
#        wait_for(is_invisible)


@step(u'I edit the value of a policy key$')
def edit_the_value_of_a_policy_key(step):
    """
    It is hard to figure out how to get into the CodeMirror
    area, so cheat and do it from the policy key field :)
    """
    e = css_find(KEY_CSS)[get_index_of(DISPLAY_NAME_KEY)]
    e._element.send_keys(Keys.TAB, Keys.END, Keys.ARROW_LEFT, ' ', 'X')


@step('I create a JSON object as a value$')
def create_JSON_object(step):
    change_display_name_value(step, '{"key": "value", "key_2": "value_2"}')


@step('I create a non-JSON value not in quotes$')
def create_value_not_in_quotes(step):
    change_display_name_value(step, 'quote me')


############### RESULTS ####################
@step('I see default advanced settings$')
def i_see_default_advanced_settings(step):
    # Test only a few of the existing properties (there are around 34 of them)
    assert_policy_entries(
        ["advanced_modules", DISPLAY_NAME_KEY, "show_calculator"], ["[]", DISPLAY_NAME_VALUE, "false"])


@step('the settings are alphabetized$')
def they_are_alphabetized(step):
    key_elements = css_find(KEY_CSS)
    all_keys = []
    for key in key_elements:
        all_keys.append(key.value)

    assert_equal(sorted(all_keys), all_keys, "policy keys were not sorted")


@step('it is displayed as formatted$')
def it_is_formatted(step):
    assert_policy_entries([DISPLAY_NAME_KEY], ['{\n    "key": "value",\n    "key_2": "value_2"\n}'])


@step('it is displayed as a string')
def it_is_formatted(step):
    assert_policy_entries([DISPLAY_NAME_KEY], ['"quote me"'])


@step(u'the policy key value is unchanged$')
def the_policy_key_value_is_unchanged(step):
    assert_equal(get_display_name_value(), DISPLAY_NAME_VALUE)


@step(u'the policy key value is changed$')
def the_policy_key_value_is_changed(step):
    assert_equal(get_display_name_value(), '"Robot Super Course X"')


############# HELPERS ###############
def assert_policy_entries(expected_keys, expected_values):
    for counter in range(len(expected_keys)):
        index = get_index_of(expected_keys[counter])
        assert_false(index == -1, "Could not find key: " + expected_keys[counter])
        assert_equal(expected_values[counter], css_find(VALUE_CSS)[index].value, "value is incorrect")


def get_index_of(expected_key):
    for counter in range(len(css_find(KEY_CSS))):
        #   Sometimes get stale reference if I hold on to the array of elements
        key = css_find(KEY_CSS)[counter].value
        if key == expected_key:
            return counter

    return -1


def get_display_name_value():
    index = get_index_of(DISPLAY_NAME_KEY)
    return css_find(VALUE_CSS)[index].value


def change_display_name_value(step, new_value):
    e = css_find(KEY_CSS)[get_index_of(DISPLAY_NAME_KEY)]
    display_name = get_display_name_value()
    for count in range(len(display_name)):
        e._element.send_keys(Keys.TAB, Keys.END, Keys.BACK_SPACE)
        # Must delete "" before typing the JSON value
    e._element.send_keys(Keys.TAB, Keys.END, Keys.BACK_SPACE, Keys.BACK_SPACE, new_value)
    press_the_notification_button(step, "Save")