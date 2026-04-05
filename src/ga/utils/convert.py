from typing import Any, Hashable
def dict_to_object(dict_obj):
    class DictObject:
        def __init__(self, d):
            for k, v in d.items():
                if isinstance(v, dict):
                    setattr(self, k, DictObject(v))
                else:
                    setattr(self, k, v)
    return DictObject(dict_obj)

def identity(x: Any) -> Any:
    return x