"""
Catch changes in user progress and send it by API
"""
import json

from django.db.models.signals import post_save
from django.dispatch import receiver



@receiver(post_save, sender='courseware.StudentModule')
def send_achivenent(sender, instance, **kwargs):
    if instance.module_type in ('video', 'problem', 'course'):
        if instance.module_type == 'video' and (instance.modified-instance.created).total_seconds()<=1:
            return None
        if instance.module_type == 'course' and json.loads(instance.state).get('position'):
            return None
        if instance.module_type == 'problem' and (not instance.grade or type(instance.grade) != float):
            return None
        data = {
            'username': instance.student.username,
            'course_id': unicode(instance.course_id),
            'event_type': instance.module_type,
            'uid': unicode(instance.module_state_key),
        }
        send_api_request(data)
