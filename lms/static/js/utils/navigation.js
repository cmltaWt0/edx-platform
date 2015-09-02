var edx = edx || {},

    Navigation = (function() {

        var navigation = {

            init: function() {

                if ($('.accordion').length) {

                    navigation.openAccordion();
                }
            },

            openAccordion: function() {
                navigation.checkForCurrent();
                navigation.listenForClick();
            },

            checkForCurrent: function() {
                var active = $('.accordion .chapter-content-container:has(.active)').index('.accordion .chapter-content-container') ? $('.accordion .chapter-content-container:has(.active)').index('.accordion .chapter-content-container') : 0,
                    activeSection = $('.accordion .button-chapter:eq(' + active + ')');

                navigation.closeAccordions();
                navigation.openAccordionSection(activeSection);
            },

            listenForClick: function() {
                $('.accordion').on('click', '.button-chapter', function(event) {
                    navigation.closeAccordions();
                    navigation.openAccordionSection(event.currentTarget);
                });
            },

            closeAccordions: function() {
                $('.chapter-content-container').hide();

                $('.accordion .button-chapter').each(function(event) {
                    var el = $(this);

                    el.removeClass('is-open').attr('aria-expanded', 'false');
                    el.next('.chapter-content-container').attr('aria-expanded', 'false');
                    el.children('.group-heading').removeClass('active');
                    el.children('.group-heading').find('.icon').addClass('fa-caret-right').removeClass('fa-caret-down');
                });
            },

            openAccordionSection: function(section) {
                var elSection = $(section).next('.chapter-content-container');

                elSection.show().focus();

                $(section).addClass('is-open').attr('aria-expanded', 'true');
                $(section).next('.chapter-content-container').attr('aria-expanded', 'true');
                $(section).children('.group-heading').addClass('active');
                $(section).children('.group-heading').find('.icon').removeClass('fa-caret-right').addClass('fa-caret-down');
            }
        };

        return {
            init: navigation.init
        };

    })();

    edx.util = edx.util || {};
    edx.util.navigation = Navigation;
    edx.util.navigation.init();
