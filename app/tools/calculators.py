"""Calculator processors.

Same contract as every other tool module:
    fn(files: list[Path], text: str, options: dict) -> ToolResult

Calculators take their input from `options` (no upload, no textarea) and return
numbers in `ToolResult.meta`, which the generic tool UI renders as a result list.
"""
from __future__ import annotations

from app.tools.registry import ToolResult, register


def _num(options: dict, key: str, default: float = 0.0) -> float:
    """Read a numeric option, tolerating strings and blanks from the form."""
    raw = options.get(key, default)
    if raw is None or raw == "":
        return float(default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


def _money(value: float) -> float:
    return round(value + 0.0, 2)


# --- Loans ------------------------------------------------------------------

def _amortise(principal: float, annual_rate: float, months: int) -> dict:
    """Standard amortising payment. A 0% rate divides evenly instead of
    dividing by zero."""
    if months <= 0 or principal <= 0:
        return {"error": "Enter a loan amount and a term greater than zero."}
    r = annual_rate / 100 / 12
    payment = principal / months if r == 0 else principal * r / (1 - (1 + r) ** -months)
    total = payment * months
    return {
        "monthly_payment": _money(payment),
        "total_paid": _money(total),
        "total_interest": _money(total - principal),
        "principal": _money(principal),
        "months": months,
    }


@register("loan-calculator")
def loan_calculator(files, text: str, options: dict) -> ToolResult:
    months = int(_num(options, "years", 5) * 12)
    return ToolResult(meta=_amortise(_num(options, "amount", 10000),
                                     _num(options, "rate", 8), months))


@register("mortgage-calculator")
def mortgage_calculator(files, text: str, options: dict) -> ToolResult:
    price = _num(options, "price", 250000)
    down = _num(options, "down_payment", 50000)
    months = int(_num(options, "years", 25) * 12)
    result = _amortise(price - down, _num(options, "rate", 6), months)
    if "error" not in result:
        result["down_payment"] = _money(down)
        result["loan_amount"] = _money(price - down)
    return ToolResult(meta=result)


@register("car-loan-calculator")
def car_loan_calculator(files, text: str, options: dict) -> ToolResult:
    months = int(_num(options, "years", 5) * 12)
    return ToolResult(meta=_amortise(_num(options, "amount", 20000),
                                     _num(options, "rate", 7), months))


@register("emi-calculator")
def emi_calculator(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_amortise(_num(options, "amount", 100000),
                                     _num(options, "rate", 10),
                                     int(_num(options, "months", 24))))


# --- Savings & investment ---------------------------------------------------

@register("compound-interest-calculator")
def compound_interest(files, text: str, options: dict) -> ToolResult:
    principal = _num(options, "principal", 1000)
    rate = _num(options, "rate", 7) / 100
    years = _num(options, "years", 10)
    per_year = max(1, int(_num(options, "compounds_per_year", 12)))
    amount = principal * (1 + rate / per_year) ** (per_year * years)
    return ToolResult(meta={
        "final_amount": _money(amount),
        "interest_earned": _money(amount - principal),
        "principal": _money(principal),
    })


@register("simple-interest-calculator")
def simple_interest(files, text: str, options: dict) -> ToolResult:
    p = _num(options, "principal", 1000)
    interest = p * _num(options, "rate", 5) / 100 * _num(options, "years", 3)
    return ToolResult(meta={"interest": _money(interest), "total": _money(p + interest)})


@register("savings-goal-calculator")
def savings_goal(files, text: str, options: dict) -> ToolResult:
    goal = _num(options, "goal", 10000)
    monthly = _num(options, "monthly", 250)
    rate = _num(options, "rate", 4) / 100 / 12
    if monthly <= 0:
        return ToolResult(meta={"error": "Enter a monthly contribution above zero."})
    if rate == 0:
        months = goal / monthly
    else:
        # Solve the future-value-of-an-annuity formula for the number of months.
        from math import log
        months = log(1 + goal * rate / monthly) / log(1 + rate)
    return ToolResult(meta={
        "months_needed": round(months, 1),
        "years_needed": round(months / 12, 1),
        "total_contributed": _money(monthly * months),
    })


# --- Percentages & everyday maths -------------------------------------------

@register("percentage-calculator")
def percentage_calculator(files, text: str, options: dict) -> ToolResult:
    value = _num(options, "value", 200)
    percent = _num(options, "percent", 15)
    return ToolResult(meta={
        "result": _money(value * percent / 100),
        "value_plus": _money(value * (1 + percent / 100)),
        "value_minus": _money(value * (1 - percent / 100)),
    })


@register("percentage-change-calculator")
def percentage_change(files, text: str, options: dict) -> ToolResult:
    old = _num(options, "old_value", 100)
    new = _num(options, "new_value", 125)
    if old == 0:
        return ToolResult(meta={"error": "The original value cannot be zero."})
    change = (new - old) / abs(old) * 100
    return ToolResult(meta={
        "change_percent": round(change, 2),
        "direction": "increase" if change >= 0 else "decrease",
        "difference": _money(new - old),
    })


@register("discount-calculator")
def discount_calculator(files, text: str, options: dict) -> ToolResult:
    price = _num(options, "price", 100)
    off = _num(options, "discount", 20)
    saved = price * off / 100
    return ToolResult(meta={"final_price": _money(price - saved), "you_save": _money(saved)})


@register("tip-calculator")
def tip_calculator(files, text: str, options: dict) -> ToolResult:
    bill = _num(options, "bill", 50)
    tip = bill * _num(options, "tip_percent", 15) / 100
    people = max(1, int(_num(options, "people", 1)))
    total = bill + tip
    return ToolResult(meta={
        "tip": _money(tip), "total": _money(total), "per_person": _money(total / people),
    })


@register("vat-calculator")
def vat_calculator(files, text: str, options: dict) -> ToolResult:
    amount = _num(options, "amount", 100)
    rate = _num(options, "rate", 20)
    if str(options.get("mode", "add")) == "remove":
        net = amount / (1 + rate / 100)
        return ToolResult(meta={"net": _money(net), "vat": _money(amount - net), "gross": _money(amount)})
    vat = amount * rate / 100
    return ToolResult(meta={"net": _money(amount), "vat": _money(vat), "gross": _money(amount + vat)})


# --- Health -----------------------------------------------------------------

@register("bmi-calculator")
def bmi_calculator(files, text: str, options: dict) -> ToolResult:
    kg = _num(options, "weight_kg", 70)
    cm = _num(options, "height_cm", 175)
    if kg <= 0 or cm <= 0:
        return ToolResult(meta={"error": "Enter a weight and height above zero."})
    bmi = kg / (cm / 100) ** 2
    if bmi < 18.5:
        band = "Underweight"
    elif bmi < 25:
        band = "Normal weight"
    elif bmi < 30:
        band = "Overweight"
    else:
        band = "Obese"
    return ToolResult(meta={"bmi": round(bmi, 1), "category": band})


@register("bmr-calculator")
def bmr_calculator(files, text: str, options: dict) -> ToolResult:
    """Mifflin-St Jeor, the formula most widely used clinically."""
    kg = _num(options, "weight_kg", 70)
    cm = _num(options, "height_cm", 175)
    age = _num(options, "age", 30)
    base = 10 * kg + 6.25 * cm - 5 * age
    bmr = base + (5 if str(options.get("sex", "male")) == "male" else -161)
    factors = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very active": 1.9}
    factor = factors.get(str(options.get("activity", "sedentary")), 1.2)
    return ToolResult(meta={"bmr": round(bmr), "daily_calories": round(bmr * factor)})


# --- Time & dates -----------------------------------------------------------

@register("age-calculator")
def age_calculator(files, text: str, options: dict) -> ToolResult:
    from datetime import date

    raw = str(options.get("birth_date", "")).strip()
    if not raw:
        return ToolResult(meta={"error": "Enter a birth date as YYYY-MM-DD."})
    try:
        born = date.fromisoformat(raw)
    except ValueError:
        return ToolResult(meta={"error": "Use the format YYYY-MM-DD."})
    today = date.today()
    if born > today:
        return ToolResult(meta={"error": "That date is in the future."})
    years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    months = (today.year - born.year) * 12 + today.month - born.month - (today.day < born.day)
    return ToolResult(meta={
        "years": years, "total_months": months, "total_days": (today - born).days,
    })


@register("date-difference-calculator")
def date_difference(files, text: str, options: dict) -> ToolResult:
    from datetime import date

    try:
        start = date.fromisoformat(str(options.get("start_date", "")).strip())
        end = date.fromisoformat(str(options.get("end_date", "")).strip())
    except ValueError:
        return ToolResult(meta={"error": "Enter both dates as YYYY-MM-DD."})
    days = abs((end - start).days)
    return ToolResult(meta={
        "days": days, "weeks": round(days / 7, 1), "months": round(days / 30.44, 1),
        "years": round(days / 365.25, 2),
    })


# --- Unit conversion --------------------------------------------------------
#
# Every unit is defined by its size in one base unit, so a conversion is just
# value * from_factor / to_factor. Temperature is the exception (it has offsets,
# not just scale) and is handled separately below.

_UNITS: dict[str, dict[str, float]] = {
    "length": {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0,
               "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344},
    "weight": {"mg": 1e-6, "g": 0.001, "kg": 1.0, "t": 1000.0,
               "oz": 0.028349523125, "lb": 0.45359237, "st": 6.35029318},
    "volume": {"ml": 0.001, "l": 1.0, "m3": 1000.0,
               "tsp": 0.00492892159375, "tbsp": 0.01478676478125,
               "cup": 0.2365882365, "pt": 0.473176473, "qt": 0.946352946,
               "gal": 3.785411784, "fl oz": 0.0295735295625},
    "area": {"mm2": 1e-6, "cm2": 1e-4, "m2": 1.0, "ha": 10000.0, "km2": 1e6,
             "in2": 0.00064516, "ft2": 0.09290304, "yd2": 0.83612736,
             "acre": 4046.8564224, "mi2": 2589988.110336},
    "speed": {"m/s": 1.0, "km/h": 0.277777778, "mph": 0.44704,
              "knot": 0.514444444, "ft/s": 0.3048},
    "data": {"B": 1.0, "KB": 1024.0, "MB": 1024.0**2, "GB": 1024.0**3,
             "TB": 1024.0**4, "PB": 1024.0**5,
             "bit": 0.125, "Kbit": 128.0, "Mbit": 131072.0},
}


def _convert(kind: str, options: dict) -> dict:
    table = _UNITS[kind]
    src = str(options.get("from", "")) or list(table)[0]
    dst = str(options.get("to", "")) or list(table)[1]
    if src not in table or dst not in table:
        return {"error": f"Choose units from: {', '.join(table)}"}
    value = _num(options, "value", 1)
    result = value * table[src] / table[dst]
    return {"result": round(result, 6), "formatted": f"{value:g} {src} = {result:g} {dst}"}


@register("length-converter")
def length_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_convert("length", options))


@register("weight-converter")
def weight_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_convert("weight", options))


