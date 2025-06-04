from main import logger

def log_action(message: str):
    """Simple logging function to replace print statements
    
    Args:
        message: The message to log
    """
    
    # Log the message with timestamp
    logger.info(message)

# Example usage
if __name__ == "__main__":
    log_action("Application started")
    log_action("User logged in", "info")
    log_action("Failed login attempt", "warning")
    log_action("Database connection error", "error")
