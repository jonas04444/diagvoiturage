"""Conversions entre heures « HH:MM » et minutes depuis minuit."""


def time_to_minutes(time_str):
    """'08:30' -> 510"""
    heures, minutes = map(int, time_str.split(':'))
    return heures * 60 + minutes


def minutes_to_time(minutes):
    """510 -> '08h30'"""
    return f"{minutes // 60:02d}h{minutes % 60:02d}"
