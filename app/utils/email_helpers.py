from datetime import date, datetime, timedelta


def f_date(date_value: date | None) -> str:
    if date_value is None:
        return "Not specified"
    return date_value.strftime("%B %d, %Y")


def f_datetime(datetime_value: datetime | None) -> str:
    if datetime_value is None:
        return "Not specified"
    return datetime_value.strftime("%B %d, %Y at %H:%M")


def f_boolean_r(bool_value: bool | None) -> str:
    if bool_value is None:
        return "Not specified"
    return "Required" if bool_value else "Not Required"


def f_boolean_yn(bool_value: bool | None) -> str:
    if bool_value is None:
        return "Not specified"
    return "Yes" if bool_value else "No"


def safe_format(template: str, **kwargs) -> str:
    safe_kwargs = {}
    for key, value in kwargs.items():
        if value is None:
            safe_kwargs[key] = ""
        else:
            safe_kwargs[key] = str(value)
    return template.format(**safe_kwargs)