@register("volume-converter")
def volume_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_convert("volume", options))


@register("area-converter")
def area_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_convert("area", options))


@register("speed-converter")
def speed_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_convert("speed", options))


@register("data-storage-converter")
def data_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_convert("data", options))


@register("temperature-converter")
def temperature_converter(files, text: str, options: dict) -> ToolResult:
    """Kept apart from the table-driven converters: temperature scales have an
    offset as well as a scale, so a single multiplier can't express them."""
    value = _num(options, "value", 0)
    src = str(options.get("from", "C")).upper()[:1]
    dst = str(options.get("to", "F")).upper()[:1]
    if src not in "CFK" or dst not in "CFK":
        return ToolResult(meta={"error": "Choose C, F or K."})
    celsius = value if src == "C" else (value - 32) * 5 / 9 if src == "F" else value - 273.15
    out = celsius if dst == "C" else celsius * 9 / 5 + 32 if dst == "F" else celsius + 273.15
    return ToolResult(meta={"result": round(out, 2), "formatted": f"{value:g}°{src} = {round(out, 2):g}°{dst}"})


# --- Maths ------------------------------------------------------------------

def _numbers(text: str, options: dict) -> list[float]:
    """Parse a list of numbers from free text — commas, spaces or newlines."""
    import re as _re

    raw = options.get("numbers") or text or ""
    return [float(x) for x in _re.findall(r"-?\d+(?:\.\d+)?", str(raw))]


