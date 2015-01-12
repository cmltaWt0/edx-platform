"""
Acceptance tests for Content Libraries in Studio
"""
from ddt import ddt, data

from .base_studio_test import StudioLibraryTest
from ...fixtures.course import XBlockFixtureDesc
from ...pages.studio.utils import add_component
from ...pages.studio.library import LibraryPage


@ddt
class LibraryEditPageTest(StudioLibraryTest):
    """
    Test the functionality of the library edit page.
    """
    def setUp(self):  # pylint: disable=arguments-differ
        """
        Ensure a library exists and navigate to the library edit page.
        """
        super(LibraryEditPageTest, self).setUp()
        self.lib_page = LibraryPage(self.browser, self.library_key)
        self.lib_page.visit()
        self.lib_page.wait_until_ready()

    def test_page_header(self):
        """
        Scenario: Ensure that the library's name is displayed in the header and title.
        Given I have a library in Studio
        And I navigate to Library Page in Studio
        Then I can see library name in page header title
        And I can see library name in browser page title
        """
        self.assertIn(self.library_info['display_name'], self.lib_page.get_header_title())
        self.assertIn(self.library_info['display_name'], self.browser.title)

    def test_add_duplicate_delete_actions(self):
        """
        Scenario: Ensure that we can add an HTML block, duplicate it, then delete the original.
        Given I have a library in Studio with no XBlocks
        And I navigate to Library Page in Studio
        Then there are no XBlocks displayed
        When I add Text XBlock
        Then one XBlock is displayed
        When I duplicate first XBlock
        Then two XBlocks are displayed
        And those XBlocks locators' are different
        When I delete first XBlock
        Then one XBlock is displayed
        And displayed XBlock are second one
        """
        self.assertEqual(len(self.lib_page.xblocks), 0)

        # Create a new block:
        add_component(self.lib_page, "html", "Text")
        self.assertEqual(len(self.lib_page.xblocks), 1)
        first_block_id = self.lib_page.xblocks[0].locator

        # Duplicate the block:
        self.lib_page.click_duplicate_button(first_block_id)
        self.assertEqual(len(self.lib_page.xblocks), 2)
        second_block_id = self.lib_page.xblocks[1].locator
        self.assertNotEqual(first_block_id, second_block_id)

        # Delete the first block:
        self.lib_page.click_delete_button(first_block_id, confirm=True)
        self.assertEqual(len(self.lib_page.xblocks), 1)
        self.assertEqual(self.lib_page.xblocks[0].locator, second_block_id)

    def test_add_edit_xblock(self):
        """
        Scenario: Ensure that we can add an XBlock, edit it, then see the resulting changes.
        Given I have a library in Studio with no XBlocks
        And I navigate to Library Page in Studio
        Then there are no XBlocks displayed
        When I add Multiple Choice XBlock
        Then one XBlock is displayed
        When I edit first XBlock
        And I go to basic tab
        And set it's text to a fairly trivial question about Battlestar Galactica
        And save XBlock
        Then one XBlock is displayed
        And first XBlock student content contains at least part of text I set
        """
        self.assertEqual(len(self.lib_page.xblocks), 0)
        # Create a new problem block:
        add_component(self.lib_page, "problem", "Multiple Choice")
        self.assertEqual(len(self.lib_page.xblocks), 1)
        problem_block = self.lib_page.xblocks[0]
        # Edit it:
        problem_block.edit()
        problem_block.open_basic_tab()
        problem_block.set_codemirror_text(
            """
            >>Who is "Starbuck"?<<
             (x) Kara Thrace
             ( ) William Adama
             ( ) Laura Roslin
             ( ) Lee Adama
             ( ) Gaius Baltar
            """
        )
        problem_block.save_settings()
        # Check that the save worked:
        self.assertEqual(len(self.lib_page.xblocks), 1)
        problem_block = self.lib_page.xblocks[0]
        self.assertIn("Laura Roslin", problem_block.student_content)

    def test_no_discussion_button(self):
        """
        Ensure the UI is not loaded for adding discussions.
        """
        self.assertFalse(self.browser.find_elements_by_css_selector('span.large-discussion-icon'))

    def test_library_pagination(self):
        """
        Scenario: Ensure that adding several XBlocks to a library results in pagination.
        Given that I have a library in Studio with no XBlocks
        And I create 10 Multiple Choice XBlocks
        Then 10 are displayed.
        When I add one more Multiple Choice XBlock
        Then 1 XBlock will be displayed
        When I delete that XBlock
        Then 10 are displayed.
        """
        self.assertEqual(len(self.lib_page.xblocks), 0)
        for _ in range(0, 10):
            add_component(self.lib_page, "problem", "Multiple Choice")
        self.assertEqual(len(self.lib_page.xblocks), 10)
        add_component(self.lib_page, "problem", "Multiple Choice")
        self.assertEqual(len(self.lib_page.xblocks), 1)
        self.lib_page.click_delete_button(self.lib_page.xblocks[0].locator)
        self.assertEqual(len(self.lib_page.xblocks), 10)

    @data('top', 'bottom')
    def test_nav_present_but_disabled(self, position):
        """
        Scenario: Ensure that the navigation buttons aren't active when there aren't enough XBlocks.
        Given that I have a library in Studio with no XBlocks
        The Navigation buttons should be disabled.
        When I add a multiple choice problem
        The Navigation buttons should be disabled.
        """
        self.assertEqual(len(self.lib_page.xblocks), 0)
        self.assertTrue(self.lib_page.nav_disabled(position))
        add_component(self.lib_page, "problem", "Multiple Choice")
        self.assertTrue(self.lib_page.nav_disabled(position))


