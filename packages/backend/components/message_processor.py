import asyncio
from packages.shared.transcript_logger import TranscriptLogger


class MessageProcessor:
    """
    Processes in-character player messages for a campaign.
    Appends each message to the campaign transcript log using TranscriptLogger.
    """

    def __init__(self):
        self.transcript_logger = TranscriptLogger()

    async def process_player_message(self, campaign_id: str, author: str, message: str):
        """
        Process an in-character player message as an in-game action.
        Appends the message to the campaign transcript log.
        """
        try:
            await self.transcript_logger.log_message(campaign_id, author, message)
        except Exception as e:
            # Robust error handling: log and continue
            print(f"[MessageProcessor] Error logging message: {e}")

    async def log_ai_response(self, campaign_id: str, message: str):
        """
        Log an AI-generated narrative response to the campaign transcript.

        This method is the canonical integration point for all future AI response
        generation logic. When the AI generates a narrative, call this method
        to append the response to the campaign's transcript log.

        Example usage (in future AI response generator):
            await self.log_ai_response(campaign_id, ai_narrative)

        Args:
            campaign_id (str): The campaign's unique identifier.
            message (str): The AI-generated narrative content.

        The log entry will have author="AI" and include a timestamp.
        """
        try:
            await self.transcript_logger.log_message(campaign_id, "AI", message)
        except Exception as e:
            # Robust error handling: log and continue
            print(f"[MessageProcessor] Error logging AI response: {e}")
