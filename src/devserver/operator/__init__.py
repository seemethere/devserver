# NOTE: This is what registers our operator's function with kopf so that
#       `kopf.run -m devserver.operator` can work. If you add more functions
#       to the operator, you must add them here.
# flake8: noqa: F401
from .operator import create_devserver
from .operator import delete_devserver
from .operator import create_devserver_user
from .operator import update_devserver_user
from .operator import delete_devserver_user