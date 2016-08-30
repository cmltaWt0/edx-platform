"""
Catch changes in user progress and send it by API
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from api_calls import APICalls


@receiver(post_save, sender='courseware.StudentModule')
def send_achivenent(sender, instance, **kwargs):
    if instance.module_type in ('video', 'problem', 'course'):
        data = {
            'user': instance.student.pk,
            'course_id': unicode(instance.course_id),
            'event_type': instance.module_type,
            'uid': unicode(instance.module_state_key),
        }
        APICalls().api_call(**data)
