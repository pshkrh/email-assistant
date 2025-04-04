const CLIENT_ID =
  "673808915782-hgbcr3o8tjjct8pvgej9uq4599pc4k0g.apps.googleusercontent.com";
const REDIRECT_URI = "https://fdclgicibpkmpihelkmiggcljjnbgfni.chromiumapp.org";
const SCOPES =
  "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email";

function getAuthToken(callback) {
  const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${CLIENT_ID}&redirect_uri=${encodeURIComponent(
    REDIRECT_URI
  )}&response_type=token&scope=${encodeURIComponent(SCOPES)}&prompt=consent`;
  console.log("Auth URL:", authUrl);

  chrome.identity.launchWebAuthFlow(
    {
      url: authUrl,
      interactive: true,
    },
    (redirectUrl) => {
      if (chrome.runtime.lastError || !redirectUrl) {
        console.error(
          "Auth error:",
          chrome.runtime.lastError || "No redirect URL returned"
        );
        callback(null);
        return;
      }
      console.log("Redirect URL:", redirectUrl);
      const hash = new URL(redirectUrl).hash;
      if (!hash) {
        console.error("No hash in redirect URL");
        callback(null);
        return;
      }
      const params = hash.slice(1).split("&");
      const tokenParam = params.find((param) =>
        param.startsWith("access_token=")
      );
      if (!tokenParam) {
        console.error("No access_token in redirect URL:", hash);
        callback(null);
        return;
      }
      const token = tokenParam.split("=")[1];
      console.log("Token:", token);
      callback(token);
    }
  );
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("Message received:", request);
  if (request.action === "fetchThread") {
    chrome.tabs.query({ url: "https://mail.google.com/*" }, (tabs) => {
      if (!tabs || tabs.length === 0) {
        console.error("No Gmail tabs found");
        sendResponse({ error: "Please open a Gmail tab" });
        return;
      }
      // Prefer the active tab if available, otherwise use the first Gmail tab
      const activeTab = tabs.find((tab) => tab.active) || tabs[0];
      const tabId = activeTab.id;
      console.log("Selected tab ID:", tabId, "URL:", activeTab.url);

      chrome.scripting.executeScript(
        {
          target: { tabId: tabId },
          func: checkGmailOpen,
        },
        (results) => {
          if (chrome.runtime.lastError) {
            console.error("Script execution error:", chrome.runtime.lastError);
            sendResponse({ error: chrome.runtime.lastError.message });
            return;
          }
          chrome.tabs.sendMessage(
            tabId,
            { action: "getThreadInfo" },
            (response) => {
              if (chrome.runtime.lastError) {
                console.error(
                  "🚨 Send message error:",
                  chrome.runtime.lastError
                );
                sendResponse({ error: chrome.runtime.lastError.message });
                return;
              }
              if (response && response.threadId && response.email) {
                console.log(
                  "✅ Thread ID:",
                  response.threadId,
                  "Email:",
                  response.email
                );
                getAuthToken((token) => {
                  if (token) {
                    fetchThreadData(
                      token,
                      response.threadId,
                      response.email,
                      sendResponse
                    );
                  } else {
                    console.error("❌ Failed to get auth token");
                    sendResponse({ error: "Failed to get auth token" });
                  }
                });
              } else {
                console.warn("❌ No thread ID or email found");
                sendResponse({ error: "No thread ID or email found" });
              }
            }
          );
        }
      );
    });
    return true;
  }
});

function checkGmailOpen() {
  if (window.location.hostname.includes("mail.google.com")) {
    console.log("📧 Gmail is open!");
  } else {
    console.error("❌ Gmail is not open in this tab.");
  }
}

function fetchThreadData(token, threadId, email, sendResponse) {
  fetch(`https://gmail.googleapis.com/gmail/v1/users/me/threads/${threadId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((res) => res.json())
    .then((threadData) => {
      const message = threadData.messages[threadData.messages.length - 1];
      const headers = message.payload.headers.reduce(
        (acc, h) => ({ ...acc, [h.name]: h.value }),
        {}
      );
      let body = "";
      if (message.payload.parts) {
        const textPart = message.payload.parts.find(
          (p) => p.mimeType === "text/plain"
        );
        if (textPart)
          body = atob(textPart.body.data.replace(/-/g, "+").replace(/_/g, "/"));
      } else if (message.payload.body.data) {
        body = atob(
          message.payload.body.data.replace(/-/g, "+").replace(/_/g, "/")
        );
      }

      const data = {
        userEmail: email,
        messageId: message.id,
        date: headers["Date"],
        from: headers["From"],
        to: headers["To"],
        subject: headers["Subject"],
        body: body || "No readable body",
        messagesCount: threadData.messages.length,
        threadId: threadId,
      };

      console.log("Data: ", data);

      fetch("http://localhost:8000/fetch_gmail_thread", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      })
        .then((res) => res.json())
        .then((data) => {
          console.log("✅ Server Response:", data);
          chrome.storage.local.set({ threadData: data }, () => {
            sendResponse({ success: "Thread data fetched and stored" });
          });
        })
        .catch((err) => {
          console.error("🚨 Fetch error:", err);
          sendResponse({ error: "Fetch error" });
        });
    })
    .catch((err) => {
      console.error("🚨 Gmail API error:", err);
      sendResponse({ error: "Gmail API error" });
    });
}
