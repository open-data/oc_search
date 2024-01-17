from .models import *
from .custom import *
import pkgutil
import importlib

for finder, name, ispkg in pkgutil.iter_modules(custom.__path__, custom.__name__ + "."):
    importlib.import_module(name)

