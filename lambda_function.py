"""
Alias to lambda_handler.py for AWS Lambda compatibility
AWS Lambda defaults to looking for lambda_function.py
"""

from lambda_handler import handler as lambda_handler

# AWS Lambda will call this
__all__ = ["lambda_handler"]