@register("average-calculator")
def average_calculator(files, text: str, options: dict) -> ToolResult:
    xs = _numbers(text, options)
    if not xs:
        return ToolResult(meta={"error": "Enter some numbers, separated by commas or spaces."})
    xs_sorted = sorted(xs)
    mid = len(xs) // 2
    median = xs_sorted[mid] if len(xs) % 2 else (xs_sorted[mid - 1] + xs_sorted[mid]) / 2
    return ToolResult(meta={
        "count": len(xs), "sum": round(sum(xs), 6), "mean": round(sum(xs) / len(xs), 6),
        "median": round(median, 6), "min": min(xs), "max": max(xs),
    })


@register("standard-deviation-calculator")
def standard_deviation(files, text: str, options: dict) -> ToolResult:
    import statistics

    xs = _numbers(text, options)
    if len(xs) < 2:
        return ToolResult(meta={"error": "Enter at least two numbers."})
    return ToolResult(meta={
        "count": len(xs), "mean": round(statistics.fmean(xs), 6),
        "sample_std_dev": round(statistics.stdev(xs), 6),
        "population_std_dev": round(statistics.pstdev(xs), 6),
        "variance": round(statistics.variance(xs), 6),
    })


@register("percentage-of-total-calculator")
def percentage_of_total(files, text: str, options: dict) -> ToolResult:
    part = _num(options, "part", 25)
    total = _num(options, "total", 200)
    if total == 0:
        return ToolResult(meta={"error": "The total cannot be zero."})
    return ToolResult(meta={"percentage": round(part / total * 100, 4)})


