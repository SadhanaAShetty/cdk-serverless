import boto3
from app.config import settings
from botocore.exceptions import ClientError


class EmailService:
    def __init__(self):
        self.ses_client = None
        self.sender = None

    def initialize(self, profile_name: str = None):
        """Initialize SES client with proper credentials"""
        if profile_name:
            print(f"Initializing SES with profile: {profile_name}")
            session = boto3.Session(profile_name=profile_name)
            self.ses_client = session.client('ses', region_name=settings.AWS_REGION)
        else:
            print(" Initializing SES with default credentials")
            self.ses_client = boto3.client('ses', region_name=settings.AWS_REGION)
        
        self.sender = settings.SES_SENDER_EMAIL
        print(f" SES sender email: {self.sender}")

    def send_match_notification(self, user_email: str, user_name: str, match_location: str):
        """Send email notification for new match"""
        if not self.ses_client:
            print(" SES client not initialized")
            return False
            
        if not self.sender:
            print(" SES sender email not configured, skipping email notification")
            return False
            
        subject = "New Home Swap Match Found!!"
        body_text = f"""Hello {user_name},

Great news! We found a potential home swap match for you in {match_location}.

Log in to your account to view the match details and connect with the other homeowner.

Happy swapping!
"""
        try:
            print(f" Sending email from {self.sender} to {user_email}")
            response = self.ses_client.send_email(
                Source=self.sender,
                Destination={'ToAddresses': [user_email]},
                Message={
                    'Subject': {'Data': subject},
                    'Body': {'Text': {'Data': body_text}}
                }
            )
            print(f" Email sent! Message ID: {response['MessageId']}")
            return True
        except ClientError as e:
            print(f"AWS Error sending email: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error sending email: {e}")
            return False

email_service = EmailService()