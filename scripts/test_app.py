import sys
try:
    import src.api.main
    print("SUCCESS: src.api.main loaded cleanly!")
except Exception as e:
    import traceback
    print("ERROR loading src.api.main:")
    traceback.print_exc()
