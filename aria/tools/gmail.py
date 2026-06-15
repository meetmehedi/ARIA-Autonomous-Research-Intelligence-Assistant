import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(subject: str, body: str, to_email: str = None) -> bool:
    """Drafts and sends an email. 
    
    If SMTP variables are not configured in the environment, it prints the 
    draft to stdout as a fallback.
    """
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    default_to = os.getenv("EMAIL_RECEIVER", "meetmehedi1@gmail.com")
    
    target_to = to_email if to_email else default_to
    
    # Check if credentials are present, else print draft fallback
    if not smtp_server or not smtp_user or not smtp_pass:
        print("\n=== DRAFT EMAIL GENERATED ===")
        print(f"To: {target_to}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body}")
        print("=============================")
        print("Note: SMTP configuration not set in .env. Mocking delivery.")
        return True
        
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = target_to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, target_to, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email to {target_to} via SMTP: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    print("Gmail/SMTP helper tool loaded.")
