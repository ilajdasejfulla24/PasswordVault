"""
password_generator.py
---------------------
Utility class for generating cryptographically strong random passwords.
"""

import secrets
import string


class PasswordGenerator:
    """
    Generates random, cryptographically strong passwords using the
    `secrets` module (CSPRNG-backed).

    Attributes
    ----------
    LOWERCASE  : lowercase ASCII letters
    UPPERCASE  : uppercase ASCII letters
    DIGITS     : decimal digits
    SYMBOLS    : common special characters
    ALL        : full character pool (all of the above combined)
    """

    LOWERCASE = string.ascii_lowercase
    UPPERCASE = string.ascii_uppercase
    DIGITS = string.digits
    SYMBOLS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    ALL = LOWERCASE + UPPERCASE + DIGITS + SYMBOLS

    @classmethod
    def generate(
        cls,
        length: int = 16,
        use_uppercase: bool = True,
        use_digits: bool = True,
        use_symbols: bool = True,
    ) -> str:
        """
        Generate a random password that satisfies the requested character-class
        requirements.

        Parameters
        ----------
        length        : Total password length (minimum 4)
        use_uppercase : Include uppercase letters
        use_digits    : Include digit characters
        use_symbols   : Include special symbol characters

        Returns
        -------
        str : A random password of the requested length

        Raises
        ------
        ValueError : If *length* is less than the number of required character classes
        """
        if length < 4:
            raise ValueError("Password length must be at least 4.")

        # Build the character pool and mandatory character list
        pool = cls.LOWERCASE
        mandatory: list[str] = [secrets.choice(cls.LOWERCASE)]

        if use_uppercase:
            pool += cls.UPPERCASE
            mandatory.append(secrets.choice(cls.UPPERCASE))

        if use_digits:
            pool += cls.DIGITS
            mandatory.append(secrets.choice(cls.DIGITS))

        if use_symbols:
            pool += cls.SYMBOLS
            mandatory.append(secrets.choice(cls.SYMBOLS))

        if length < len(mandatory):
            raise ValueError(
                f"Password length ({length}) is shorter than the number of "
                f"required character classes ({len(mandatory)})."
            )

        # Fill remaining positions with random pool characters
        remaining = [secrets.choice(pool) for _ in range(length - len(mandatory))]
        password_chars = mandatory + remaining

        # Shuffle to avoid predictable positions for mandatory characters
        secrets.SystemRandom().shuffle(password_chars)

        return "".join(password_chars)

    @classmethod
    def strength(cls, password: str) -> str:
        """
        Estimate the strength of a given password.

        Parameters
        ----------
        password : Password string to evaluate

        Returns
        -------
        str : "Weak", "Fair", "Strong", or "Very Strong"
        """
        score = 0

        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if len(password) >= 16:
            score += 1
        if any(c in cls.UPPERCASE for c in password):
            score += 1
        if any(c in cls.DIGITS for c in password):
            score += 1
        if any(c in cls.SYMBOLS for c in password):
            score += 1

        if score <= 2:
            return "Weak"
        elif score <= 3:
            return "Fair"
        elif score <= 4:
            return "Strong"
        else:
            return "Very Strong"
