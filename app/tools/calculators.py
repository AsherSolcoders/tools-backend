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


# --- Loans & debt -----------------------------------------------------------

@register("amortization-calculator")
def amortization_calculator(files, text: str, options: dict) -> ToolResult:
    """Payment plus a year-by-year split of interest and principal."""
    principal = _num(options, "amount", 200000)
    rate = _num(options, "rate", 6)
    years = int(_num(options, "years", 20))
    base = _amortise(principal, rate, years * 12)
    if "error" in base:
        return ToolResult(meta=base)
    payment, r, balance = base["monthly_payment"], rate / 100 / 12, principal
    schedule = []
    for year in range(1, years + 1):
        interest_year = principal_year = 0.0
        for _ in range(12):
            interest = balance * r
            principal_part = min(payment - interest, balance)
            balance -= principal_part
            interest_year += interest
            principal_year += principal_part
        schedule.append({"year": year, "interest": _money(interest_year),
                         "principal": _money(principal_year), "balance": _money(max(balance, 0))})
    base["yearly_schedule"] = schedule
    return ToolResult(meta=base)


@register("refinance-calculator")
def refinance_calculator(files, text: str, options: dict) -> ToolResult:
    balance = _num(options, "balance", 180000)
    old = _amortise(balance, _num(options, "current_rate", 7), int(_num(options, "years_left", 20)) * 12)
    new = _amortise(balance, _num(options, "new_rate", 5), int(_num(options, "new_years", 20)) * 12)
    if "error" in old or "error" in new:
        return ToolResult(meta={"error": "Enter a balance and terms above zero."})
    fees = _num(options, "closing_costs", 3000)
    saving = old["monthly_payment"] - new["monthly_payment"]
    return ToolResult(meta={
        "current_payment": old["monthly_payment"], "new_payment": new["monthly_payment"],
        "monthly_saving": _money(saving),
        "break_even_months": round(fees / saving, 1) if saving > 0 else "never — the new payment is higher",
        "lifetime_saving": _money(old["total_paid"] - new["total_paid"] - fees),
    })


@register("debt-payoff-calculator")
def debt_payoff_calculator(files, text: str, options: dict) -> ToolResult:
    """How long a fixed monthly payment takes to clear a balance."""
    balance = _num(options, "balance", 5000)
    rate = _num(options, "rate", 18) / 100 / 12
    payment = _num(options, "monthly_payment", 250)
    if balance <= 0 or payment <= 0:
        return ToolResult(meta={"error": "Enter a balance and payment above zero."})
    if payment <= balance * rate:
        return ToolResult(meta={"error": "That payment only covers the interest — the balance would never clear."})
    months, total, owed = 0, 0.0, balance
    while owed > 0 and months < 1200:
        owed = owed * (1 + rate) - payment
        total += payment
        months += 1
    return ToolResult(meta={
        "months_to_clear": months, "years": round(months / 12, 1),
        "total_paid": _money(total - max(owed, 0)), "total_interest": _money(total - max(owed, 0) - balance),
    })


@register("credit-card-payoff-calculator")
def credit_card_payoff(files, text: str, options: dict) -> ToolResult:
    return debt_payoff_calculator(files, text, {
        "balance": _num(options, "balance", 3000),
        "rate": _num(options, "apr", 22),
        "monthly_payment": _num(options, "monthly_payment", 150),
    })


@register("apr-calculator")
def apr_calculator(files, text: str, options: dict) -> ToolResult:
    """Effective APR once fees are rolled into the cost of borrowing."""
    amount = _num(options, "amount", 10000)
    fees = _num(options, "fees", 300)
    rate = _num(options, "rate", 8)
    months = int(_num(options, "years", 5) * 12)
    base = _amortise(amount, rate, months)
    if "error" in base:
        return ToolResult(meta=base)
    received = amount - fees
    if received <= 0:
        return ToolResult(meta={"error": "Fees cannot be more than the loan."})
    # Bisect for the rate that makes the payment match on the smaller amount.
    lo, hi, payment = 0.0, 100.0, base["monthly_payment"]
    for _ in range(200):
        mid = (lo + hi) / 2
        r = mid / 100 / 12
        guess = received / months if r == 0 else received * r / (1 - (1 + r) ** -months)
        if guess < payment:
            lo = mid
        else:
            hi = mid
    return ToolResult(meta={
        "nominal_rate": rate, "effective_apr": round((lo + hi) / 2, 3),
        "monthly_payment": payment, "total_fees": _money(fees),
    })


@register("down-payment-calculator")
def down_payment_calculator(files, text: str, options: dict) -> ToolResult:
    price = _num(options, "price", 300000)
    percent = _num(options, "percent", 20)
    down = price * percent / 100
    return ToolResult(meta={
        "down_payment": _money(down), "loan_amount": _money(price - down),
        "loan_to_value_percent": round((price - down) / price * 100, 2) if price else 0,
    })


# --- Savings & investment ---------------------------------------------------