@register("fraction-calculator")
def fraction_calculator(files, text: str, options: dict) -> ToolResult:
    from fractions import Fraction

    try:
        a = Fraction(str(options.get("a", "1/2")).strip())
        bfr = Fraction(str(options.get("b", "1/3")).strip())
    except (ValueError, ZeroDivisionError):
        return ToolResult(meta={"error": "Write fractions like 3/4 (or a whole number)."})
    op = str(options.get("operation", "+"))
    if op == "/" and bfr == 0:
        return ToolResult(meta={"error": "Cannot divide by zero."})
    result = {"+": a + bfr, "-": a - bfr, "*": a * bfr, "/": a / bfr if bfr else a}.get(op)
    if result is None:
        return ToolResult(meta={"error": "Choose +, -, * or /."})
    return ToolResult(meta={"result": str(result), "decimal": round(float(result), 6)})


@register("ratio-calculator")
def ratio_calculator(files, text: str, options: dict) -> ToolResult:
    from math import gcd

    a, b = int(_num(options, "a", 16)), int(_num(options, "b", 9))
    if a == 0 or b == 0:
        return ToolResult(meta={"error": "Both numbers must be above zero."})
    g = gcd(a, b)
    return ToolResult(meta={
        "simplified": f"{a // g}:{b // g}", "decimal": round(a / b, 6),
        "percentage": round(a / (a + b) * 100, 2),
    })


