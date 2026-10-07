"""Authentication service."""
import hashlib
import hmac
import secrets
import time

from app.config import PASSWORD_MIN_LENGTH, MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_SECONDS
from app.services.settings_service import settings


class AuthError(Exception):
    pass


def _hash(text: str, salt: str) -> str:
    """Legacy SHA-256 hash retained only for transparent migration."""
    return hashlib.sha256((salt + text).encode("utf-8")).hexdigest()


PBKDF2_ITERATIONS = 600_000
PBKDF2_PREFIX = "pbkdf2_sha256"


def _pbkdf2_hash(text: str, salt: str, iterations: int = PBKDF2_ITERATIONS) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256", text.encode("utf-8"), bytes.fromhex(salt), iterations,
    ).hex()
    return f"{PBKDF2_PREFIX}${iterations}${digest}"


def _verify_hash(text: str, salt: str, stored: str) -> tuple[bool, bool]:
    """Return (valid, needs_upgrade), supporting hashes from older versions."""
    if stored.startswith(f"{PBKDF2_PREFIX}$"):
        try:
            _, iterations, _ = stored.split("$", 2)
            candidate = _pbkdf2_hash(text, salt, int(iterations))
        except (ValueError, TypeError):
            return False, False
        return hmac.compare_digest(candidate, stored), int(iterations) < PBKDF2_ITERATIONS
    return hmac.compare_digest(_hash(text, salt), stored), True


class AuthService:

    def has_password(self) -> bool:
        return bool(settings.get("password_hash"))

    def set_password(self, password: str) -> None:
        if len(password) < PASSWORD_MIN_LENGTH:
            raise AuthError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
        security_answer_salt = settings.get("security_answer_salt")
        password_salt = settings.get("password_salt")
        if settings.get("security_answer_hash") and not security_answer_salt and password_salt:
            settings.set("security_answer_salt", password_salt)
        salt = secrets.token_hex(16)
        pwd_hash = _pbkdf2_hash(password, salt)
        settings.set_many({"password_salt": salt, "password_hash": pwd_hash})

    def verify_password(self, password: str) -> bool:
        stored_hash = settings.get("password_hash")
        salt = settings.get("password_salt")
        if not stored_hash or not salt:
            return False
        valid, needs_upgrade = _verify_hash(password, salt, stored_hash)
        if valid and needs_upgrade:
            self.set_password(password)
        return valid

    def change_password(self, old: str, new: str, confirm: str) -> None:
        if not self.verify_password(old):
            raise AuthError("Current password is incorrect.")
        if new != confirm:
            raise AuthError("New passwords do not match.")
        self.set_password(new)

    def has_security_question(self) -> bool:
        return bool(settings.get("security_question")) and bool(settings.get("security_answer_hash"))

    def set_security_question(self, question: str, answer: str, confirm: str) -> None:
        if not question.strip():
            raise AuthError("Question cannot be empty.")
        if not answer.strip():
            raise AuthError("Answer cannot be empty.")
        if answer != confirm:
            raise AuthError("Answers do not match.")
        salt = settings.get("security_answer_salt") or secrets.token_hex(16)
        settings.set_many({
            "security_answer_salt": salt,
            "security_question": question.strip(),
            "security_answer_hash": _pbkdf2_hash(answer.strip().lower(), salt),
        })

    def verify_security_answer(self, answer: str) -> bool:
        stored = settings.get("security_answer_hash")
        salt = settings.get("security_answer_salt") or settings.get("password_salt")
        if not stored or not salt:
            return False
        normalized = answer.strip().lower()
        valid, needs_upgrade = _verify_hash(normalized, salt, stored)
        if valid and needs_upgrade:
            new_salt = secrets.token_hex(16)
            settings.set_many({
                "security_answer_salt": new_salt,
                "security_answer_hash": _pbkdf2_hash(normalized, new_salt),
            })
        return valid

    def reset_password_via_security(self, answer: str, new_password: str, confirm: str) -> None:
        if not self.verify_security_answer(answer):
            raise AuthError("Security answer is incorrect.")
        if new_password != confirm:
            raise AuthError("Passwords do not match.")
        self.set_password(new_password)

    def lockout_remaining(self, now: float | None = None) -> int:
        now = time.time() if now is None else now
        try:
            lock_until = float(settings.get("login_lock_until", 0) or 0)
        except (TypeError, ValueError):
            lock_until = 0
        return max(0, int(lock_until - now + 0.999))

    def register_failed_login(self, now: float | None = None) -> tuple[int, int]:
        now = time.time() if now is None else now
        if self.lockout_remaining(now):
            return 0, self.lockout_remaining(now)
        attempts = settings.get_int("login_failed_attempts", 0) + 1
        if attempts >= MAX_LOGIN_ATTEMPTS:
            lock_until = now + LOGIN_LOCKOUT_SECONDS
            settings.set_many({
                "login_failed_attempts": 0,
                "login_lock_until": lock_until,
            })
            return 0, LOGIN_LOCKOUT_SECONDS
        settings.set("login_failed_attempts", attempts)
        return MAX_LOGIN_ATTEMPTS - attempts, 0

    def clear_login_failures(self) -> None:
        settings.set_many({"login_failed_attempts": 0, "login_lock_until": 0})


auth = AuthService()
