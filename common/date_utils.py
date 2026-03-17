from datetime import datetime, timezone

def format_date(dt):
    return {
        "date_object": dt.date(),
        "date_ymd_compact": dt.strftime('%Y%m%d'),
        "date_dot_padded": dt.strftime('%Y.%m.%d'),
        "date_dash_padded": dt.strftime('%Y-%m-%d'),
        "date_slash_padded": dt.strftime('%Y/%m/%d'),
        "date_jp_padded": dt.strftime('%Y年%m月%d日'),
        "date_dot_unpadded": f"{dt.year}.{dt.month}.{dt.day}",
        "date_dash_unpadded": f"{dt.year}-{dt.month}-{dt.day}",
        "date_slash_unpadded": f"{dt.year}/{dt.month}/{dt.day}",
        "date_kr": f"{dt.year}년 {dt.month:02}월 {dt.day:02}일",
        "start_of_day": dt.replace(hour=0, minute=0, second=0, microsecond=0),
        "unixtime": int(dt.timestamp()),
        "unixtime_ms": int(dt.timestamp() * 1000),
        "date_iso": dt.date().isoformat(),
        "datetime_iso": dt.isoformat()
    }

def get_today_date():
    now_local = datetime.now()
    now_utc = datetime.now(timezone.utc)

    return {
        "local": format_date(now_local),
        "utc": format_date(now_utc)
    }