@register("investment-roi-calculator")
def roi_calculator(files, text: str, options: dict) -> ToolResult:
    invested = _num(options, "invested", 10000)
    returned = _num(options, "returned", 15000)
    years = _num(options, "years", 3)
    if invested <= 0:
        return ToolResult(meta={"error": "Enter an amount invested above zero."})
    gain = returned - invested
    out = {"profit": _money(gain), "roi_percent": round(gain / invested * 100, 2)}
    if years > 0 and returned > 0:
        out["annualised_percent"] = round(((returned / invested) ** (1 / years) - 1) * 100, 2)
    return ToolResult(meta=out)


def _future_value(monthly: float, annual_rate: float, years: float, lump: float = 0.0) -> dict:
    r = annual_rate / 100 / 12
    months = int(years * 12)
    fv_lump = lump * (1 + r) ** months
    fv_monthly = monthly * months if r == 0 else monthly * (((1 + r) ** months - 1) / r)
    invested = lump + monthly * months
    total = fv_lump + fv_monthly
    return {"final_value": _money(total), "total_invested": _money(invested),
            "returns": _money(total - invested), "months": months}


@register("sip-calculator")
def sip_calculator(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_future_value(_num(options, "monthly", 5000),
                                         _num(options, "rate", 12), _num(options, "years", 10)))


@register("lumpsum-calculator")
def lumpsum_calculator(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_future_value(0, _num(options, "rate", 12),
                                         _num(options, "years", 10), _num(options, "amount", 100000)))


@register("retirement-calculator")
def retirement_calculator(files, text: str, options: dict) -> ToolResult:
    age = _num(options, "current_age", 30)
    retire = _num(options, "retirement_age", 60)
    if retire <= age:
        return ToolResult(meta={"error": "Retirement age must be later than your current age."})
    fv = _future_value(_num(options, "monthly_saving", 500), _num(options, "rate", 7),
                       retire - age, _num(options, "current_savings", 20000))
    fv["years_to_retirement"] = round(retire - age, 1)
    # A common rule of thumb for a sustainable withdrawal.
    fv["income_at_4_percent_per_year"] = _money(float(fv["final_value"]) * 0.04)
    return ToolResult(meta=fv)


@register("401k-calculator")
def four01k_calculator(files, text: str, options: dict) -> ToolResult:
    salary = _num(options, "annual_salary", 60000)
    contrib = _num(options, "contribution_percent", 6)
    match = min(_num(options, "employer_match_percent", 3), contrib)
    monthly = salary * (contrib + match) / 100 / 12
    fv = _future_value(monthly, _num(options, "rate", 7), _num(options, "years", 30))
    fv["your_monthly"] = _money(salary * contrib / 100 / 12)
    fv["employer_monthly"] = _money(salary * match / 100 / 12)
    return ToolResult(meta=fv)


@register("future-value-calculator")
def future_value_calculator(files, text: str, options: dict) -> ToolResult:
    amount = _num(options, "amount", 10000)
    rate = _num(options, "rate", 7) / 100
    years = _num(options, "years", 10)
    if str(options.get("direction", "future")) == "present":
        if (1 + rate) ** years == 0:
            return ToolResult(meta={"error": "Those inputs don't produce a result."})
        return ToolResult(meta={"present_value": _money(amount / (1 + rate) ** years)})
    return ToolResult(meta={"future_value": _money(amount * (1 + rate) ** years)})


@register("annuity-calculator")
def annuity_calculator(files, text: str, options: dict) -> ToolResult:
    payment = _num(options, "payment", 1000)
    rate = _num(options, "rate", 5) / 100
    years = int(_num(options, "years", 20))
    if rate == 0:
        return ToolResult(meta={"total_value": _money(payment * years), "payments": years})
    fv = payment * (((1 + rate) ** years - 1) / rate)
    pv = payment * ((1 - (1 + rate) ** -years) / rate)
    return ToolResult(meta={"future_value": _money(fv), "present_value": _money(pv), "payments": years})


@register("dividend-calculator")
def dividend_calculator(files, text: str, options: dict) -> ToolResult:
    shares = _num(options, "shares", 500)
    per_share = _num(options, "dividend_per_share", 2.5)
    price = _num(options, "share_price", 50)
    annual = shares * per_share
    out = {"annual_income": _money(annual), "quarterly": _money(annual / 4), "monthly": _money(annual / 12)}
    if price > 0:
        out["yield_percent"] = round(per_share / price * 100, 2)
    return ToolResult(meta=out)


@register("inflation-calculator")
def inflation_calculator(files, text: str, options: dict) -> ToolResult:
    amount = _num(options, "amount", 1000)
    rate = _num(options, "rate", 3) / 100
    years = _num(options, "years", 10)
    future_cost = amount * (1 + rate) ** years
    return ToolResult(meta={
        "same_basket_costs": _money(future_cost),
        "todays_money_worth_then": _money(amount / (1 + rate) ** years),
        "lost_purchasing_power_percent": round((1 - 1 / (1 + rate) ** years) * 100, 2),
    })


@register("net-worth-calculator")
def net_worth_calculator(files, text: str, options: dict) -> ToolResult:
    assets = _num(options, "assets", 250000)
    debts = _num(options, "liabilities", 90000)
    return ToolResult(meta={
        "net_worth": _money(assets - debts), "assets": _money(assets), "liabilities": _money(debts),
        "debt_to_asset_percent": round(debts / assets * 100, 2) if assets else 0,
    })


