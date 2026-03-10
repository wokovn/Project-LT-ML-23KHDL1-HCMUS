"""
Vietnamese text normalization module for TTS training.
"""

import re
import logging

from num2words import num2words


class VietnameseTextNormalizer:
    """Normalize Vietnamese text for TTS training.

    Handles: lowercasing, emoji removal, number/date/percentage expansion,
    and stripping of non-Vietnamese characters.
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.digit_map = {
            '0': 'không', '1': 'một', '2': 'hai', '3': 'ba', '4': 'bốn',
            '5': 'năm', '6': 'sáu', '7': 'bảy', '8': 'tám', '9': 'chín'
        }

    def normalize(self, text: str) -> str:
        """Normalize a Vietnamese text string for TTS.

        Args:
            text: Raw transcription text.

        Returns:
            Cleaned, lowercased text with numbers expanded to words.
        """
        if not text:
            return ""

        text = text.lower()
        text = self._remove_emojis(text)
        text = self._expand_numbers(text)
        text = self._expand_dates(text)
        text = self._expand_percentages(text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(
            r'[^a-záàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ\s.,!?]',
            '', text
        )
        return text

    @staticmethod
    def _remove_emojis(text: str) -> str:
        """Strip emoji and symbol characters."""
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"
            u"\U0001F300-\U0001F5FF"
            u"\U0001F680-\U0001F6FF"
            u"\U0001F1E0-\U0001F1FF"
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        return emoji_pattern.sub(r'', text)

    def _expand_numbers(self, text: str) -> str:
        """Expand numeric tokens to Vietnamese words."""
        def replace_number(match):
            num_str = match.group(0)
            try:
                num = int(num_str)
                return num2words(num, lang='vi')
            except Exception:
                return ' '.join(self.digit_map.get(d, d) for d in num_str)

        return re.sub(r'\b\d+\b', replace_number, text)

    def _expand_dates(self, text: str) -> str:
        """Expand date formats (DD/MM or DD/MM/YYYY) to Vietnamese words."""
        def replace_date(match):
            day = match.group(1)
            month = match.group(2)
            year = match.group(3) if match.group(3) else ""
            result = f"ngày {num2words(int(day), lang='vi')} tháng {num2words(int(month), lang='vi')}"
            if year:
                result += f" năm {num2words(int(year), lang='vi')}"
            return result

        return re.sub(r'\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b', replace_date, text)

    def _expand_percentages(self, text: str) -> str:
        """Expand percentage symbols to Vietnamese words."""
        def replace_percent(match):
            num = match.group(1)
            return f"{num2words(int(num), lang='vi')} phần trăm"

        return re.sub(r'(\d+)\s*%', replace_percent, text)
