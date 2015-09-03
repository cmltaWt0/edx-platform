/**
 * A custom TabbedView for Teams.
 */
;(function (define) {
    'use strict';

    define([
        'js/components/tabbed/views/tabbed_view',
        'teams/js/utils/team_analytics'
    ], function (TabbedView, TeamAnalytics) {
        var TeamsTabbedView = TabbedView.extend({
            /**
             * Overrides TabbedView.prototype.setActiveTab in order to
             * log page viewed events.
             */
            setActiveTab: function (index) {
                var pageName = (typeof index === 'string') ? this.urlMap[index].url : this.tabs[index].url;
                TabbedView.prototype.setActiveTab.call(this, index);
                TeamAnalytics.emitPageViewed(pageName, null, null);
            }
        });

        return TeamsTabbedView;
    });
}).call(this, define || RequireJS.define);
