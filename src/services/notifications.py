import logging
import smtplib
from email.message import EmailMessage

from src.core.config import Settings

logger = logging.getLogger(__name__)


def send_task_created(settings: Settings, recipient: str, task_id: int, title: str) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message["Subject"] = f"Создана задача №{task_id}"
    message.set_content(f"В вашей учётной записи создана задача №{task_id}.\n\n{title}")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=5) as smtp:
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("SMTP delivery failed for task %s", task_id)
