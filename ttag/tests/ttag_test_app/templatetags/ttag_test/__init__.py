from django import template
from .as_tags import (
    FishAs, AnotherFishAs, MaybeAs, DefaultAs, OutputAs
)
from .template_tags import (
    Do, Go, Ask
)

register = template.Library()

register.tag(FishAs)
register.tag(AnotherFishAs)
register.tag(MaybeAs)
register.tag(DefaultAs)
register.tag(OutputAs)

register.tag(Do)
register.tag(Go)
register.tag(Ask)
