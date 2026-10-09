from typing import Annotated

from pydantic import UUID4

UserUID = Annotated[UUID4, ...]
UserName = Annotated[str, ...]
Email = Annotated[str, ...]
PasswordHash = Annotated[str, ...]
Password = Annotated[str, ...]
