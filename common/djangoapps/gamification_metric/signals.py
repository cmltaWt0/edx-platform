"""
Catch changes in user progress and send it by API
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from tasks import send_api_request


@receiver(post_save, sender='courseware.StudentModule')
def send_achivenent(sender, instance, **kwargs):
    if instance.module_type in ('video', 'problem', 'course'):
        data = {
            'username': instance.student.username,
            'course_id': unicode(instance.course_id),
            'event_type': instance.module_type,
            'uid': unicode(instance.module_state_key),
        }
        send_api_request(data)
