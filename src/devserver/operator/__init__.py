# NOTE: This is what registers our operator's function with kopf so that
#       `kopf.run -m devserver.operator` can work. If you add more functions
#       to the operator, you must add them here.
# flake8: noqa: F401
from . import operator