from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Type:
    name: str

    def __str__(self) -> str:
        return self.name


# Primitive-like
BOOL = Type("Bool")
STRING = Type("String")
INT = Type("Int")
DECIMAL = Type("Decimal")
TIMESTAMP = Type("Timestamp")
DURATION = Type("Duration")
DATE = Type("Date")

# Domain types (v0.2 target subset)
PRICE = Type("Price")
QUANTITY = Type("Quantity")
PERCENT = Type("Percent")

# Options (v1.1-A target subset)
OPTION_CONTRACT = Type("OptionContract")
OPTION_ID = Type("OptionId")

# Internal helper types
UNKNOWN = Type("Unknown")
INT_LITERAL = Type("IntLiteral")
DECIMAL_LITERAL = Type("DecimalLiteral")
PERCENT_LITERAL = Type("PercentLiteral")


def is_numeric(t: Type) -> bool:
    return t in (INT, DECIMAL, PRICE, QUANTITY, PERCENT, INT_LITERAL, DECIMAL_LITERAL, PERCENT_LITERAL)


def is_literal(t: Type) -> bool:
    return t in (INT_LITERAL, DECIMAL_LITERAL, PERCENT_LITERAL)


def widen_literal(t: Type) -> Type:
    if t == INT_LITERAL:
        return INT
    if t == DECIMAL_LITERAL:
        return DECIMAL
    if t == PERCENT_LITERAL:
        return PERCENT
    return t


def literal_compatible_with(lit: Type, expected: Type) -> bool:
    if lit == INT_LITERAL:
        return expected in (INT, DECIMAL, PRICE, QUANTITY)
    if lit == DECIMAL_LITERAL:
        return expected in (DECIMAL, PRICE, QUANTITY)
    if lit == PERCENT_LITERAL:
        return expected == PERCENT
    return False


def type_matches(expected: Type, got: Type) -> bool:
    if expected == UNKNOWN or got == UNKNOWN:
        return True
    if expected == got:
        return True
    if is_literal(got) and literal_compatible_with(got, expected):
        return True
    # Allow Decimal where Int is expected? (conservative: no)
    return False
