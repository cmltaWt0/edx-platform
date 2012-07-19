from django.conf import settings
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin
from django.conf.urls.static import static

import django.contrib.auth.views

# Uncomment the next two lines to enable the admin:
if settings.DEBUG:
    from django.contrib import admin
    admin.autodiscover()

urlpatterns = ('',
    url(r'^$', 'student.views.index', name="root"), # Main marketing page, or redirect to courseware
    url(r'^dashboard$', 'student.views.dashboard', name="dashboard"),
    url(r'^change_email$', 'student.views.change_email_request'),
    url(r'^email_confirm/(?P<key>[^/]*)$', 'student.views.confirm_email_change'),
    url(r'^change_name$', 'student.views.change_name_request'),
    url(r'^accept_name_change$', 'student.views.accept_name_change'),
    url(r'^reject_name_change$', 'student.views.reject_name_change'),
    url(r'^pending_name_changes$', 'student.views.pending_name_changes'),
    url(r'^gradebook$', 'courseware.views.gradebook'),
    url(r'^event$', 'track.views.user_track'),
    url(r'^t/(?P<template>[^/]*)$', 'static_template_view.views.index'),
    url(r'^login$', 'student.views.login_user'),
    url(r'^login/(?P<error>[^/]*)$', 'student.views.login_user'),
    url(r'^logout$', 'student.views.logout_user', name='logout'),
    url(r'^create_account$', 'student.views.create_account'),
    url(r'^activate/(?P<key>[^/]*)$', 'student.views.activate_account'),
#    url(r'^reactivate/(?P<key>[^/]*)$', 'student.views.reactivation_email'),
    url(r'^password_reset/$', 'student.views.password_reset'),
    ## Obsolete Django views for password resets
    ## TODO: Replace with Mako-ized views
    url(r'^password_change/$', django.contrib.auth.views.password_change,
        name='auth_password_change'),
    url(r'^password_change_done/$', django.contrib.auth.views.password_change_done,
        name='auth_password_change_done'),
    url(r'^password_reset_confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        django.contrib.auth.views.password_reset_confirm,
        name='auth_password_reset_confirm'),
    url(r'^password_reset_complete/$', django.contrib.auth.views.password_reset_complete,
        name='auth_password_reset_complete'),
    url(r'^password_reset_done/$', django.contrib.auth.views.password_reset_done,
        name='auth_password_reset_done'),
    ## Feedback
    url(r'^send_feedback$', 'util.views.send_feedback'),
    
    
    
    #Semi-static views (these need to be rendered and have the login bar, but don't change)
    url(r'^404$', 'static_template_view.views.render', 
        {'template': '404.html'}, name="404"),
    url(r'^about$', 'static_template_view.views.render', 
        {'template': 'about.html'}, name="about_edx"),
    url(r'^jobs$', 'static_template_view.views.render', 
        {'template': 'jobs.html'}, name="jobs"),
    url(r'^contact$', 'static_template_view.views.render', 
        {'template': 'contact.html'}, name="contact"),
    url(r'^press$', 'static_template_view.views.render', 
        {'template': 'press.html'}, name="press"),
    url(r'^faq$', 'static_template_view.views.render', 
        {'template': 'faq.html'}, name="faq_edx"),
    url(r'^help$', 'static_template_view.views.render', 
        {'template': 'help.html'}, name="help_edx"),
    url(r'^pressrelease$', 'static_template_view.views.render', 
        {'template': 'pressrelease.html'}, name="pressrelease"),
    url(r'^tos$', 'static_template_view.views.render', 
        {'template': 'tos.html'}, name="tos"),
    url(r'^privacy$', 'static_template_view.views.render', 
        {'template': 'privacy.html'}, name="privacy_edx"),
    url(r'^copyright$', 'static_template_view.views.render', 
        {'template': 'copyright.html'}, name="copyright"),
    url(r'^honor$', 'static_template_view.views.render', 
        {'template': 'honor.html'}, name="honor"),
    
    
    
    #Temporarily static, for testing
    url(r'^university_profile$', 'static_template_view.views.render', 
        {'template': 'university_profile.html'}, name="university_profile"),
    
    
    #TODO: Convert these pages to the new edX layout
    # 'tos.html', 
    # 'privacy.html', 
    # 'honor.html', 
    # 'copyright.html', 
)

if settings.PERFSTATS:
    urlpatterns += (url(r'^reprofile$','perfstats.views.end_profile'),)