@register("rounding-calculator")
def rounding_calculator(files, text: str, options: dict) -> ToolResult:
    import math

    v = _num(options, "value", 3.14159)
    dp = int(_num(options, "decimals", 2))
    return ToolResult(meta={
        "rounded": round(v, dp), "round_up": math.ceil(v), "round_down": math.floor(v),
        "to_integer": round(v),
    })


@register("exponent-calculator")
def exponent_calculator(files, text: str, options: dict) -> ToolResult:
    base = _num(options, "base", 2)
    power = _num(options, "power", 10)
    try:
        result = base ** power
    except (OverflowError, ValueError):
        return ToolResult(meta={"error": "That result is too large to calculate."})
    if isinstance(result, complex):
        return ToolResult(meta={"error": "A negative base with a fractional power has no real result."})
    return ToolResult(meta={"result": round(result, 6)})


@register("root-calculator")
def root_calculator(files, text: str, options: dict) -> ToolResult:
    value = _num(options, "value", 144)
    n = _num(options, "root", 2)
    if n == 0:
        return ToolResult(meta={"error": "The root cannot be zero."})
    if value < 0 and int(n) % 2 == 0:
        return ToolResult(meta={"error": "An even root of a negative number has no real result."})
    result = -((-value) ** (1 / n)) if value < 0 else value ** (1 / n)
    return ToolResult(meta={"result": round(result, 6)})


@register("logarithm-calculator")
def logarithm_calculator(files, text: str, options: dict) -> ToolResult:
    import math

    value = _num(options, "value", 100)
    base = _num(options, "base", 10)
    if value <= 0:
        return ToolResult(meta={"error": "The number must be greater than zero."})
    if base <= 0 or base == 1:
        return ToolResult(meta={"error": "The base must be positive and not 1."})
    return ToolResult(meta={
        "result": round(math.log(value, base), 6),
        "natural_log": round(math.log(value), 6),
        "log10": round(math.log10(value), 6),
    })


@register("gcf-lcm-calculator")
def gcf_lcm_calculator(files, text: str, options: dict) -> ToolResult:
    from math import gcd

    xs = [int(x) for x in _numbers(text, options) if x]
    if len(xs) < 2:
        return ToolResult(meta={"error": "Enter at least two whole numbers."})
    g = xs[0]
    l = abs(xs[0])
    for n in xs[1:]:
        g = gcd(g, n)
        l = abs(l * n) // gcd(l, n)
    return ToolResult(meta={"gcf": g, "lcm": l, "numbers": xs})


@register("quadratic-solver")
def quadratic_solver(files, text: str, options: dict) -> ToolResult:
    import math

    a, b, c = _num(options, "a", 1), _num(options, "b", -3), _num(options, "c", 2)
    if a == 0:
        return ToolResult(meta={"error": "'a' cannot be zero — that is a linear equation."})
    disc = b * b - 4 * a * c
    if disc < 0:
        real, imag = -b / (2 * a), math.sqrt(-disc) / (2 * a)
        return ToolResult(meta={
            "discriminant": round(disc, 6), "roots": "complex",
            "x1": f"{round(real, 4)} + {round(imag, 4)}i",
            "x2": f"{round(real, 4)} - {round(imag, 4)}i",
        })
    root = math.sqrt(disc)
    return ToolResult(meta={
        "discriminant": round(disc, 6),
        "x1": round((-b + root) / (2 * a), 6), "x2": round((-b - root) / (2 * a), 6),
    })


@register("permutation-combination-calculator")
def perm_comb_calculator(files, text: str, options: dict) -> ToolResult:
    import math

    n, r = int(_num(options, "n", 10)), int(_num(options, "r", 3))
    if n < 0 or r < 0:
        return ToolResult(meta={"error": "Both values must be zero or above."})
    if r > n:
        return ToolResult(meta={"error": "r cannot be larger than n."})
    return ToolResult(meta={"permutations": math.perm(n, r), "combinations": math.comb(n, r)})


# --- Geometry ---------------------------------------------------------------

