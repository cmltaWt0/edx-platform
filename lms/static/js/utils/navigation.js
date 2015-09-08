var edx = edx || {},

    Navigation = (function() {

        var navigation = {

            init: function() {
                if ($('.accordion').length) {
                    navigation.loadAccordion();
                }
            },

            loadAccordion: function() {
                navigation.checkForCurrent();
                navigation.listenForClick();
            },

            getActiveIndex: function() {
                var index = $('.accordion .chapter-content-container:has(.active)').index('.accordion .chapter-content-container'),
                    button = null;

                if (index > -1) {
                    button = $('.accordion .button-chapter:eq(' + index + ')');
                }

                return button;
            },

            checkForCurrent: function() {
                var button = navigation.getActiveIndex();

                navigation.closeAccordions();

                if (button !== null) {
                    navigation.setupCurrentAccordionSection(button);
                }
            },

            listenForClick: function() {
                $('.accordion').on('click', '.button-chapter', function(event) {
                    var button = $(event.currentTarget),
                        section = button.next('.chapter-content-container');

                    navigation.closeAccordions(button, section);
                    navigation.openAccordion(button, section);
                });
            },

            closeAccordions: function(button, section) {
                var menu = $(section).find('.chapter-menu'), toggle;

                $('.accordion .button-chapter').each(function(index, event) {
                    toggle = $(event);

                    toggle
                        .removeClass('is-open')
                        .attr('aria-expanded', 'false');

                    toggle
                        .children('.group-heading')
                        .removeClass('active')
                        .find('.icon')
                            .addClass('fa-caret-right')
                            .removeClass('fa-caret-down');

                    toggle
                        .next('.chapter-content-container')
                        .removeClass('is-open')
                        .find('.chapter-menu').not(menu)
                            .removeClass('is-open')
                            .slideUp();
                });
            },

            setupCurrentAccordionSection: function(button) {
                var section = $(button).next('.chapter-content-container');

                navigation.openAccordion(button, section);
            },

            openAccordion: function(button, section) {
                var sectionEl = $(section),
                    buttonEl = $(button);

                buttonEl
                    .addClass('is-open')
                    .attr('aria-expanded', 'true');

                buttonEl
                    .children('.group-heading')
                    .addClass('active')
                    .find('.icon')
                        .removeClass('fa-caret-right')
                        .addClass('fa-caret-down');

                sectionEl
                    .addClass('is-open')
                    .find('.chapter-menu')
                        .addClass('is-open')
                        .slideDown();

                sectionEl.focus();
            }
        };

        return {
            init: navigation.init
        };

    })();

    edx.util = edx.util || {};
    edx.util.navigation = Navigation;
    edx.util.navigation.init();
