from rest_framework import status
from rest_framework.response import Response

# Success Messages
SUCCESS_OTP_SENT = "OTP sent successfully."
SUCCESS_VERIFICATION = "OTP verified successfully."

# Error Messages
ERROR_PHONE_REQUIRED = "Phone number is required."
ERROR_USER_NOT_FOUND = "User not found or phone number is already verified."
ERROR_OTP_SEND_FAILED = "Failed to send OTP. Please try again."
ERROR_INVALID_OTP = "Invalid OTP. Try again."
ERROR_OTP_EXPIRED = "OTP has expired. Please request a new OTP."
ERROR_GENERIC = "An error occurred. Please try again."

# Response Handlers
def success_response(message, data=None):
    return Response({
        "message": message,
        "data": data
    }, status=status.HTTP_200_OK)


def error_response(message, code=status.HTTP_400_BAD_REQUEST, data=None):
    return Response({
        "error": message,
        "data": data
    }, status=code)