if settings.COURSEWARE_ENABLED:
    urlpatterns += (
        url(r'^masquerade/', include('masquerade.urls')),
        url(r'^jumpto/(?P<probname>[^/]+)/$', 'courseware.views.jump_to'),
        url(r'^modx/(?P<id>.*?)/(?P<dispatch>[^/]*)$', 'courseware.module_render.modx_dispatch'), #reset_problem'),
        url(r'^xqueue/(?P<userid>[^/]*)/(?P<id>.*?)/(?P<dispatch>[^/]*)$', 'courseware.module_render.xqueue_callback'),
        url(r'^change_setting$', 'student.views.change_setting'),
        url(r'^s/(?P<template>[^/]*)$', 'static_template_view.views.auth_index'),
        #    url(r'^course_info/$', 'student.views.courseinfo'),
        #    url(r'^show_circuit/(?P<circuit>[^/]*)$', 'circuit.views.show_circuit'),
        url(r'^edit_circuit/(?P<circuit>[^/]*)$', 'circuit.views.edit_circuit'),
        url(r'^save_circuit/(?P<circuit>[^/]*)$', 'circuit.views.save_circuit'),
        url(r'^calculate$', 'util.views.calculate'),
        url(r'^heartbeat$', include('heartbeat.urls')),

        # Multicourse related:
        url(r'^courses/?$', 'courseware.views.courses', name="courses"),        
        #About the course
        url(r'^courses/(?P<course_id>[^/]+/[^/]+/[^/]+)/about$', 
            'student.views.course_info', name="about_course"),
        url(r'^courses/(?P<course_id>[^/]+/[^/]+/[^/]+)/enroll$', 
            'student.views.enroll', name="enroll"),
        
        #Inside the course
        url(r'^courses/(?P<course_id>[^/]+/[^/]+/[^/]+)/info$', 
            'courseware.views.course_info', name="info"),
        url(r'^courses/(?P<course_id>[^/]+/[^/]+/[^/]+)/book$', 
            'staticbook.views.index', name="book"),
        url(r'^courses/(?P<course_id>[^/]+/[^/]+/[^/]+)/book/(?P<page>[^/]*)$', 
            'staticbook.views.index'),
        url(r'^courses/(?P<course_id>[^/]+/[^/]+/[^/]+)/book-shifted/(?P<page>[^/]*)$', 
            'staticbook.views.index_shifted'),
        url(r'^courses/(?P<course_id>[^/]+/[^/]+/[^/]+)/courseware/?$', 
            'courseware.views.index', name="courseware"),
        url(r'^courses/(?P<course_id>[^/]+/[^/]+/[^/]+)/courseware/(?P<chapter>[^/]*)/(?P<section>[^/]*)/$', 
            'courseware.views.index', name="courseware_section"),
        url(r'^courses/(?P<course_id>[^/]+/[^/]+/[^/]+)/profile$', 
            'courseware.views.profile', name="profile"),
        url(r'^courses/(?P<course_id>[^/]+/[^/]+/[^/]+)/profile/(?P<student_id>[^/]*)/$', 
            'courseware.views.profile'),
    )
    
    # Multicourse wiki
if settings.WIKI_ENABLED:
    urlpatterns += (
        url(r'^wiki/', include('simplewiki.urls')),
        url(r'^courses/(?P<course_id>[^/]+/[^/]+/[^/]+)/wiki/', include('simplewiki.urls')),
    )

if settings.ENABLE_MULTICOURSE:
	urlpatterns += (url(r'^mitxhome$', 'multicourse.views.mitxhome'),)

if settings.QUICKEDIT:
	urlpatterns += (url(r'^quickedit/(?P<id>[^/]*)$', 'dogfood.views.quickedit'),)
	urlpatterns += (url(r'^dogfood/(?P<id>[^/]*)$', 'dogfood.views.df_capa_problem'),)

if settings.ASKBOT_ENABLED:
    urlpatterns += (url(r'^%s' % settings.ASKBOT_URL, include('askbot.urls')), \
                    url(r'^admin/', include(admin.site.urls)), \
                    url(r'^settings/', include('askbot.deps.livesettings.urls')), \
                    url(r'^followit/', include('followit.urls')), \
#                       url(r'^robots.txt$', include('robots.urls')),
                              )

if settings.DEBUG:
    ## Jasmine
    urlpatterns=urlpatterns + (url(r'^_jasmine/', include('django_jasmine.urls')),)

urlpatterns = patterns(*urlpatterns)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
