define([
    'jquery',
    'backbone',
    'logger',
    'common/js/spec_helpers/ajax_helpers',
    'teams/js/views/teams_tab',
    'teams/js/spec_helpers/team_spec_helpers'
], function ($, Backbone, Logger, AjaxHelpers, TeamsTabView, TeamSpecHelpers) {
    'use strict';

    describe('TeamsTab', function () {
        var expectError = function (teamsTabView, text) {
            expect(teamsTabView.$('.warning').text()).toContain(text);
        };

        var expectFocus = function (element) {
            expect(element.focus).toHaveBeenCalled();
        };

        var createTeamsTabView = function(options) {
            var defaultTopics = {
                    count: 5,
                    num_pages: 1,
                    current_page: 1,
                    start: 0,
                    results: TeamSpecHelpers.createMockTopicData(1, 5)
                },
                teamsTabView = new TeamsTabView(
                    {
                        el: $('.teams-content'),
                        context: TeamSpecHelpers.createMockContext(options)
                    }
                );
            teamsTabView.start();
            return teamsTabView;
        };

        var verifyTeamsRequest = function(requests, queryParams) {
            AjaxHelpers.expectRequestURL(requests, TeamSpecHelpers.testContext.teamsUrl,
                                         _.extend(
                                             {
                                                 topic_id: TeamSpecHelpers.testTopicID,
                                                 expand: 'user',
                                                 course_id: TeamSpecHelpers.testCourseID,
                                                 order_by: '',
                                                 page: '1',
                                                 page_size: '10',
                                                 text_search: ''
                                             },
                                             queryParams
                                         ));
        };

        /**
         * Filters out all team events from a list of requests.
         */
        var removeTeamEvents = function (requests) {
            return requests.filter(function (request) {
                if (request.requestBody && request.requestBody.startsWith('event_type=edx.team')) {
                    return false;
                } else {
                    return true;
                }
            });
        };

        beforeEach(function () {
            setFixtures('<div class="teams-content"></div>');
            spyOn($.fn, 'focus');
            spyOn(Logger, 'log');
        });

        afterEach(function () {
            Backbone.history.stop();
        });

        describe('Navigation', function () {
            it('does not interfere with anchor links to #content', function () {
                var teamsTabView = createTeamsTabView();
                teamsTabView.router.navigate('#content', {trigger: true});
                expect(teamsTabView.$('.warning')).toHaveClass('is-hidden');
            });

            it('displays and focuses an error message when trying to navigate to a nonexistent page', function () {
                var teamsTabView = createTeamsTabView();
                teamsTabView.router.navigate('no_such_page', {trigger: true});
                expectError(teamsTabView, 'The page "no_such_page" could not be found.');
                expectFocus(teamsTabView.$('.warning'));
            });

            it('displays and focuses an error message when trying to navigate to a nonexistent topic', function () {
                var requests = AjaxHelpers.requests(this),
                    teamsTabView = createTeamsTabView();
                teamsTabView.router.navigate('topics/no_such_topic', {trigger: true});
                AjaxHelpers.expectRequest(requests, 'GET', '/api/team/v0/topics/no_such_topic,course/1', null);
                AjaxHelpers.respondWithError(requests, 404);
                expectError(teamsTabView, 'The topic "no_such_topic" could not be found.');
                expectFocus(teamsTabView.$('.warning'));
            });

            it('displays and focuses an error message when trying to navigate to a nonexistent team', function () {
                var requests = AjaxHelpers.requests(this),
                    teamsTabView = createTeamsTabView();
                teamsTabView.router.navigate('teams/' + TeamSpecHelpers.testTopicID + '/no_such_team', {trigger: true});
                AjaxHelpers.expectRequest(requests, 'GET', '/api/team/v0/teams/no_such_team?expand=user', null);
                AjaxHelpers.respondWithError(requests, 404);
                expectError(teamsTabView, 'The team "no_such_team" could not be found.');
                expectFocus(teamsTabView.$('.warning'));
            });
        });

        describe('Analytics Events', function () {
            beforeEach(function () {
            //    TODO: createTeamsTabView, navigate to browse teams page...
            });
            it('fires a page view event for the topic page', function () {
                var requests = AjaxHelpers.requests(this),
                    teamsTabView = createTeamsTabView();
                teamsTabView.router.navigate('topics/' + TeamSpecHelpers.testTopicID, {trigger: true});
                AjaxHelpers.respondWithJson(requests, {});
                expect(Logger.log).toHaveBeenCalledWith('edx.team.page_viewed', {
                    page_name: 'single-topic',
                    topic_id: TeamSpecHelpers.testTopicID,
                    team_id: null
                });
            });

            it('fires a page view event for the team page', function () {
                var requests = AjaxHelpers.requests(this),
                    teamsTabView = createTeamsTabView(),
                    team_id = 'test_team_id';
                teamsTabView.router.navigate('teams/' + TeamSpecHelpers.testTopicID + '/' + team_id, {trigger: true});
                AjaxHelpers.respondWithJson(requests, {});
                expect(Logger.log).toHaveBeenCalledWith('edx.team.page_viewed', {
                    page_name: 'single-team',
                    topic_id: TeamSpecHelpers.testTopicID,
                    team_id: team_id
                });
            });

            it('fires a page view event for the search team page', function () {
                var requests = AjaxHelpers.requests(this),
                    teamsTabView = createTeamsTabView();
                teamsTabView.browseTopic(TeamSpecHelpers.testTopicID);
                teamsTabView.router.navigate('topics/' + TeamSpecHelpers.testTopicID + '/search', {trigger: true});
                AjaxHelpers.respondWithJson(requests, {});
                expect(Logger.log).toHaveBeenCalledWith('edx.team.page_viewed', {
                    page_name: 'search-teams',
                    topic_id: TeamSpecHelpers.testTopicID,
                    team_id: null
                });
            });

            it('fires a page view event for the new team page', function () {
                var teamsTabView = createTeamsTabView();
                teamsTabView.router.navigate('topics/' + TeamSpecHelpers.testTopicID + '/create-team', {trigger: true});
                expect(Logger.log).toHaveBeenCalledWith('edx.team.page_viewed', {
                    page_name: 'new-team',
                    topic_id: TeamSpecHelpers.testTopicID,
                    team_id: null
                });
            });

            it('fires a page view event for the edit team page', function () {
                var requests = AjaxHelpers.requests(this),
                    teamsTabView = createTeamsTabView(),
                    team_id = 'test_team_id';
                teamsTabView.router.navigate('topics/' + TeamSpecHelpers.testTopicID + '/' + team_id + '/edit-team', {
                    trigger: true
                });
                AjaxHelpers.respondWithJson(requests, {});
                expect(Logger.log).toHaveBeenCalledWith('edx.team.page_viewed', {
                    page_name: 'edit-team',
                    topic_id: TeamSpecHelpers.testTopicID,
                    team_id: team_id
                });
            });
        });

        describe('Discussion privileges', function () {
            it('allows privileged access to any team', function () {
                var teamsTabView = createTeamsTabView({
                    userInfo: TeamSpecHelpers.createMockUserInfo({ privileged: true })
                });
                // Note: using `undefined` here to ensure that we
                // don't even look at the team when the user is
                // privileged
                expect(teamsTabView.readOnlyDiscussion(undefined)).toBe(false);
            });

            it('allows access to a team which an unprivileged user is a member of', function () {
                var teamsTabView = createTeamsTabView({
                    userInfo: TeamSpecHelpers.createMockUserInfo({
                        username: TeamSpecHelpers.testUser,
                        privileged: false
                    })
                });
                expect(teamsTabView.readOnlyDiscussion({
                    attributes: {
                        membership: [{
                            user: {
                                username: TeamSpecHelpers.testUser
                            }
                        }]
                    }
                })).toBe(false);
            });

            it('does not allow access if the user is neither privileged nor a team member', function () {
                var teamsTabView = createTeamsTabView({
                    userInfo: TeamSpecHelpers.createMockUserInfo({ privileged: false, staff: true })
                });
                expect(teamsTabView.readOnlyDiscussion({
                    attributes: { membership: [] }
                })).toBe(true);
            });
        });

        describe('Search', function () {
            it('can search teams', function () {
                var requests = AjaxHelpers.requests(this),
                    teamsTabView = createTeamsTabView();
                teamsTabView.browseTopic(TeamSpecHelpers.testTopicID);
                verifyTeamsRequest(requests, {
                    order_by: 'last_activity_at',
                    text_search: ''
                });
                AjaxHelpers.respondWithJson(requests, {});
                teamsTabView.$('.search-field').val('foo');
                teamsTabView.$('.action-search').click();
                verifyTeamsRequest(requests, {
                    order_by: '',
                    text_search: 'foo'
                });
                AjaxHelpers.respondWithJson(requests, {});
                expect(teamsTabView.$('.page-title').text()).toBe('Team Search');
                expect(teamsTabView.$('.page-description').text()).toBe('Showing results for "foo"');
            });

            it('can clear a search', function () {
                var requests = AjaxHelpers.requests(this),
                    teamsTabView = createTeamsTabView();
                teamsTabView.browseTopic(TeamSpecHelpers.testTopicID);
                AjaxHelpers.respondWithJson(requests, {});

                // Perform a search
                teamsTabView.$('.search-field').val('foo');
                teamsTabView.$('.action-search').click();
                AjaxHelpers.respondWithJson(requests, {});

                // Clear the search and submit it again
                teamsTabView.$('.search-field').val('');
                teamsTabView.$('.action-search').click();
                verifyTeamsRequest(requests, {
                    order_by: 'last_activity_at',
                    text_search: ''
                });
                AjaxHelpers.respondWithJson(requests, {});
                expect(teamsTabView.$('.page-title').text()).toBe('Test Topic 1');
                expect(teamsTabView.$('.page-description').text()).toBe('Test description 1');
            });

            it('clears the search when navigating away and then back', function () {
                var requests = AjaxHelpers.requests(this),
                    teamsTabView = createTeamsTabView();
                teamsTabView.browseTopic(TeamSpecHelpers.testTopicID);
                AjaxHelpers.respondWithJson(requests, {});

                // Perform a search
                teamsTabView.$('.search-field').val('foo');
                teamsTabView.$('.action-search').click();
                AjaxHelpers.respondWithJson(requests, {});

                // Navigate back to the teams list
                teamsTabView.$('.breadcrumbs a').last().click();
                verifyTeamsRequest(removeTeamEvents(requests), {
                    order_by: 'last_activity_at',
                    text_search: ''
                });
                AjaxHelpers.respondWithJson(requests, {});
                expect(teamsTabView.$('.page-title').text()).toBe('Test Topic 1');
                expect(teamsTabView.$('.page-description').text()).toBe('Test description 1');
            });

            it('does not switch to showing results when the search returns an error', function () {
                var requests = AjaxHelpers.requests(this),
                    teamsTabView = createTeamsTabView();
                teamsTabView.browseTopic(TeamSpecHelpers.testTopicID);
                AjaxHelpers.respondWithJson(requests, {});

                // Perform a search
                teamsTabView.$('.search-field').val('foo');
                teamsTabView.$('.action-search').click();
                AjaxHelpers.respondWithError(requests);
                expect(teamsTabView.$('.page-title').text()).toBe('Test Topic 1');
                expect(teamsTabView.$('.page-description').text()).toBe('Test description 1');
                expect(teamsTabView.$('.search-field').val(), 'foo');
            });
        });
    });
});