@register("fd-rd-calculator")
def fd_rd_calculator(files, text: str, options: dict) -> ToolResult:
    """Fixed deposit (one lump) or recurring deposit (monthly)."""
    rate = _num(options, "rate", 7)
    years = _num(options, "years", 5)
    if str(options.get("type", "fixed")) == "recurring":
        return ToolResult(meta=_future_value(_num(options, "monthly", 5000), rate, years))
    amount = _num(options, "amount", 100000)
    per_year = max(1, int(_num(options, "compounds_per_year", 4)))
    total = amount * (1 + rate / 100 / per_year) ** (per_year * years)
    return ToolResult(meta={"maturity_amount": _money(total), "interest_earned": _money(total - amount)})


# --- Income & business ------------------------------------------------------

@register("salary-calculator")
def salary_calculator(files, text: str, options: dict) -> ToolResult:
    """Convert a salary between every common pay period."""
    amount = _num(options, "amount", 60000)
    period = str(options.get("period", "year"))
    hours = _num(options, "hours_per_week", 40)
    per_year = {"hour": hours * 52, "day": 260, "week": 52, "month": 12, "year": 1}
    if period not in per_year:
        return ToolResult(meta={"error": "Choose hour, day, week, month or year."})
    annual = amount * per_year[period]
    return ToolResult(meta={
        "annual": _money(annual), "monthly": _money(annual / 12), "weekly": _money(annual / 52),
        "daily": _money(annual / 260), "hourly": _money(annual / (hours * 52)) if hours else 0,
    })


@register("paycheck-calculator")
def paycheck_calculator(files, text: str, options: dict) -> ToolResult:
    """Take-home pay from a gross figure and the deduction rates you enter.

    Rates are inputs rather than built in, because tax bands differ by country
    and a hard-coded table would be wrong for most visitors.
    """
    gross = _num(options, "gross_annual", 60000)
    tax = _num(options, "tax_percent", 20)
    other = _num(options, "other_deductions_percent", 5)
    total_rate = tax + other
    if total_rate >= 100:
        return ToolResult(meta={"error": "Deductions add up to 100% or more."})
    net = gross * (1 - total_rate / 100)
    return ToolResult(meta={
        "net_annual": _money(net), "net_monthly": _money(net / 12), "net_weekly": _money(net / 52),
        "total_deductions": _money(gross - net),
    })


@register("markup-margin-calculator")
def markup_margin_calculator(files, text: str, options: dict) -> ToolResult:
    cost = _num(options, "cost", 60)
    price = _num(options, "price", 100)
    if cost <= 0:
        return ToolResult(meta={"error": "Enter a cost above zero."})
    profit = price - cost
    return ToolResult(meta={
        "profit": _money(profit),
        "markup_percent": round(profit / cost * 100, 2),
        "margin_percent": round(profit / price * 100, 2) if price else 0,
    })


@register("break-even-calculator")
def break_even_calculator(files, text: str, options: dict) -> ToolResult:
    fixed = _num(options, "fixed_costs", 10000)
    price = _num(options, "price_per_unit", 25)
    variable = _num(options, "variable_cost_per_unit", 15)
    contribution = price - variable
    if contribution <= 0:
        return ToolResult(meta={"error": "The price must be higher than the variable cost per unit."})
    units = fixed / contribution
    return ToolResult(meta={
        "break_even_units": round(units, 2), "break_even_revenue": _money(units * price),
        "contribution_per_unit": _money(contribution),
    })


@register("overtime-calculator")
def overtime_calculator(files, text: str, options: dict) -> ToolResult:
    rate = _num(options, "hourly_rate", 20)
    normal = _num(options, "normal_hours", 40)
    overtime = _num(options, "overtime_hours", 8)
    multiplier = _num(options, "overtime_multiplier", 1.5)
    base = rate * normal
    extra = rate * multiplier * overtime
    return ToolResult(meta={
        "base_pay": _money(base), "overtime_pay": _money(extra), "total_pay": _money(base + extra),
        "overtime_rate": _money(rate * multiplier),
    })


@register("commission-calculator")
def commission_calculator(files, text: str, options: dict) -> ToolResult:
    sales = _num(options, "sales", 50000)
    rate = _num(options, "rate", 5)
    base = _num(options, "base_salary", 0)
    commission = sales * rate / 100
    return ToolResult(meta={
        "commission": _money(commission), "total_earnings": _money(base + commission),
        "effective_rate_percent": round((base + commission) / sales * 100, 2) if sales else 0,
    })


# --- Health -----------------------------------------------------------------

@register("tdee-calculator")
def tdee_calculator(files, text: str, options: dict) -> ToolResult:
    """Daily calories, plus targets for losing or gaining weight."""
    result = bmr_calculator(files, text, options).meta
    if "error" in result:
        return ToolResult(meta=result)
    tdee = result["daily_calories"]
    return ToolResult(meta={
        "bmr": result["bmr"], "maintenance_calories": tdee,
        "mild_weight_loss": round(tdee - 250), "weight_loss": round(tdee - 500),
        "weight_gain": round(tdee + 500),
    })


