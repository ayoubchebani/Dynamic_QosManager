import re

from django.core.exceptions import ValidationError
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_time(time):
    time_re = "^(0[0-9]|1[0-9]|2[0-3]|[0-9]):[0-5][0-9]$"
    if not re.match(time_re, time):
        print("fau")
        raise ValidationError(
            _("you must be at least 13 years old"),
            code='invalid'
        )
