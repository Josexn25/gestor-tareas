import resend
from flask import current_app


def build_email_html(title, intro, link=None, button_text=None, footer=""):
    """Crea el HTML base para correos transaccionales."""
    button_html = ""
    link_html = ""

    if link and button_text:
        button_html = (
            f'<a href="{link}" style="display:inline-block;background:#5eead4;color:#05201c;'
            'text-decoration:none;font-weight:800;padding:13px 18px;border-radius:14px;">'
            f"{button_text}</a>"
        )
        link_html = (
            '<p style="margin:16px 0 0;color:#737b8c;font-size:12px;line-height:1.5;word-break:break-all;">'
            f"{link}</p>"
        )

    return f"""
    <div style="margin:0;padding:32px;background:#0b0d12;color:#f8fafc;font-family:Arial,sans-serif;">
      <div style="max-width:560px;margin:0 auto;background:#12151d;border:1px solid rgba(255,255,255,.08);border-radius:20px;padding:28px;">
        <p style="margin:0 0 12px;color:#5eead4;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">Gestor de tareas</p>
        <h1 style="margin:0 0 14px;font-size:28px;line-height:1.15;color:#f8fafc;">{title}</h1>
        <p style="margin:0 0 22px;color:#a3aab7;font-size:16px;line-height:1.55;">{intro}</p>
        {button_html}
        <p style="margin:22px 0 0;color:#a3aab7;font-size:13px;line-height:1.5;">{footer}</p>
        {link_html}
      </div>
    </div>
    """


def send_email(to_email, subject, text_body, html_body):
    """Envia un email transaccional con Resend API."""
    api_key = current_app.config.get("RESEND_API_KEY")

    if not api_key:
        current_app.logger.warning("RESEND_API_KEY no configurada. Email pendiente para %s: %s", to_email, text_body)
        return False

    resend.api_key = api_key

    try:
        resend.Emails.send(
            {
                "from": "onboarding@resend.dev",
                "to": [to_email],
                "subject": subject,
                "text": text_body,
                "html": html_body,
            }
        )
        return True
    except Exception:
        current_app.logger.exception("Resend no pudo enviar email a %s", to_email)
        return False