@register("area-calculator")
def area_calculator(files, text: str, options: dict) -> ToolResult:
    import math

    shape = str(options.get("shape", "rectangle"))
    a, b = _num(options, "a", 10), _num(options, "b", 5)
    if a <= 0 or (shape != "circle" and b <= 0):
        return ToolResult(meta={"error": "Enter measurements above zero."})
    areas = {
        "rectangle": a * b,
        "triangle": a * b / 2,
        "circle": math.pi * a * a,
        "trapezoid": (a + b) / 2 * _num(options, "height", 4),
    }
    if shape not in areas:
        return ToolResult(meta={"error": "Choose rectangle, triangle, circle or trapezoid."})
    return ToolResult(meta={"shape": shape, "area": round(areas[shape], 6)})


@register("volume-calculator")
def volume_calculator(files, text: str, options: dict) -> ToolResult:
    import math

    shape = str(options.get("shape", "box"))
    a, b, c = _num(options, "a", 10), _num(options, "b", 5), _num(options, "c", 3)
    volumes = {
        "box": a * b * c,
        "cylinder": math.pi * a * a * b,
        "sphere": 4 / 3 * math.pi * a ** 3,
        "cone": math.pi * a * a * b / 3,
    }
    if shape not in volumes:
        return ToolResult(meta={"error": "Choose box, cylinder, sphere or cone."})
    if a <= 0:
        return ToolResult(meta={"error": "Enter measurements above zero."})
    return ToolResult(meta={"shape": shape, "volume": round(volumes[shape], 6)})


# --- Health -----------------------------------------------------------------

@register("body-fat-calculator")
def body_fat_calculator(files, text: str, options: dict) -> ToolResult:
    """US Navy method — the standard tape-measure estimate."""
    import math

    sex = str(options.get("sex", "male"))
    waist, neck = _num(options, "waist_cm", 85), _num(options, "neck_cm", 38)
    height = _num(options, "height_cm", 175)
    hip = _num(options, "hip_cm", 95)
    if min(waist, neck, height) <= 0:
        return ToolResult(meta={"error": "Enter all measurements above zero."})
    try:
        if sex == "male":
            if waist - neck <= 0:
                return ToolResult(meta={"error": "Waist must be larger than neck."})
            bf = 495 / (1.0324 - 0.19077 * math.log10(waist - neck) + 0.15456 * math.log10(height)) - 450
        else:
            if waist + hip - neck <= 0:
                return ToolResult(meta={"error": "Check the waist, hip and neck measurements."})
            bf = 495 / (1.29579 - 0.35004 * math.log10(waist + hip - neck) + 0.22100 * math.log10(height)) - 450
    except ValueError:
        return ToolResult(meta={"error": "Those measurements don't produce a valid result."})
    return ToolResult(meta={"body_fat_percent": round(bf, 1)})


@register("ideal-weight-calculator")
def ideal_weight_calculator(files, text: str, options: dict) -> ToolResult:
    """Devine formula, with the healthy-BMI range for context."""
    cm = _num(options, "height_cm", 175)
    if cm <= 0:
        return ToolResult(meta={"error": "Enter a height above zero."})
    inches_over_5ft = max(0.0, cm / 2.54 - 60)
    base = 50 if str(options.get("sex", "male")) == "male" else 45.5
    m = cm / 100
    return ToolResult(meta={
        "ideal_weight_kg": round(base + 2.3 * inches_over_5ft, 1),
        "healthy_range_kg": f"{round(18.5 * m * m, 1)} – {round(24.9 * m * m, 1)}",
    })


@register("water-intake-calculator")
def water_intake_calculator(files, text: str, options: dict) -> ToolResult:
    kg = _num(options, "weight_kg", 70)
    minutes = _num(options, "exercise_minutes", 30)
    if kg <= 0:
        return ToolResult(meta={"error": "Enter a weight above zero."})
    litres = kg * 0.033 + (minutes / 30) * 0.35
    return ToolResult(meta={
        "litres_per_day": round(litres, 2), "ml_per_day": round(litres * 1000),
        "glasses_250ml": round(litres * 1000 / 250, 1),
    })