@register("macro-calculator")
def macro_calculator(files, text: str, options: dict) -> ToolResult:
    calories = _num(options, "calories", 2200)
    split = str(options.get("goal", "balanced"))
    ratios = {"balanced": (0.30, 0.40, 0.30), "low carb": (0.40, 0.20, 0.40),
              "high protein": (0.40, 0.35, 0.25), "endurance": (0.20, 0.55, 0.25)}
    if split not in ratios:
        return ToolResult(meta={"error": "Choose balanced, low carb, high protein or endurance."})
    if calories <= 0:
        return ToolResult(meta={"error": "Enter a calorie target above zero."})
    p, c, f = ratios[split]
    # 4 kcal per gram of protein and carbs, 9 per gram of fat.
    return ToolResult(meta={
        "protein_g": round(calories * p / 4), "carbs_g": round(calories * c / 4),
        "fat_g": round(calories * f / 9), "calories": round(calories), "split": split,
    })


@register("pregnancy-due-date-calculator")
def due_date_calculator(files, text: str, options: dict) -> ToolResult:
    """Naegele's rule: 280 days from the last period."""
    from datetime import date, timedelta

    raw = str(options.get("last_period", "")).strip()
    if not raw:
        return ToolResult(meta={"error": "Enter the first day of your last period as YYYY-MM-DD."})
    try:
        lmp = date.fromisoformat(raw)
    except ValueError:
        return ToolResult(meta={"error": "Use the format YYYY-MM-DD."})
    cycle = _num(options, "cycle_length", 28)
    due = lmp + timedelta(days=280 + (cycle - 28))
    elapsed = (date.today() - lmp).days
    return ToolResult(meta={
        "due_date": due.isoformat(), "weekday": due.strftime("%A"),
        "weeks_pregnant": round(max(elapsed, 0) / 7, 1),
        "days_remaining": (due - date.today()).days,
    })


@register("ovulation-calculator")
def ovulation_calculator(files, text: str, options: dict) -> ToolResult:
    from datetime import date, timedelta

    raw = str(options.get("last_period", "")).strip()
    if not raw:
        return ToolResult(meta={"error": "Enter the first day of your last period as YYYY-MM-DD."})
    try:
        lmp = date.fromisoformat(raw)
    except ValueError:
        return ToolResult(meta={"error": "Use the format YYYY-MM-DD."})
    cycle = int(_num(options, "cycle_length", 28))
    if cycle < 20 or cycle > 45:
        return ToolResult(meta={"error": "Cycle length is usually between 20 and 45 days."})
    ovulation = lmp + timedelta(days=cycle - 14)
    return ToolResult(meta={
        "ovulation_date": ovulation.isoformat(),
        "fertile_window": f"{(ovulation - timedelta(days=5)).isoformat()} to {ovulation.isoformat()}",
        "next_period": (lmp + timedelta(days=cycle)).isoformat(),
    })


@register("target-heart-rate-calculator")
def heart_rate_calculator(files, text: str, options: dict) -> ToolResult:
    age = _num(options, "age", 30)
    resting = _num(options, "resting_hr", 65)
    if age <= 0 or age > 120:
        return ToolResult(meta={"error": "Enter an age between 1 and 120."})
    max_hr = 220 - age
    reserve = max_hr - resting
    zone = lambda lo, hi: f"{round(resting + reserve * lo)}–{round(resting + reserve * hi)} bpm"
    return ToolResult(meta={
        "max_heart_rate": round(max_hr),
        "warm_up_50_60": zone(0.5, 0.6), "fat_burn_60_70": zone(0.6, 0.7),
        "cardio_70_80": zone(0.7, 0.8), "peak_80_90": zone(0.8, 0.9),
    })


@register("bac-calculator")
def bac_calculator(files, text: str, options: dict) -> ToolResult:
    """Widmark formula. An estimate only — never a fitness-to-drive test."""
    drinks = _num(options, "standard_drinks", 3)
    kg = _num(options, "weight_kg", 75)
    hours = _num(options, "hours_since", 2)
    if kg <= 0:
        return ToolResult(meta={"error": "Enter a weight above zero."})
    ratio = 0.68 if str(options.get("sex", "male")) == "male" else 0.55
    grams = drinks * 14  # a US standard drink
    bac = max(0.0, grams / (kg * 1000 * ratio) * 100 - 0.015 * hours)
    return ToolResult(meta={
        "estimated_bac_percent": round(bac, 3),
        "note": "An estimate only — many factors change how alcohol is absorbed. Never use it to decide whether to drive.",
    })


@register("sleep-calculator")
def sleep_calculator(files, text: str, options: dict) -> ToolResult:
    """Wake times that land at the end of a 90-minute sleep cycle."""
    from datetime import datetime, timedelta

    raw = str(options.get("bedtime", "23:00")).strip()
    try:
        start = datetime.strptime(raw, "%H:%M")
    except ValueError:
        return ToolResult(meta={"error": "Enter a time as HH:MM, e.g. 23:00."})
    start += timedelta(minutes=14)  # average time to fall asleep
    times = [(start + timedelta(minutes=90 * n)).strftime("%H:%M") for n in range(3, 7)]
    return ToolResult(meta={
        "best_wake_times": times,
        "cycles": "4 to 6 cycles of 90 minutes, allowing ~14 minutes to fall asleep",
    })


# --- More maths -------------------------------------------------------------

