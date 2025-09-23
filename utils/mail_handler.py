from flask_mail import Mail, Message

class MailSender:
    def __init__(self, app=None):
        self.mail = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.mail = Mail(app)

    def send_email(self, subject, html_body, recipient):
        if not self.mail:
            return "Mail not initialized"
        
        msg = Message(
            subject=subject,
            recipients=[recipient],
            html=html_body,
            sender="no-reply@fast.bi"
        )
        try:
            self.mail.send(msg)
            return "Email sent successfully"
        except Exception as e:
            return f"Failed to send email: {str(e)}"