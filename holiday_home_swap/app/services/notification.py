import boto3
from app.config import settings
from botocore.exceptions import ClientError


class EmailService:
    def __init__(self):
        self.ses_client = boto3.client('ses', region_name=settings.AWS_REGION)
        self.sender = settings.SES_SENDER_EMAIL

    def send_match_notification(self, user_email: str, user_name: str, match_location: str):
        """Send email notification for new match"""
        if not self.sender:
            print("SES sender email not configured, skipping email notification")
            return False
            
        subject = "New Home Swap Match Found!!"
        body_text = f"""Hello {user_name},

Great news! We found a potential home swap match for you in {match_location}.

Log in to your account to view the match details and connect with the other homeowner.

Happy swapping!
"""
        try:
            response = self.ses_client.send_email(
                Source=self.sender,
                Destination={'ToAddresses': [user_email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Text': {'Data': body_text}}
                }
            )
            print(f"Email sent! Message ID: {response['MessageId']}")
            return True
        except ClientError as e:
            print(f"Error sending email: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error sending email: {e}")
            return False

email_service = EmailService()