@ddt
class LibraryNavigationTest(StudioLibraryTest):
    """
    Test common Navigation actions
    """
    def setUp(self):  # pylint: disable=arguments-differ
        """
        Ensure a library exists and navigate to the library edit page.
        """
        super(LibraryNavigationTest, self).setUp()
        self.lib_page = LibraryPage(self.browser, self.library_key)
        self.lib_page.visit()
        self.lib_page.wait_until_ready()

    def populate_library_fixture(self, library_fixture):
        """
        Create four pages worth of XBlocks, and offset by one so each is named
        after the number they should be in line by the user's perception.
        """
        # pylint: disable=attribute-defined-outside-init
        self.blocks = [XBlockFixtureDesc('html', str(i)) for i in xrange(1, 41)]
        library_fixture.add_children(*self.blocks)

    def test_arbitrary_page_selection(self):
        """
        Scenario: I can pick a specific page number of a Library at will.
        Given that I have a library in Studio with 40 XBlocks
        When I go to the 3rd page
        The first XBlock should be the 21st XBlock
        When I go to the 4th Page
        The first XBlock should be the 31st XBlock
        When I go to the 1st page
        The first XBlock should be the 1st XBlock
        When I go to the 2nd page
        The first XBlock should be the 11th XBlock
        """
        self.lib_page.go_to_page(3)
        self.assertEqual(self.lib_page.xblocks[0].name, '21')
        self.lib_page.go_to_page(4)
        self.assertEqual(self.lib_page.xblocks[0].name, '31')
        self.lib_page.go_to_page(1)
        self.assertEqual(self.lib_page.xblocks[0].name, '1')
        self.lib_page.go_to_page(2)
        self.assertEqual(self.lib_page.xblocks[0].name, '11')

    def test_bogus_page_selection(self):
        """
        Scenario: I can't pick a nonsense page number of a Library
        Given that I have a library in Studio with 40 XBlocks
        When I attempt to go to the 'a'th page
        The input field will be cleared and no change of XBlocks will be made
        When I attempt to visit the 5th page
        The input field will be cleared and no change of XBlocks will be made
        When I attempt to visit the -1st page
        The input field will be cleared and no change of XBlocks will be made
        When I attempt to visit the 0th page
        The input field will be cleared and no change of XBlocks will be made
        """
        self.assertEqual(self.lib_page.xblocks[0].name, '1')
        self.lib_page.go_to_page('a')
        self.assertTrue(self.lib_page.check_page_unchanged('1'))
        self.lib_page.go_to_page(-1)
        self.assertTrue(self.lib_page.check_page_unchanged('1'))
        self.lib_page.go_to_page(5)
        self.assertTrue(self.lib_page.check_page_unchanged('1'))
        self.lib_page.go_to_page(0)
        self.assertTrue(self.lib_page.check_page_unchanged('1'))

    @data('top', 'bottom')
    def test_nav_buttons(self, position):
        """
        Scenario: Ensure that the navigation buttons work.
        Given that I have a library in Studio with 40 XBlocks
        The previous button should be disabled.
        The first XBlock should be the 1st XBlock
        Then if I hit the next button
        The first XBlock should be the 11th XBlock
        Then if I hit the next button
        The first XBlock should be the 21st XBlock
        Then if I hit the next button
        The first XBlock should be the 31st XBlock
        And the next button should be disabled
        Then if I hit the previous button
        The first XBlock should be the 21st XBlock
        Then if I hit the previous button
        The first XBlock should be the 11th XBlock
        Then if I hit the previous button
        The first XBlock should be the 1st XBlock
        And the previous button should be disabled
        """
        # Check forward navigation
        self.assertTrue(self.lib_page.nav_disabled(position, ['previous']))
        self.assertEqual(self.lib_page.xblocks[0].name, '1')
        self.lib_page.move_forward(position)
        self.assertEqual(self.lib_page.xblocks[0].name, '11')
        self.lib_page.move_forward(position)
        self.assertEqual(self.lib_page.xblocks[0].name, '21')
        self.lib_page.move_forward(position)
        self.assertEqual(self.lib_page.xblocks[0].name, '31')
        self.lib_page.nav_disabled(position, ['next'])

        # Check backward navigation
        self.lib_page.move_back(position)
        self.assertEqual(self.lib_page.xblocks[0].name, '21')
        self.lib_page.move_back(position)
        self.assertEqual(self.lib_page.xblocks[0].name, '11')
        self.lib_page.move_back(position)
        self.assertEqual(self.lib_page.xblocks[0].name, '1')
        self.assertTrue(self.lib_page.nav_disabled(position, ['previous']))

    def test_library_pagination(self):
        """
        Scenario: Ensure that adding several XBlocks to a library results in pagination.
        Given that I have a library in Studio with 40 XBlocks
        Then 10 are displayed
        And the first XBlock will be the 1st one
        And I'm on the 1st page
        When I add 1 Multiple Choice XBlock
        Then 1 XBlock will be displayed
        And I'm on the 5th page
        The first XBlock will be the newest one
        When I delete that XBlock
        Then 10 are displayed
        And I'm on the 4th page
        And the first XBlock is the 31st one
        And the last XBlock is the 40th one.
        """
        self.assertEqual(len(self.lib_page.xblocks), 10)
        self.assertEqual(self.lib_page.get_page_number(), '1')
        self.assertEqual(self.lib_page.xblocks[0].name, '1')
        add_component(self.lib_page, "problem", "Multiple Choice")
        self.assertEqual(len(self.lib_page.xblocks), 1)
        self.assertEqual(self.lib_page.get_page_number(), '5')
        self.assertEqual(self.lib_page.xblocks[0].name, "Multiple Choice")
        self.lib_page.click_delete_button(self.lib_page.xblocks[0].locator)
        self.assertEqual(len(self.lib_page.xblocks), 10)
        self.assertEqual(self.lib_page.get_page_number(), '4')
        self.assertEqual(self.lib_page.xblocks[0].name, '31')
        self.assertEqual(self.lib_page.xblocks[-1].name, '40')

    def test_delete_shifts_blocks(self):
        """
        Scenario: Ensure that removing an XBlock shifts other blocks back.
        Given that I have a library in Studio with 40 XBlocks
        Then 10 are displayed
        And I will be on the first page
        When I delete the third XBlock
        There will be 10 displayed
        And the first XBlock will be the first one
        And the last XBlock will be the 11th one
        And I will be on the first page
        """
        self.assertEqual(len(self.lib_page.xblocks), 10)
        self.assertEqual(self.lib_page.get_page_number(), '1')
        self.lib_page.click_delete_button(self.lib_page.xblocks[2].locator, confirm=True)
        self.assertEqual(len(self.lib_page.xblocks), 10)
        self.assertEqual(self.lib_page.xblocks[0].name, '1')
        self.assertEqual(self.lib_page.xblocks[-1].name, '11')
        self.assertEqual(self.lib_page.get_page_number(), '1')
