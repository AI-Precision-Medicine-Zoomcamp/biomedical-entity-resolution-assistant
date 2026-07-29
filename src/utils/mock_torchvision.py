import sys
from importlib.machinery import ModuleSpec
from unittest.mock import MagicMock

# Dynamic mock class that returns mock objects for any attribute access
class MockModule(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

class TorchvisionMockLoader:
    def create_module(self, spec):
        mod = MockModule()
        mod.__name__ = spec.name
        mod.__file__ = "<mock>"
        mod.__loader__ = self
        mod.__path__ = []  # Crucial: marks the module as a package so submodules can be imported
        return mod

    def exec_module(self, module):
        pass

class TorchvisionMockFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname == "torchvision" or fullname.startswith("torchvision."):
            return ModuleSpec(fullname, TorchvisionMockLoader())
            
        # Also catch related PyTorch/Caffe/etc. dependencies if needed,
        # but for now we focus strictly on torchvision
        return None

# Register our finder at the beginning of the import meta-path
sys.meta_path.insert(0, TorchvisionMockFinder())
