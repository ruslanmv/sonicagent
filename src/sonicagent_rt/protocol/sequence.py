from dataclasses import dataclass


class SequenceError(ValueError):
    pass


@dataclass
class SequenceValidator:
    expected: int = 0
    allow_first: bool = True

    def accept(self, sequence: int) -> None:
        if sequence < 0 or sequence > 0xFFFFFFFF:
            raise SequenceError("sequence out of range")
        if self.allow_first and self.expected == 0:
            self.expected = (sequence + 1) & 0xFFFFFFFF
            self.allow_first = False
            return
        if sequence != self.expected:
            kind = "replay" if sequence < self.expected else "out-of-order"
            raise SequenceError(f"{kind} sequence: expected {self.expected}, got {sequence}")
        self.expected = (self.expected + 1) & 0xFFFFFFFF
