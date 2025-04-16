from google_auth_oauthlib.flow import InstalledAppFlow

client_secrets = {
    "installed": {
        "client_id": "673808915782-v3jahrr9jdl63t0l0t6e97vvda1a32kl.apps.googleusercontent.com",
        "project_id": "email-assistant-449706",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "<your_client_secret>",
        "redirect_uris": ["http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_secrets_file(
    "./data_pipeline/scripts/client_secrets.json",  # Save client_secrets to a file temporarily
    scopes=["https://www.googleapis.com/auth/gmail.send"],
)
creds = flow.run_local_server(port=0)
print("Refresh Token:", creds.refresh_token)