@register("one-rep-max-calculator")
def one_rep_max(files, text: str, options: dict) -> ToolResult:
    """Epley formula, with the common training percentages."""
    weight = _num(options, "weight", 80)
    reps = int(_num(options, "reps", 5))
    if weight <= 0 or reps <= 0:
        return ToolResult(meta={"error": "Enter a weight and rep count above zero."})
    orm = weight if reps == 1 else weight * (1 + reps / 30)
    return ToolResult(meta={
        "one_rep_max": round(orm, 1),
        "95_percent": round(orm * 0.95, 1), "85_percent": round(orm * 0.85, 1),
        "70_percent": round(orm * 0.70, 1),
    })


@register("pace-calculator")
def pace_calculator(files, text: str, options: dict) -> ToolResult:
    distance = _num(options, "distance_km", 10)
    minutes = _num(options, "time_minutes", 55)
    if distance <= 0 or minutes <= 0:
        return ToolResult(meta={"error": "Enter a distance and time above zero."})
    pace = minutes / distance
    mins, secs = int(pace), round((pace - int(pace)) * 60)
    if secs == 60:
        mins, secs = mins + 1, 0
    return ToolResult(meta={
        "pace_per_km": f"{mins}:{secs:02d}", "speed_kmh": round(distance / (minutes / 60), 2),
        "pace_per_mile": round(pace * 1.609344, 2),
    })


# --- Everyday ---------------------------------------------------------------

@register("gpa-calculator")
def gpa_calculator(files, text: str, options: dict) -> ToolResult:
    """Grades and credits as parallel comma-separated lists."""
    import re as _re

    points = {"a+": 4.0, "a": 4.0, "a-": 3.7, "b+": 3.3, "b": 3.0, "b-": 2.7,
              "c+": 2.3, "c": 2.0, "c-": 1.7, "d+": 1.3, "d": 1.0, "f": 0.0}
    grades = [g.strip().lower() for g in str(options.get("grades", "A,B+,B,C")).split(",") if g.strip()]
    credits = [float(c) for c in _re.findall(r"\d+(?:\.\d+)?", str(options.get("credits", "3,3,4,3")))]
    if not grades:
        return ToolResult(meta={"error": "Enter grades like A, B+, C."})
    unknown = [g for g in grades if g not in points]
    if unknown:
        return ToolResult(meta={"error": f"Unrecognised grade(s): {', '.join(unknown)}"})
    if len(credits) != len(grades):
        credits = [1.0] * len(grades)  # equal weight when credits don't line up
    total = sum(credits)
    gpa = sum(points[g] * c for g, c in zip(grades, credits)) / total if total else 0
    return ToolResult(meta={"gpa": round(gpa, 2), "courses": len(grades), "total_credits": total})


@register("fuel-cost-calculator")
def fuel_cost_calculator(files, text: str, options: dict) -> ToolResult:
    distance = _num(options, "distance", 500)
    efficiency = _num(options, "efficiency_km_per_l", 12)
    price = _num(options, "price_per_litre", 1.5)
    if efficiency <= 0:
        return ToolResult(meta={"error": "Fuel efficiency must be above zero."})
    litres = distance / efficiency
    return ToolResult(meta={
        "litres_needed": round(litres, 2), "total_cost": _money(litres * price),
        "cost_per_km": round(litres * price / distance, 4) if distance else 0,
    })


@register("unit-price-calculator")
def unit_price_calculator(files, text: str, options: dict) -> ToolResult:
    """Compare two pack sizes and say which is actually cheaper."""
    p1, q1 = _num(options, "price_a", 3.5), _num(options, "quantity_a", 500)
    p2, q2 = _num(options, "price_b", 6.0), _num(options, "quantity_b", 1000)
    if q1 <= 0 or q2 <= 0:
        return ToolResult(meta={"error": "Both quantities must be above zero."})
    u1, u2 = p1 / q1, p2 / q2
    better = "A" if u1 < u2 else "B" if u2 < u1 else "same"
    return ToolResult(meta={
        "unit_price_a": round(u1, 6), "unit_price_b": round(u2, 6),
        "better_value": better, "saving_percent": round(abs(u1 - u2) / max(u1, u2) * 100, 1),
    })