@register("scientific-calculator")
def scientific_calculator(files, text: str, options: dict) -> ToolResult:
    """Evaluate an arithmetic expression.

    Parsed into an AST and walked by hand rather than passed to eval(), so a
    visitor can't run arbitrary Python through the box.
    """
    import ast
    import math
    import operator

    expr = str(options.get("expression") or text or "").strip()
    if not expr:
        return ToolResult(meta={"error": "Enter an expression, e.g. 2 * (3 + 4)."})

    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
              ast.FloorDiv: operator.floordiv}
    unary = {ast.UAdd: operator.pos, ast.USub: operator.neg}
    funcs = {n: getattr(math, n) for n in
             ("sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "log", "log10",
              "log2", "exp", "floor", "ceil", "fabs", "degrees", "radians")}
    funcs.update({"abs": abs, "round": round, "min": min, "max": max})
    names = {"pi": math.pi, "e": math.e, "tau": math.tau}

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("only numbers are allowed")
        if isinstance(node, ast.BinOp) and type(node.op) in binary:
            return binary[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in unary:
            return unary[type(node.op)](walk(node.operand))
        if isinstance(node, ast.Name) and node.id in names:
            return names[node.id]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in funcs:
            return funcs[node.func.id](*[walk(a) for a in node.args])
        raise ValueError("that expression isn't supported")

    try:
        value = walk(ast.parse(expr, mode="eval"))
    except ZeroDivisionError:
        return ToolResult(meta={"error": "Division by zero."})
    except (ValueError, TypeError, SyntaxError, OverflowError) as e:
        return ToolResult(meta={"error": f"Could not calculate that: {e}"})
    return ToolResult(meta={"expression": expr, "result": round(value, 10)})


@register("probability-calculator")
def probability_calculator(files, text: str, options: dict) -> ToolResult:
    favourable = _num(options, "favourable", 1)
    total = _num(options, "total", 6)
    trials = int(_num(options, "trials", 1))
    if total <= 0 or favourable < 0 or favourable > total:
        return ToolResult(meta={"error": "Favourable outcomes must be between 0 and the total."})
    p = favourable / total
    return ToolResult(meta={
        "probability": round(p, 6), "percent": round(p * 100, 4),
        "odds": f"{round(favourable)} in {round(total)}",
        "at_least_once_in_trials": round(1 - (1 - p) ** max(trials, 1), 6),
    })


@register("prime-factor-calculator")
def prime_factor_calculator(files, text: str, options: dict) -> ToolResult:
    n = int(_num(options, "number", 360))
    if n < 2:
        return ToolResult(meta={"error": "Enter a whole number of 2 or more."})
    if n > 10_000_000:
        return ToolResult(meta={"error": "Enter a number below 10,000,000."})
    remaining, factors, d = n, [], 2
    while d * d <= remaining:
        while remaining % d == 0:
            factors.append(d)
            remaining //= d
        d += 1
    if remaining > 1:
        factors.append(remaining)
    divisors = sorted(i for i in range(1, int(n ** 0.5) + 1) if n % i == 0)
    divisors += [n // i for i in reversed(divisors) if i != n // i]
    return ToolResult(meta={
        "number": n, "is_prime": len(factors) == 1,
        "prime_factors": factors,
        "factorisation": " × ".join(map(str, factors)),
        "divisors": sorted(set(divisors)),
    })


@register("random-number-generator")
def random_number_generator(files, text: str, options: dict) -> ToolResult:
    import random

    lo, hi = int(_num(options, "min", 1)), int(_num(options, "max", 100))
    count = max(1, min(int(_num(options, "count", 5)), 1000))
    if lo > hi:
        lo, hi = hi, lo
    unique = bool(options.get("unique", False))
    if unique and hi - lo + 1 < count:
        return ToolResult(meta={"error": "That range is too small for this many unique numbers."})
    numbers = random.sample(range(lo, hi + 1), count) if unique else [random.randint(lo, hi) for _ in range(count)]
    return ToolResult(meta={"numbers": numbers, "count": count, "range": f"{lo} to {hi}"})


@register("number-base-converter")
def number_base_converter(files, text: str, options: dict) -> ToolResult:
    raw = str(options.get("value", "255")).strip()
    from_base = int(_num(options, "from_base", 10))
    if not 2 <= from_base <= 36:
        return ToolResult(meta={"error": "The base must be between 2 and 36."})
    try:
        value = int(raw, from_base)
    except ValueError:
        return ToolResult(meta={"error": f"'{raw}' isn't a valid base-{from_base} number."})

    def to_base(n: int, base: int) -> str:
        if n == 0:
            return "0"
        digits, sign = "", "-" if n < 0 else ""
        n = abs(n)
        while n:
            digits = "0123456789abcdefghijklmnopqrstuvwxyz"[n % base] + digits
            n //= base
        return sign + digits

    target = int(_num(options, "to_base", 2))
    if not 2 <= target <= 36:
        return ToolResult(meta={"error": "The target base must be between 2 and 36."})
    return ToolResult(meta={
        "decimal": value, "binary": to_base(value, 2), "octal": to_base(value, 8),
        "hexadecimal": to_base(value, 16), "result": to_base(value, target),
    })


@register("slope-calculator")
def slope_calculator(files, text: str, options: dict) -> ToolResult:
    import math

    x1, y1 = _num(options, "x1", 0), _num(options, "y1", 0)
    x2, y2 = _num(options, "x2", 4), _num(options, "y2", 3)
    dx, dy = x2 - x1, y2 - y1
    out = {
        "distance": round(math.hypot(dx, dy), 6),
        "midpoint": f"({round((x1 + x2) / 2, 4)}, {round((y1 + y2) / 2, 4)})",
    }
    if dx == 0:
        out["slope"] = "undefined (vertical line)"
    else:
        slope = dy / dx
        out["slope"] = round(slope, 6)
        out["equation"] = f"y = {round(slope, 4)}x + {round(y1 - slope * x1, 4)}"
    return ToolResult(meta=out)


# --- Geometry & engineering -------------------------------------------------

@register("perimeter-calculator")
def perimeter_calculator(files, text: str, options: dict) -> ToolResult:
    import math

    shape = str(options.get("shape", "rectangle"))
    a, b = _num(options, "a", 10), _num(options, "b", 5)
    if a <= 0:
        return ToolResult(meta={"error": "Enter measurements above zero."})
    values = {"rectangle": 2 * (a + b), "square": 4 * a, "circle": 2 * math.pi * a,
              "triangle": a + b + _num(options, "c", 7)}
    if shape not in values:
        return ToolResult(meta={"error": "Choose rectangle, square, circle or triangle."})
    key = "circumference" if shape == "circle" else "perimeter"
    return ToolResult(meta={"shape": shape, key: round(values[shape], 6)})


@register("triangle-calculator")
def triangle_calculator(files, text: str, options: dict) -> ToolResult:
    """Area, perimeter and angles from three sides (Heron + law of cosines)."""
    import math

    a, b, c = _num(options, "a", 3), _num(options, "b", 4), _num(options, "c", 5)
    if min(a, b, c) <= 0:
        return ToolResult(meta={"error": "All three sides must be above zero."})
    if a + b <= c or a + c <= b or b + c <= a:
        return ToolResult(meta={"error": "Those sides cannot form a triangle."})
    s = (a + b + c) / 2
    area = math.sqrt(s * (s - a) * (s - b) * (s - c))
    ang = lambda o, p, q: math.degrees(math.acos(max(-1, min(1, (p * p + q * q - o * o) / (2 * p * q)))))
    angles = [round(ang(a, b, c), 2), round(ang(b, a, c), 2), round(ang(c, a, b), 2)]
    return ToolResult(meta={
        "area": round(area, 6), "perimeter": round(a + b + c, 6), "angles_degrees": angles,
        "type": "right" if any(abs(x - 90) < 0.01 for x in angles) else
                "equilateral" if a == b == c else "isosceles" if len({a, b, c}) == 2 else "scalene",
    })


@register("ohms-law-calculator")
def ohms_law_calculator(files, text: str, options: dict) -> ToolResult:
    """Fill in any two of volts, amps and ohms; the rest are derived."""
    v, i, r = _num(options, "volts", 0), _num(options, "amps", 0), _num(options, "ohms", 0)
    known = sum(1 for x in (v, i, r) if x)
    if known < 2:
        return ToolResult(meta={"error": "Enter any two of volts, amps and ohms."})
    if not v:
        v = i * r
    elif not i:
        if r == 0:
            return ToolResult(meta={"error": "Resistance cannot be zero."})
        i = v / r
    elif not r:
        if i == 0:
            return ToolResult(meta={"error": "Current cannot be zero."})
        r = v / i
    return ToolResult(meta={
        "volts": round(v, 6), "amps": round(i, 6), "ohms": round(r, 6), "watts": round(v * i, 6),
    })


@register("resistor-color-code-calculator")
def resistor_color_calculator(files, text: str, options: dict) -> ToolResult:
    digits = {"black":0,"brown":1,"red":2,"orange":3,"yellow":4,
              "green":5,"blue":6,"violet":7,"grey":8,"white":9}
    multipliers = {**{k: 10 ** v for k, v in digits.items()}, "gold": 0.1, "silver": 0.01}
    tolerances = {"brown":1,"red":2,"green":0.5,"blue":0.25,"violet":0.1,"gold":5,"silver":10}
    b1 = str(options.get("band1", "brown")).lower()
    b2 = str(options.get("band2", "black")).lower()
    b3 = str(options.get("multiplier", "red")).lower()
    b4 = str(options.get("tolerance", "gold")).lower()
    if b1 not in digits or b2 not in digits:
        return ToolResult(meta={"error": f"The first two bands must be one of: {', '.join(digits)}"})
    if b3 not in multipliers:
        return ToolResult(meta={"error": "The multiplier band isn't a known colour."})
    ohms = (digits[b1] * 10 + digits[b2]) * multipliers[b3]
    unit = f"{ohms/1e6:g} MΩ" if ohms >= 1e6 else f"{ohms/1e3:g} kΩ" if ohms >= 1e3 else f"{ohms:g} Ω"
    return ToolResult(meta={
        "resistance_ohms": round(ohms, 4), "resistance": unit,
        "tolerance_percent": tolerances.get(b4, "unknown"),
    })


# --- More units -------------------------------------------------------------

_UNITS["pressure"] = {"Pa": 1.0, "kPa": 1000.0, "bar": 100000.0, "psi": 6894.757293,
                      "atm": 101325.0, "mmHg": 133.322387415}
_UNITS["energy"] = {"J": 1.0, "kJ": 1000.0, "cal": 4.184, "kcal": 4184.0,
                    "Wh": 3600.0, "kWh": 3600000.0, "BTU": 1055.05585262}
_UNITS["power"] = {"W": 1.0, "kW": 1000.0, "MW": 1e6, "hp": 745.699872}


@register("pressure-converter")
def pressure_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_convert("pressure", options))


@register("energy-converter")
def energy_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_convert("energy", options))


