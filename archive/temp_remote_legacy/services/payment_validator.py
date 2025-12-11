import re
import logging

logger = logging.getLogger(__name__)

class InvalidReceiptError(Exception):
    pass

class PaymentValidator:
    def __init__(self):
        # Compiled regex patterns for performance
        
        # KBZ Pay Patterns
        self.kbz_keywords = ["KBZ Pay", "KBZPay", "Kpay"]
        self.kbz_tid_pattern = re.compile(r'(?:Transaction ID|Trans ID|TID)[\s:.]*(\d{10,})', re.IGNORECASE)
        
        # Wave Pay Patterns
        self.wave_keywords = ["Wave Money", "WavePay", "Wave Pay"]
        self.wave_tid_pattern = re.compile(r'(?:Transaction ID|Trans ID|TID)[\s:.]*(\d{10,})', re.IGNORECASE)
        
        # Common Amount Pattern (e.g., 3,000 MMK, 3000 Ks)
        # Matches: 3,000, 3000, 3000.00 followed by MMK, Ks, or Kyats
        self.amount_pattern = re.compile(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)[\s]*(?:MMK|Ks|Kyats)', re.IGNORECASE)

    def validate_receipt(self, text_lines):
        """
        Validates the receipt text and extracts data.
        :param text_lines: List of strings from OCR
        :return: dict with 'provider', 'transaction_id', 'amount'
        :raises: InvalidReceiptError
        """
        full_text = " ".join(text_lines)
        
        # 1. Identify Provider
        provider = self._identify_provider(full_text)
        if not provider:
            raise InvalidReceiptError("Could not identify payment provider (KBZ/Wave).")

        # 2. Extract Transaction ID
        transaction_id = self._extract_tid(full_text, provider)
        if not transaction_id:
            raise InvalidReceiptError("Could not find Transaction ID.")

        # 3. Extract Amount
        amount = self._extract_amount(full_text)
        if not amount:
            # Fallback: Try to find standalone numbers that look like 3000
            # This is risky but helpful if OCR misses "MMK"
            if "3000" in full_text.replace(",", ""):
                amount = 3000.0
            else:
                raise InvalidReceiptError("Could not find valid amount.")

        return {
            "provider": provider,
            "transaction_id": transaction_id,
            "amount": amount
        }

    def _identify_provider(self, text):
        for kw in self.kbz_keywords:
            if kw.lower() in text.lower():
                return "KBZ Pay"
        for kw in self.wave_keywords:
            if kw.lower() in text.lower():
                return "Wave Pay"
        return None

    def _extract_tid(self, text, provider):
        # 1. Try standard patterns with labels
        if provider == "KBZ Pay":
            match = self.kbz_tid_pattern.search(text)
            if match: return match.group(1)
        elif provider == "Wave Pay":
            match = self.wave_tid_pattern.search(text)
            if match: return match.group(1)
            
        # 2. Fallback: Look for any standalone sequence of 15-25 digits
        # This handles cases where OCR misses the "Transaction ID" label
        # KBZ TIDs are usually ~20 digits, Wave ~15-20
        fallback_pattern = re.compile(r'\b(\d{15,25})\b')
        match = fallback_pattern.search(text)
        if match:
            return match.group(1)
            
        return None

    def _extract_amount(self, text):
        # 1. Try Fallback Pattern FIRST (More robust for OCR noise)
        # Look for a group of characters that *could* be a number (digits, dots, commas, spaces, =)
        # immediately followed by Ks or MMK
        fallback_pattern = re.compile(r'([=\d\s.,]+)[\s]*(?:Ks|MMK)', re.IGNORECASE)
        matches = fallback_pattern.findall(text)
        
        for m in matches:
            # Clean up: remove commas, spaces, equals signs
            clean_str = m.replace(",", "").replace(" ", "").replace("=", "")
            try:
                val = float(clean_str)
                if val > 0: return val # Return first positive amount found
            except ValueError:
                continue
                
        # 2. Try standard pattern (e.g., 3,000 MMK, 3000 Ks)
        match = self.amount_pattern.search(text)
        if match:
            amount_str = match.group(1).replace(",", "")
            try: return float(amount_str)
            except ValueError: pass
            
        return None

# Singleton
payment_validator = PaymentValidator()
