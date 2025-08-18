import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Sender credentials
sender_email = "vmoperations3@gmail.com"
password = "tucq kspl jryl brnv"

# List of recipient emails
recipient_emails = [
    "matinaryan06@gmail.com",
    "shirohskates@gmail.com"
]

# Email subject and body template
subject_template = "Hello, {name}!"
body_template = """To all Vending Machine Admins,

The vending machine requires assistance as its temeperature has fallen out of the optimal range.

Best regards,
The Team at DevOps Vending Machine
"""

# Loop through each recipient and send a personalized email
for recipient in recipient_emails:
    # Extract name from email (before the @)
    name = recipient.split("@")[0]

    # Create a fresh message for this recipient
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient
    message["Subject"] = subject_template.format(name=name.capitalize())

    # Personalize the email body
    body = body_template.format(name=name.capitalize())
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient, message.as_string())
            print(f"Email sent to {recipient}")
    except Exception as e:
        print(f"Error sending to {recipient}: {e}")