@register("electricity-cost-calculator")
def electricity_cost_calculator(files, text: str, options: dict) -> ToolResult:
    watts = _num(options, "watts", 100)
    hours = _num(options, "hours_per_day", 5)
    rate = _num(options, "rate_per_kwh", 0.25)
    kwh = watts / 1000 * hours
    return ToolResult(meta={
        "kwh_per_day": round(kwh, 4), "cost_per_day": _money(kwh * rate),
        "cost_per_month": _money(kwh * rate * 30), "cost_per_year": _money(kwh * rate * 365),
    })


@register("paint-calculator")
def paint_calculator(files, text: str, options: dict) -> ToolResult:
    length = _num(options, "length_m", 5)
    width = _num(options, "width_m", 4)
    height = _num(options, "height_m", 2.7)
    coats = max(1, int(_num(options, "coats", 2)))
    coverage = _num(options, "coverage_m2_per_litre", 10)
    if min(length, width, height) <= 0 or coverage <= 0:
        return ToolResult(meta={"error": "Enter room measurements and coverage above zero."})
    wall_area = 2 * (length + width) * height
    return ToolResult(meta={
        "wall_area_m2": round(wall_area, 2),
        "litres_needed": round(wall_area * coats / coverage, 2), "coats": coats,
    })


# --- More dates -------------------------------------------------------------

@register("add-subtract-date-calculator")
def add_subtract_date(files, text: str, options: dict) -> ToolResult:
    from datetime import date, timedelta

    raw = str(options.get("start_date", "")).strip()
    try:
        start = date.fromisoformat(raw) if raw else date.today()
    except ValueError:
        return ToolResult(meta={"error": "Use the format YYYY-MM-DD."})
    days = int(_num(options, "days", 30))
    if str(options.get("operation", "add")) == "subtract":
        days = -days
    result = start + timedelta(days=days)
    return ToolResult(meta={"result_date": result.isoformat(), "weekday": result.strftime("%A")})


@register("countdown-calculator")
def countdown_calculator(files, text: str, options: dict) -> ToolResult:
    from datetime import date

    raw = str(options.get("target_date", "")).strip()
    if not raw:
        return ToolResult(meta={"error": "Enter a target date as YYYY-MM-DD."})
    try:
        target = date.fromisoformat(raw)
    except ValueError:
        return ToolResult(meta={"error": "Use the format YYYY-MM-DD."})
    delta = (target - date.today()).days
    return ToolResult(meta={
        "days": abs(delta), "weeks": round(abs(delta) / 7, 1),
        "direction": "away" if delta >= 0 else "ago",
        "weekday": target.strftime("%A"),
    })


@register("work-hours-calculator")
def work_hours_calculator(files, text: str, options: dict) -> ToolResult:
    from datetime import datetime, timedelta

    try:
        start = datetime.strptime(str(options.get("start_time", "09:00")).strip(), "%H:%M")
        end = datetime.strptime(str(options.get("end_time", "17:30")).strip(), "%H:%M")
    except ValueError:
        return ToolResult(meta={"error": "Enter times as HH:MM, e.g. 09:00."})
    if end <= start:
        end += timedelta(days=1)  # an overnight shift
    worked = (end - start).total_seconds() / 3600 - _num(options, "break_minutes", 30) / 60
    if worked < 0:
        return ToolResult(meta={"error": "The break is longer than the shift."})
    rate = _num(options, "hourly_rate", 0)
    out = {"hours": round(worked, 2), "hours_minutes": f"{int(worked)}h {round((worked % 1) * 60)}m"}
    if rate:
        out["pay"] = _money(worked * rate)
    return ToolResult(meta=out)
