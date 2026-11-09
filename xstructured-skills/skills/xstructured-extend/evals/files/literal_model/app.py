"""An in-house model that answers with Python dictionaries instead of JSON.

Every reply below is what the model returned in production last week. The
xstructured wrapper rejects all three with RecoveryError.
"""

from pydantic import BaseModel

from xstructured import XStructuredRunnable, with_xstructured_output
from xstructured.testing import ScriptedChatModel

REPLIES = [
    "Approved. <xstructured>{'approved': True, 'limit': 5000}</xstructured>",
    "Declined. <xstructured>{'approved': False, 'limit': 0}</xstructured>",
    "Approved with a cap.\n<xstructured>{'approved': True, 'limit': 1200,}</xstructured>",
]


class Decision(BaseModel):
    approved: bool
    limit: int


def make_wrapper(model: ScriptedChatModel) -> XStructuredRunnable:
    return with_xstructured_output(model, Decision)


model = ScriptedChatModel.of(*REPLIES)
