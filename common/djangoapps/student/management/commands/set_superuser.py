from optparse import make_option
import re
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--unset',
                    action='store_true',
                    dest='unset',
                    default=False,
                    help='Set is_superuser to False instead of True'),
    )

    args = '<user|email> [user|email ...]>'
    help = """
    This command will set is_superuser to true for one or more users.
    Lookup by username or email address, assumes usernames
    do not look like email addresses.
    """

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError('Usage is set_superuser {0}'.format(self.args))

        for user in args:
            if '@' user):
                v = User.objects.get(email=user)
            else:
                v = User.objects.get(username=user)

            if options['unset']:
                v.is_superuser = False
            else:
                v.is_superuser = True

            v.save()

        print 'Success!'
