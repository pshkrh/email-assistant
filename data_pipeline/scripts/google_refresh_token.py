from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://mail.google.com/"]

flow = InstalledAppFlow.from_client_secrets_file("mail_mate_client.json", SCOPES)

creds = flow.run_local_server(port=0)

print("Refresh Token:", creds.refresh_token)