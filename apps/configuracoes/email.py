from django.core.mail import EmailMessage
from django.conf import settings


class EmailService:

    @staticmethod
    def send_email(subject: str, body: str, to: list, html: bool = False):
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
        )

        if html:
            email.content_subtype = "html"

        return email.send()

    @staticmethod
    def send_email_contrstos_pdf(subject: str, body: str, to: list, pdf, html: bool = False):
        email = EmailMessage(
            subject=subject,
            body=f"",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=to,
        )

        if html:
            email.content_subtype = "html"

        # Anexa o PDF recebido do frontend
        email.attach(pdf.name, pdf.read(), 'application/pdf')

        return email.send()

    @staticmethod
    def send_welcome_email(user):
        subject = "Bem-vindo(a) ao nosso sistema!"
        body = f"Olá {user.nome}, bem-vindo(a) ao nosso sistema!"
        to = [user.email]
        html = True

        EmailService.send_email(subject, body, to, html)

    @staticmethod
    def send_emai_intervencao():
        pass
