from datetime import timedelta

def format_timedelta(td: timedelta) -> str:
    """Convert timedelta to human-readable format"""
    total_seconds = int(td.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:  # Show seconds if nothing else
        parts.append(f"{seconds}s")
    
    return " ".join(parts)
