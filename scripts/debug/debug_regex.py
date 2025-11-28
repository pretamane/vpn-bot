import re

text = "E-Receipt =1 .00 Ks 28/11/2025 10:48:41 01003984011751096081 Transfer Than Than Win (******4377) -1.00 Ks tztest tg bot Thank you for using KBZPay! The e-receipt only means you already paid for the merchant. You need to confirm the final transaction status with merchant."

print(f"Testing text: {text}")

# Fallback Pattern
fallback_pattern = re.compile(r'([=\d\s.,]+)[\s]*(?:Ks|MMK)', re.IGNORECASE)
matches = fallback_pattern.findall(text)

print(f"Matches: {matches}")

for m in matches:
    clean_str = m.replace(",", "").replace(" ", "").replace("=", "")
    print(f"Cleaning '{m}' -> '{clean_str}'")
    try:
        val = float(clean_str)
        print(f"Parsed float: {val}")
    except ValueError as e:
        print(f"Float parse failed: {e}")
