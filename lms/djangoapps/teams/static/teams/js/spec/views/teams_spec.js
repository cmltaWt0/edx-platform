define([
    'backbone', 'teams/js/collections/team', 'teams/js/views/teams'
], function (Backbone, TeamCollection, TeamsView) {
    'use strict';
    describe('Teams View', function () {
        var teamsView, teamCollection, initialTeams,
            createTeams = function (startIndex, stopIndex) {
                return _.map(_.range(startIndex, stopIndex + 1), function (i) {
                    return {
                        name: "team " + i,
                        id: "id " + i,
                        language: languages[i%4][0],
                        country: countries[i%4][0],
                        is_active: true,
                        membership: []
                    };
                });
            },
            countries = [
                ['', ''],
                ['US', 'United States'],
                ['CA', 'Canada'],
                ['MX', 'Mexico']
            ],
            languages = [
                ['', ''],
                ['en', 'English'],
                ['es', 'Spanish'],
                ['fr', 'French']
            ];

        beforeEach(function () {
            setFixtures('<div class="teams-container"></div>');
            initialTeams = createTeams(1, 5);
            teamCollection = new TeamCollection(
                {
                    count: 6,
                    num_pages: 2,
                    current_page: 1,
                    start: 0,
                    results: initialTeams
                },
                {course_id: 'my/course/id', parse: true}
            );
            teamsView = new TeamsView({
                el: '.teams-container',
                collection: teamCollection,
                teamParams: {
                    countries: countries,
                    languages: languages
                }
            }).render();
        });

        it('can render itself', function () {
            var footerEl = teamsView.$('.teams-paging-footer'),
                teamCards = teamsView.$('.team-card');
            expect(teamsView.$('.teams-paging-header').text()).toMatch('Showing 1-5 out of 6 total');
            _.each(initialTeams, function (team, index) {
                var currentCard = teamCards.eq(index);

                expect(currentCard.text()).toMatch(team.name);
                expect(currentCard.text()).toMatch(_.object(languages)[team.language]);
                expect(currentCard.text()).toMatch(_.object(countries)[team.country]);
            });
            expect(footerEl.text()).toMatch('1\\s+out of\\s+\/\\s+2');
            expect(footerEl).not.toHaveClass('hidden');
        });
    });
});
