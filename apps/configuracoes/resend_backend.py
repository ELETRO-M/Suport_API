import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        resend.api_key = getattr(settings, "RESEND_API_KEY", "")
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "onboarding@resend.dev")

        count = 0
        for message in email_messages:
            try:
                to_list = message.to or []
                if not to_list:
                    continue

                params = {
                    "from": from_email,
                    "to": to_list,
                    "subject": message.subject or "",
                    "html": message.body if getattr(message, "content_subtype", "plain") == "html" else None,
                    "text": message.body if getattr(message, "content_subtype", "plain") == "plain" else message.body,
                }

                # If message has alternatives, prefer html
                if hasattr(message, "alternatives") and message.alternatives:
                    for content, mimetype in message.alternatives:
                        if mimetype == "text/html":
                            params["html"] = content
                            break
                    else:
                        if params["html"] is None:
                            params["html"] = message.body

                if params["html"] is None and params.get("text") is None:
                    params["text"] = message.body or ""

                resend.Emails.send(params)
                count += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return count
