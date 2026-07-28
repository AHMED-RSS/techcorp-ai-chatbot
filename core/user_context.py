from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _normalise_roles(
    value: Any,
) -> tuple[str, ...]:
    if isinstance(value, str):
        candidates = value.split(",")

    elif isinstance(value, (list, tuple, set)):
        candidates = value

    else:
        candidates = ()

    roles = {
        _clean_text(role)
        for role in candidates
        if _clean_text(role)
    }

    return tuple(sorted(roles))


@dataclass(
    frozen=True,
    slots=True,
)
class UserContext:
    """Authenticated identity used by application services."""

    user_id: str
    email: str
    name: str
    avatar_url: str | None = None
    email_verified: bool = False
    roles: tuple[str, ...] = ()

    @classmethod
    def from_claims(
        cls,
        claims: Mapping[str, Any],
    ) -> UserContext:
        user_id = _clean_text(
            claims.get("sub")
        )

        if not user_id:
            raise ValueError(
                "The identity provider did not return "
                "a stable 'sub' user identifier."
            )

        email = _clean_text(
            claims.get("email")
            or claims.get(
                "preferred_username"
            )
        )

        name = _clean_text(
            claims.get("name")
            or claims.get("nickname")
            or email
            or "TechCorp AI user"
        )

        avatar_url = _clean_text(
            claims.get("picture")
            or claims.get("avatar_url")
        ) or None

        return cls(
            user_id=user_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            email_verified=bool(
                claims.get(
                    "email_verified",
                    False,
                )
            ),
            roles=_normalise_roles(
                claims.get("roles")
            ),
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "email_verified": (
                self.email_verified
            ),
            "roles": list(self.roles),
        }