@register("power-converter")
def power_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_convert("power", options))


@register("fuel-economy-converter")
def fuel_economy_converter(files, text: str, options: dict) -> ToolResult:
    """mpg and L/100km are inverses of each other, so this can't use the
    multiply-by-a-factor table the other converters share."""
    value = _num(options, "value", 30)
    src = str(options.get("from", "mpg (US)"))
    if value <= 0:
        return ToolResult(meta={"error": "Enter a value above zero."})
    # Everything goes via km per litre.
    to_kmpl = {"mpg (US)": 0.425143707, "mpg (UK)": 0.354006189, "km/l": 1.0}
    if src == "L/100km":
        kmpl = 100 / value
    elif src in to_kmpl:
        kmpl = value * to_kmpl[src]
    else:
        return ToolResult(meta={"error": "Choose mpg (US), mpg (UK), km/l or L/100km."})
    return ToolResult(meta={
        "km_per_litre": round(kmpl, 3), "litres_per_100km": round(100 / kmpl, 3),
        "mpg_us": round(kmpl / 0.425143707, 3), "mpg_uk": round(kmpl / 0.354006189, 3),
    })


@register("cooking-converter")
def cooking_converter(files, text: str, options: dict) -> ToolResult:
    return ToolResult(meta=_convert("volume", options))


