# Data Models



The following Pydantic models define the core data structures for the application.



```python
from pydantic import BaseModel, SecretStr
from typing import List, Optional, Literal

class ServerConfig(BaseModel):
    server\_id: str
    api\_key: SecretStr
    dm\_roll\_visibility: Literal\['public', 'hidden']
    player\_roll\_mode: Literal\['manual\_physical\_total', 'manual\_physical\_raw', 'manual\_digital', 'auto\_visible', 'auto\_hidden']
    character\_sheet\_mode: Literal\['digital\_sheet', 'physical\_sheet']

class Campaign(BaseModel):
    campaign\_id: str
    server\_id: str
    name: str
    active\_player\_ids: List\[str]

class PlayerCharacter(BaseModel):
    character\_id: str
    player\_discord\_id: str
    campaign\_id: str
    name: str
    character\_sheet\_url: Optional\[str] = None
    preferred\_output\_mode: Literal\['text', 'voice'] = 'text'
```
