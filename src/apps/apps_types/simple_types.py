from typing import Annotated

from pydantic import UUID4

UserUID = Annotated[UUID4, ...]
UserLogin = Annotated[str, ...]
Email = Annotated[str, ...]
PasswordHash = Annotated[str, ...]
Password = Annotated[str, ...]
