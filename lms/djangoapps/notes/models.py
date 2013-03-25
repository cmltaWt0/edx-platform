from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError

import json
import logging

log = logging.getLogger(__name__)

class Note(models.Model):
    user = models.ForeignKey(User, db_index=True)
    course_id = models.CharField(max_length=255, db_index=True)
    uri = models.CharField(max_length=1024, db_index=True)
    text = models.TextField(default="")
    quote = models.TextField(default="")
    range_start = models.CharField(max_length=2048)
    range_start_offset = models.IntegerField()
    range_end = models.CharField(max_length=2048)
    range_end_offset = models.IntegerField()
    tags = models.TextField(default="") # comma-separated string
    created = models.DateTimeField(auto_now_add=True, null=True, db_index=True)
    updated = models.DateTimeField(auto_now=True, db_index=True)

    def clean(self, json_body):
        if json_body is None:
            raise ValidationError('Note must have a body.')

        body = json.loads(json_body)
        if not type(body) is dict:
            raise ValidationError('Note body must be a dictionary.')

        self.uri = body.get('uri')
        self.text = body.get('text')
        self.quote = body.get('quote')

        ranges = body.get('ranges')
        if ranges is None or len(ranges) != 1:
            raise ValidationError('Note must contain exactly one range.')

        self.range_start = ranges[0]['start']
        self.range_start_offset = ranges[0]['startOffset']
        self.range_end = ranges[0]['end']
        self.range_end_offset = ranges[0]['endOffset']

        self.tags = ""
        tags = body.get('tags', [])
        if len(tags) > 0:
            self.tags = ",".join(tags)

    def get_absolute_url(self):
        kwargs = {'course_id': self.course_id, 'note_id': str(self.id)}
        return reverse('notes_api_note', kwargs=kwargs)

    def as_dict(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'uri': self.uri,
            'text': self.text,
            'quote': self.quote,
            'ranges': [{
                'start': self.range_start,
                'startOffset': self.range_start_offset,
                'end': self.range_end,
                'endOffset': self.range_end_offset
            }],
            'tags': self.tags.split(","),
            'created': str(self.created),
            'updated': str(self.updated)
        }