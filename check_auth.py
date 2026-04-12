import passlib
import bcrypt
import sys

print(f"Passlib version: {passlib.__version__}")
print(f"Bcrypt version: {bcrypt.__version__}")

try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash("test")
    verified = pwd_context.verify("test", hashed)
    if verified:
        print("✅ Auth system (bcrypt) is working correctly!")
    else:
        print("❌ Auth system failed verification.")
except Exception as e:
    print(f"❌ Auth system error: {e}")
    print("\n[FIX] Try running: pip install bcrypt==4.0.1")