@register("shoe-size-converter")
def shoe_size_converter(files, text: str, options: dict) -> ToolResult:
    """Approximate conversion — brands differ, so this is a starting point."""
    size = _num(options, "size", 9)
    region = str(options.get("from", "US men"))
    # Normalise everything to EU.
    to_eu = {"US men": lambda s: s + 33, "US women": lambda s: s + 31,
             "UK": lambda s: s + 34, "EU": lambda s: s}
    if region not in to_eu:
        return ToolResult(meta={"error": "Choose US men, US women, UK or EU."})
    eu = to_eu[region](size)
    return ToolResult(meta={
        "eu": round(eu, 1), "us_men": round(eu - 33, 1), "us_women": round(eu - 31, 1),
        "uk": round(eu - 34, 1), "cm": round((eu - 2) / 1.5, 1),
        "note": "Approximate — sizing varies between brands.",
    })


# --- More everyday ----------------------------------------------------------

@register("grade-calculator")
def grade_calculator(files, text: str, options: dict) -> ToolResult:
    """Weighted final grade, and what the last assessment needs to score."""
    import re as _re

    scores = [float(x) for x in _re.findall(r"-?\d+(?:\.\d+)?", str(options.get("scores", "85, 90, 78")))]
    weights = [float(x) for x in _re.findall(r"-?\d+(?:\.\d+)?", str(options.get("weights", "30, 30, 40")))]
    if not scores:
        return ToolResult(meta={"error": "Enter your scores, separated by commas."})
    if len(weights) != len(scores):
        weights = [1.0] * len(scores)
    total_weight = sum(weights)
    if total_weight <= 0:
        return ToolResult(meta={"error": "Weights must add up to more than zero."})
    current = sum(s * w for s, w in zip(scores, weights)) / total_weight
    out = {"current_grade": round(current, 2), "assessments": len(scores)}
    target = _num(options, "target_grade", 0)
    remaining = _num(options, "remaining_weight", 0)
    if target and remaining:
        needed = (target * (total_weight + remaining) - current * total_weight) / remaining
        out["needed_on_remaining"] = round(needed, 2)
        out["achievable"] = needed <= 100
    return ToolResult(meta=out)


@register("split-bill-calculator")
def split_bill_calculator(files, text: str, options: dict) -> ToolResult:
    bill = _num(options, "bill", 120)
    people = max(1, int(_num(options, "people", 4)))
    tip = _num(options, "tip_percent", 10)
    tax = _num(options, "tax_percent", 0)
    total = bill * (1 + tax / 100) * (1 + tip / 100)
    return ToolResult(meta={
        "total": _money(total), "per_person": _money(total / people),
        "tip_amount": _money(bill * (1 + tax / 100) * tip / 100), "people": people,
    })


@register("mileage-calculator")
def mileage_calculator(files, text: str, options: dict) -> ToolResult:
    distance = _num(options, "distance", 1200)
    rate = _num(options, "rate_per_km", 0.45)
    return ToolResult(meta={
        "reimbursement": _money(distance * rate), "distance": distance, "rate": rate,
    })


