from django.core.mail import EmailMessage
import threading
import requests
from django.conf import settings


class EmailThread(threading.Thread):

    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send()


class Util:
    @staticmethod
    def send_email(data):
        email = EmailMessage(
            subject=data['email_subject'], body=data['email_body'], to=[data['to_email']])
        EmailThread(email).start()


def send_otp(to):
    url = "https://control.msg91.com/api/v5/otp"
    params = {
        "authkey": settings.MSG91_API_KEY,
        "template_id": settings.MSG91_OTP_TEMPLATE_ID,
        "mobile": to,
        "otp_length": 6,
    }
    response = requests.post(url, params=params)
    print(response.text)
    data = response.json()
    return data


def verify_otp(to, otp_entered_by_user):
    url = "https://control.msg91.com/api/v5/otp/verify"
    headers = {
        "accept": "application/json",
        "authkey": settings.MSG91_API_KEY
    }
    params = {
        "mobile": str(to),
        "otp": str(otp_entered_by_user),
    }
    response = requests.post(url, params=params, headers=headers)
    data = response.json()
    return data


def send_custom_sms(to, student_name, adm_no, exam_name, date, marks):
    url = "https://control.msg91.com/api/v5/flow"  
    headers = {
        "authkey": settings.MSG91_API_KEY,
        "content-type": "application/json"
    }
    payload = {
        "template_id": "67591057d6fc054ffb759f72", 
        "recipients": [
            {
            "mobiles": to,  
            "var1": student_name,
            "var2": date
            }
        ]
    }
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    return data