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
                    navigation.closeAccordions(event.currentTarget);
                    navigation.openAccordionSection(event.currentTarget);
                });
            },

            closeAccordions: function(button) {
                var menu = $(button).next('.chapter-content-container').find('.chapter-menu');
                console.log(button, menu);

                $('.accordion .button-chapter').each(function(event) {
                    var el = $(this);

                    el.removeClass('is-open').attr('aria-expanded', 'false');
                    el.children('.group-heading').removeClass('active');
                    el.children('.group-heading').find('.icon').addClass('fa-caret-right').removeClass('fa-caret-down');

                    el.next('.chapter-content-container').removeClass('is-open');
                    el.next('.chapter-content-container').find('.chapter-menu').not(menu).slideUp();
                });
            },

            openAccordionSection: function(section) {
                var elSection = $(section).next('.chapter-content-container');

                $(section).addClass('is-open').attr('aria-expanded', 'true');
                $(section).children('.group-heading').addClass('active');
                $(section).children('.group-heading').find('.icon').removeClass('fa-caret-right').addClass('fa-caret-down');

                elSection.find('.chapter-menu').slideDown();
                elSection.addClass('is-open').focus();
            }
        };

        return {
            init: navigation.init
        };

    })();

    edx.util = edx.util || {};
    edx.util.navigation = Navigation;
    edx.util.navigation.init();