@register("concrete-calculator")
def concrete_calculator(files, text: str, options: dict) -> ToolResult:
    length = _num(options, "length_m", 5)
    width = _num(options, "width_m", 3)
    depth = _num(options, "depth_cm", 10) / 100
    waste = _num(options, "waste_percent", 10)
    if min(length, width, depth) <= 0:
        return ToolResult(meta={"error": "Enter measurements above zero."})
    volume = length * width * depth * (1 + waste / 100)
    return ToolResult(meta={
        "volume_m3": round(volume, 3), "bags_25kg": round(volume * 2400 / 25 + 0.5),
        "approx_weight_kg": round(volume * 2400),
    })


@register("tile-calculator")
def tile_calculator(files, text: str, options: dict) -> ToolResult:
    area = _num(options, "area_m2", 20)
    tile_w = _num(options, "tile_width_cm", 30) / 100
    tile_h = _num(options, "tile_height_cm", 30) / 100
    waste = _num(options, "waste_percent", 10)
    if area <= 0 or tile_w <= 0 or tile_h <= 0:
        return ToolResult(meta={"error": "Enter an area and tile size above zero."})
    per_tile = tile_w * tile_h
    tiles = area / per_tile * (1 + waste / 100)
    return ToolResult(meta={
        "tiles_needed": round(tiles + 0.5), "tile_area_m2": round(per_tile, 4),
        "includes_waste_percent": waste,
    })


@register("carbon-footprint-calculator")
def carbon_footprint_calculator(files, text: str, options: dict) -> ToolResult:
    """Rough annual CO2 from the three biggest household sources."""
    car_km = _num(options, "car_km_per_year", 12000)
    electricity = _num(options, "electricity_kwh_per_month", 300)
    flights = _num(options, "flight_hours_per_year", 10)
    # kg CO2e per unit — typical averages.
    car = car_km * 0.171
    power = electricity * 12 * 0.233
    air = flights * 90
    total = car + power + air
    return ToolResult(meta={
        "total_kg_co2_per_year": round(total), "tonnes_per_year": round(total / 1000, 2),
        "car_kg": round(car), "electricity_kg": round(power), "flights_kg": round(air),
        "trees_to_offset": round(total / 21),
    })


@register("dice-roller")
def dice_roller(files, text: str, options: dict) -> ToolResult:
    import random

    sides = max(2, int(_num(options, "sides", 6)))
    count = max(1, min(int(_num(options, "count", 2)), 100))
    rolls = [random.randint(1, sides) for _ in range(count)]
    return ToolResult(meta={
        "rolls": rolls, "total": sum(rolls), "highest": max(rolls), "lowest": min(rolls),
        "dice": f"{count}d{sides}",
    })


# --- More time --------------------------------------------------------------

@register("time-duration-calculator")
def time_duration_calculator(files, text: str, options: dict) -> ToolResult:
    from datetime import datetime, timedelta

    try:
        start = datetime.strptime(str(options.get("start_time", "09:00")).strip(), "%H:%M")
        end = datetime.strptime(str(options.get("end_time", "17:30")).strip(), "%H:%M")
    except ValueError:
        return ToolResult(meta={"error": "Enter times as HH:MM, e.g. 09:00."})
    if end < start:
        end += timedelta(days=1)
    total = (end - start).total_seconds()
    return ToolResult(meta={
        "hours": round(total / 3600, 2), "minutes": round(total / 60),
        "formatted": f"{int(total // 3600)}h {int(total % 3600 // 60)}m",
    })


@register("time-calculator")
def time_calculator(files, text: str, options: dict) -> ToolResult:
    """Add or subtract hours and minutes from a time."""
    from datetime import datetime, timedelta

    try:
        base = datetime.strptime(str(options.get("time", "14:30")).strip(), "%H:%M")
    except ValueError:
        return ToolResult(meta={"error": "Enter a time as HH:MM, e.g. 14:30."})
    delta = timedelta(hours=_num(options, "hours", 2), minutes=_num(options, "minutes", 45))
    if str(options.get("operation", "add")) == "subtract":
        delta = -delta
    result = base + delta
    return ToolResult(meta={"result": result.strftime("%H:%M"), "12_hour": result.strftime("%I:%M %p").lstrip("0")})


@register("timezone-converter")
def timezone_converter(files, text: str, options: dict) -> ToolResult:
    """Uses Python's bundled tz database — no network lookup."""
    from datetime import datetime
    from zoneinfo import ZoneInfo, available_timezones

    src = str(options.get("from_zone", "UTC")).strip()
    dst = str(options.get("to_zone", "Asia/Karachi")).strip()
    zones = available_timezones()
    missing = [z for z in (src, dst) if z not in zones]
    if missing:
        return ToolResult(meta={"error": f"Unknown time zone: {', '.join(missing)}. Use names like Asia/Karachi."})
    raw = str(options.get("datetime", "")).strip()
    try:
        when = datetime.fromisoformat(raw) if raw else datetime.now()
    except ValueError:
        return ToolResult(meta={"error": "Enter the time as YYYY-MM-DD HH:MM."})
    converted = when.replace(tzinfo=ZoneInfo(src)).astimezone(ZoneInfo(dst))
    return ToolResult(meta={
        "source": f"{when.strftime('%Y-%m-%d %H:%M')} {src}",
        "converted": f"{converted.strftime('%Y-%m-%d %H:%M')} {dst}",
        "offset_hours": round(converted.utcoffset().total_seconds() / 3600, 2),
    })
