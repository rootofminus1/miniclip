import os

ALLOWED_USERS = os.environ["ALLOWED_USERS"].split(",")

def lambda_handler(event, context):
    user_id = (event.get("headers") or {}).get("x-user-id", "").strip()
    return {"isAuthorized": user_id in ALLOWED_USERS}