from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr
from typing import Tuple, Optional, Dict, Any
import resend

from app.db.database import SessionLocal
from app.models.user import User
from app.templates import load_template, STYLES_CSS
from app.core.config import MAIL_FROM, MAIL_FROM_NAME
from app.utils.email_helpers import safe_format
from app.utils.logger import logger_instance as log
from app.enums.enums import EmailType


def _build_on_create_user_email_data(
    user: User,
    temporary_password: Optional[str] = None,
) -> Tuple[list[EmailStr], str, str]:

    if user.email is None:
        return None, None, None

    recipients = [user.email]
    subject = f"Bienvenido a orgs_name Data {user.nombres + ' ' + user.apellidos}"
    template = load_template("email_on_create_user.html")
    email_body = safe_format(
        template,
        email_styles=STYLES_CSS,
        user_name=user.nombres + " " + user.apellidos,
        user_email=user.email,
        user_password=temporary_password,
    )

    return recipients, subject, email_body


def _build_on_reset_password_email_data(
    user: User,
    temporary_password: Optional[str] = None,
) -> Tuple[list[EmailStr], str, str]:

    if user.email is None:
        return None, None, None

    recipients = [user.email]
    subject = f"Tu Contraseña ha sido Restablecida por un Adminstrador {user.nombres + ' ' + user.apellidos}"
    template = load_template("email_on_reset_password.html")
    email_body = safe_format(
        template,
        email_styles=STYLES_CSS,
        user_name=user.nombres + " " + user.apellidos,
        user_email=user.email,
        user_password=temporary_password,
    )

    return recipients, subject, email_body


def _build_email_message(
    user: User,
    email_type: EmailType,
    temporary_password: Optional[str] = None,
) -> Dict[str, Any] | None:

    if email_type == EmailType.create_user:
        recipients, subject, email_body = _build_on_create_user_email_data(
            user, temporary_password
        )
    elif email_type == EmailType.reset_password:
        recipients, subject, email_body = _build_on_reset_password_email_data(
            user, temporary_password
        )
    else:
        log.error(f"Unknown email type: {email_type}")
        return None

    if not recipients or not subject or not email_body:
        return None

    # Resend email parameters
    params: resend.Emails.SendParams = {
        "from": f"{MAIL_FROM_NAME} <{MAIL_FROM}>",
        "to": recipients,
        "subject": subject,
        "html": email_body,
    }

    return params


async def send_email(
    user_id: int,
    temporary_password: Optional[str] = None,
    email_type: EmailType = EmailType.create_user,
) -> bool:
    """
    Envía un email al usuario.

    Args:
        user_id: ID del usuario
        temporary_password: Contraseña temporal sin hashear (solo para nuevos usuarios o resets)
        email_type: Tipo de email a enviar (EmailType.create_user o EmailType.reset_password)
    """
    db: AsyncSession
    async with SessionLocal() as db:
        try:
            result = await db.execute(select(User).where(User.id == user_id))

            user = result.scalar_one_or_none()

            if user is None:
                log.error("User not found")
                return False

            params = _build_email_message(user, email_type, temporary_password)

            if params is None:
                log.error("Could not build message for email")
                return False

            # Send email using Resend
            email_response = resend.Emails.send(params)

            log.info(
                f"Email sent successfully",
                extra={
                    "user_id": user_id,
                    "email_type": email_type,
                    "email_id": email_response.get("id"),
                    "recipients": params["to"],
                },
            )
            return True

        except Exception as e:
            log.error(
                f"Failed to send email",
                extra={
                    "user_id": user_id,
                    "email_type": email_type,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            return False
