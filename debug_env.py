"""
Debug script to check if environment variables are loading correctly.
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Check what values are loaded
print("=" * 80)
print("ENVIRONMENT VARIABLE DEBUG")
print("=" * 80)

kite_api_key = os.getenv("KITE_API_KEY", "")
kite_api_secret = os.getenv("KITE_API_SECRET", "")
kite_access_token = os.getenv("KITE_ACCESS_TOKEN", "")

print(f"\nKITE_API_KEY:")
print(f"  Value: '{kite_api_key}'")
print(f"  Length: {len(kite_api_key)}")
print(f"  Is empty: {not kite_api_key}")

print(f"\nKITE_API_SECRET:")
print(f"  Value: '{kite_api_secret}'")
print(f"  Length: {len(kite_api_secret)}")
print(f"  Is empty: {not kite_api_secret}")

print(f"\nKITE_ACCESS_TOKEN:")
print(f"  Value: '{kite_access_token}'")
print(f"  Length: {len(kite_access_token)}")
print(f"  Is empty: {not kite_access_token}")

print("\n" + "=" * 80)
print("TIPS:")
print("=" * 80)
print("1. Values should NOT have quotes in .env file")
print("   ✓ Correct:   KITE_API_KEY=abc123")
print("   ✗ Wrong:     KITE_API_KEY='abc123'")
print("   ✗ Wrong:     KITE_API_KEY=\"abc123\"")
print("\n2. Values should NOT have spaces")
print("   ✓ Correct:   KITE_API_KEY=abc123")
print("   ✗ Wrong:     KITE_API_KEY = abc123")
print("   ✗ Wrong:     KITE_API_KEY= abc123")
print("\n3. Make sure there are no trailing spaces")
print("=" * 80)
