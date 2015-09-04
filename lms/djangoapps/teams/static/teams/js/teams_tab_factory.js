;(function (define) {
    'use strict';
    define([
        'jquery',
        'underscore',
        'backbone',
        'gettext',
        'teams/js/views/teams_tab',
        'teams/js/views/team_utils'
    ], function ($, _, Backbone, gettext, TeamsTabView, TeamUtils) {
            return function (options) {
                var teamsTab = new TeamsTabView({
                    el: $('.teams-content'),
                    context: options
                });
                $(document).ajaxError(function (event, xhr) {
                    if (_.contains([401, 500], xhr.status)) {
                        TeamUtils.showMessage(gettext("Your request could not be completed. Reload the page and try again."));
                    }
                });
                teamsTab.start();
            };
        });
}).call(this, define || RequireJS.define);
