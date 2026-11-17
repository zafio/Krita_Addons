# Cursor Resize & Opacity - value curves
# Author: Zafio
#
# Pure math, no Krita/Qt imports, so it can be tested on its own.
#
# Every value is driven by a "travel" number: how many screen pixels the
# cursor has moved (accumulated, clamped). Each curve converts travel <-> value.
# Low values get many pixels per step (precise), high values grow faster.

import math


class SizeCurve:
    """Brush size curve.

    - From MIN_SIZE up to `precise_until` px: linear, `px_per_unit` screen
      pixels per 1 px of brush size (very precise, 1..20 px is easy to hit).
    - Above that: exponential growth whose slope matches the linear part at
      the joint, so there is no jump in speed. Every `px_per_unit * precise_until
      * ln(2)` screen pixels the size doubles.
    """

    MIN_SIZE = 1.0

    def __init__(self, precise_until=20.0, px_per_unit=8.0, max_size=1000.0):
        self.precise_until = float(precise_until)
        self.px_per_unit = float(px_per_unit)
        self.max_size = float(max_size)
        # Travel where the linear part ends.
        self._joint = (self.precise_until - self.MIN_SIZE) * self.px_per_unit
        # Exponential scale: d(size)/d(travel) at the joint = 1/px_per_unit.
        self._k = self.precise_until * self.px_per_unit

    @property
    def min_travel(self):
        return 0.0

    @property
    def max_travel(self):
        return self.travel_for(self.max_size)

    def value_at(self, travel):
        travel = min(max(travel, self.min_travel), self.max_travel)
        if travel <= self._joint:
            value = self.MIN_SIZE + travel / self.px_per_unit
        else:
            value = self.precise_until * math.exp((travel - self._joint) / self._k)
        return min(max(value, self.MIN_SIZE), self.max_size)

    def travel_for(self, value):
        value = min(max(float(value), self.MIN_SIZE), self.max_size)
        if value <= self.precise_until:
            return (value - self.MIN_SIZE) * self.px_per_unit
        return self._joint + self._k * math.log(value / self.precise_until)

    @staticmethod
    def snap(value):
        """Brush sizes are applied as whole pixels (1, 2, 3 ...)."""
        return max(1, int(round(value)))


class OpacityCurve:
    """Painting opacity curve, in percent.

    Two linear segments: below `precise_until` % each percent takes
    `precise_px_per_unit` pixels, above it `px_per_unit` pixels.
    """

    def __init__(self, min_opacity=1.0, precise_until=20.0,
                 precise_px_per_unit=5.0, px_per_unit=2.5):
        self.min_opacity = float(min_opacity)
        self.max_opacity = 100.0
        self.precise_until = float(precise_until)
        self.precise_px = float(precise_px_per_unit)
        self.px = float(px_per_unit)
        self._joint = (self.precise_until - self.min_opacity) * self.precise_px

    @property
    def min_travel(self):
        return 0.0

    @property
    def max_travel(self):
        return self.travel_for(self.max_opacity)

    def value_at(self, travel):
        travel = min(max(travel, self.min_travel), self.max_travel)
        if travel <= self._joint:
            value = self.min_opacity + travel / self.precise_px
        else:
            value = self.precise_until + (travel - self._joint) / self.px
        return min(max(value, self.min_opacity), self.max_opacity)

    def travel_for(self, value):
        value = min(max(float(value), self.min_opacity), self.max_opacity)
        if value <= self.precise_until:
            return (value - self.min_opacity) * self.precise_px
        return self._joint + (value - self.precise_until) * self.px

    @staticmethod
    def snap(value):
        return max(0, min(100, int(round(value))))
