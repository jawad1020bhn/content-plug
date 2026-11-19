"""Headless stand-in for qfluentwidgets' config layer.

VSR's `backend/config.py` imports Qt widgets (`qfluentwidgets`) only to get a
settings store; `backend/main.py` never touches a widget. On a server or
container without libGL/Qt that import is the one thing that stops the CLI
from starting, so this module provides the same handful of names with the same
behaviour and no Qt.

Put this directory first on PYTHONPATH when running VSR's CLI without Qt:

    PYTHONPATH=clip-desk/scripts/vsr_shim python backend/main.py -i in -o out

Only the CLI needs this. The GUI needs the real pyside6-fluent-widgets.
Values are kept in memory for the run; nothing is persisted to disk.
"""

import json

__all__ = ["qconfig", "QConfig", "ConfigItem", "OptionsConfigItem",
           "RangeConfigItem", "ConfigValidator", "BoolValidator",
           "RangeValidator", "OptionsValidator", "ConfigSerializer",
           "EnumSerializer", "BoolSerializer"]


class ConfigValidator:
    def validate(self, value):
        return True

    def correct(self, value):
        return value


class BoolValidator(ConfigValidator):
    def validate(self, value):
        return isinstance(value, bool)

    def correct(self, value):
        return bool(value)


class RangeValidator(ConfigValidator):
    def __init__(self, min_value, max_value):
        self.min, self.max = min_value, max_value

    def validate(self, value):
        return isinstance(value, (int, float)) and self.min <= value <= self.max

    def correct(self, value):
        try:
            return max(self.min, min(self.max, value))
        except TypeError:
            return self.min


class OptionsValidator(ConfigValidator):
    def __init__(self, options):
        self.options = list(options)

    def validate(self, value):
        return value in self.options

    def correct(self, value):
        return value if value in self.options else self.options[0]


class ConfigSerializer:
    def serialize(self, value):
        return value

    def deserialize(self, value):
        return value


class EnumSerializer(ConfigSerializer):
    def __init__(self, enum_class):
        self.enum = enum_class

    def serialize(self, value):
        return getattr(value, "name", value)

    def deserialize(self, value):
        if isinstance(value, str) and value in self.enum.__members__:
            return self.enum[value]
        return value


class BoolSerializer(ConfigSerializer):
    def serialize(self, value):
        return bool(value)

    def deserialize(self, value):
        return bool(value)


class ConfigItem:
    def __init__(self, group, name, default, validator=None, restart=False,
                 serializer=None, **kwargs):
        self.group, self.name, self.default = group, name, default
        self.validator = validator or ConfigValidator()
        self.serializer = serializer or ConfigSerializer()
        self.restart = restart
        self._value = default

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = self.validator.correct(v)

    def __repr__(self):
        return f"<ConfigItem {self.group}.{self.name}={self._value!r}>"


class OptionsConfigItem(ConfigItem):
    pass


class RangeConfigItem(ConfigItem):
    pass


class QConfig:
    def __init__(self):
        self._items = {f"{c.group}.{c.name}": c
                       for c in vars(type(self)).values()
                       if isinstance(c, ConfigItem)}

    def set(self, item, value):
        item.value = value

    def get(self, item):
        return item.value

    def toDict(self):
        return {k: c.serializer.serialize(c.value) for k, c in self._items.items()}

    def load(self, file=None, config=None):
        """Load a qfluentwidgets-style json file if it exists; else keep defaults."""
        if file is None:
            return
        try:
            with open(file, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return
        for key, value in data.items():
            item = self._items.get(key)
            if item is not None:
                item.value = item.serializer.deserialize(value)

    def save(self, file=None):
        if file is None:
            return
        try:
            with open(file, "w", encoding="utf-8") as fh:
                json.dump(self.toDict(), fh)
        except OSError:
            pass


qconfig = QConfig()
