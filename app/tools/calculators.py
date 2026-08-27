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
