from __future__ import annotations

from datetime import datetime, timedelta

_CACHE = {}

TTL_MINUTES = 15

def get(key):
    item=_CACHE.get(key)
    if not item:
        return None
    expires,value=item
    if datetime.utcnow()>expires:
        _CACHE.pop(key,None)
        return None
    return value

def set(key,value):
    _CACHE[key]=(datetime.utcnow()+timedelta(minutes=TTL_MINUTES),value)

def clear():
    _CACHE.clear()

def stats():
    return {
        "items":len(_CACHE),
        "ttl_minutes":TTL_MINUTES,
    }
