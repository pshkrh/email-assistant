const CLIENT_ID =
  "673808915782-hgbcr3o8tjjct8pvgej9uq4599pc4k0g.apps.googleusercontent.com";
const REDIRECT_URI = "https://dibopfifimkeojnankjcdmlkcemlifoi.chromiumapp.org";
const SCOPES =
  "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/userinfo.email";

// Error types for better classification
const ERROR_TYPES = {
  CONNECTION: "Connection Error",
  AUTHENTICATION: "Authentication Error",
  API: "API Error",
  SERVER: "Server Error",
  GMAIL: "Gmail Error",
  ACCOUNT_MISMATCH: "Account Mismatch Error",
  UNKNOWN: "Unknown Error",
};

// Get token and verify it belongs to the expected user
function getAuthToken(expectedEmail, callback, forceRefresh = false) {
  chrome.storage.local.get("userTokens", (result) => {
    const userTokens = result.userTokens || {};
    const now = Date.now();
    const userTokenData = userTokens[expectedEmail];

    // Use cached token only if it's valid, not expired, and not forcing refresh
    if (
      !forceRefresh &&
      userTokenData &&
      userTokenData.authToken &&
      userTokenData.tokenExpiry &&
      now < userTokenData.tokenExpiry
    ) {
      console.log(
        `Using cached token for ${expectedEmail}:`,
        userTokenData.authToken.substring(0, 5) + "..."
      );

      // Verify the token belongs to the expected user before using it
      verifyTokenOwner(userTokenData.authToken, expectedEmail, (isValid) => {
        if (isValid) {
          callback(userTokenData.authToken);
        } else {
          console.error(
            `❌ Cached token doesn't match user ${expectedEmail}. Clearing and requesting new token.`
          );
          clearUserToken(expectedEmail, () => {
            // Recursively call getAuthToken with forceRefresh=true
            getAuthToken(expectedEmail, callback, true);
          });
        }
      });
      return;
    }

    console.log(
      `Getting new auth token for ${expectedEmail}${
        forceRefresh ? " (forced refresh)" : ""
      }`
    );

    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${CLIENT_ID}&redirect_uri=${encodeURIComponent(
      REDIRECT_URI
    )}&response_type=token&scope=${encodeURIComponent(
      SCOPES
    )}&prompt=consent&login_hint=${encodeURIComponent(expectedEmail)}`;
    console.log("Auth URL for", expectedEmail, ":", authUrl);

    chrome.identity.launchWebAuthFlow(
      {
        url: authUrl,
        interactive: true,
      },
      (redirectUrl) => {
        if (chrome.runtime.lastError || !redirectUrl) {
          const errorMessage = chrome.runtime.lastError
            ? chrome.runtime.lastError.message
            : "No redirect URL returned";
          console.error("Auth error for", expectedEmail, ":", errorMessage);
          callback(null, {
            type: ERROR_TYPES.AUTHENTICATION,
            message: `Authentication failed: ${errorMessage}`,
          });
          return;
        }
        console.log("Redirect URL received:", redirectUrl);
        const hash = new URL(redirectUrl).hash;
        if (!hash) {
          console.error("No hash in redirect URL for", expectedEmail);
          callback(null, {
            type: ERROR_TYPES.AUTHENTICATION,
            message: "Authentication failed: No token received",
          });
          return;
        }
        const params = hash.slice(1).split("&");
        const tokenParam = params.find((param) =>
          param.startsWith("access_token=")
        );
        if (!tokenParam) {
          console.error("No access_token in redirect URL:", hash);
          callback(null, {
            type: ERROR_TYPES.AUTHENTICATION,
            message: "Authentication failed: No access token found",
          });
          return;
        }
        const token = tokenParam.split("=")[1];
        const expiresIn = parseInt(
          params.find((p) => p.startsWith("expires_in="))?.split("=")[1] ||
            "3600",
          10
        );

        // Verify the token belongs to the expected user
        verifyTokenOwner(token, expectedEmail, (isValid, actualEmail) => {
          if (isValid) {
            const expiryTime = Date.now() + expiresIn * 1000;
            userTokens[expectedEmail] = {
              authToken: token,
              tokenExpiry: expiryTime,
            };
            chrome.storage.local.set({ userTokens }, () => {
              console.log(
                `Token saved for ${expectedEmail}:`,
                token.substring(0, 5) + "...",
                "Expires at:",
                new Date(expiryTime)
              );
              callback(token);
            });
          } else {
            console.error(
              `❌ Token received is for ${actualEmail}, not ${expectedEmail}`
            );
            callback(null, {
              type: ERROR_TYPES.ACCOUNT_MISMATCH,
              message: `You selected a different account (${actualEmail}) than the one currently open in Gmail (${expectedEmail}). Please select the correct account when prompted.`,
            });
          }
        });
      }
    );
  });
}

// Verify token belongs to the expected user by checking userinfo
function verifyTokenOwner(token, expectedEmail, callback) {
  fetch("https://www.googleapis.com/oauth2/v2/userinfo", {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((response) => {
      if (!response.ok) {
        console.error(`Token verification failed: ${response.status}`);
        callback(false);
        return null;
      }
      return response.json();
    })
    .then((data) => {
      if (!data) return;

      const tokenEmail = data.email;
      console.log(
        `Token verification: expected=${expectedEmail}, actual=${tokenEmail}`
      );

      if (
        tokenEmail &&
        tokenEmail.toLowerCase() === expectedEmail.toLowerCase()
      ) {
        callback(true);
      } else {
        callback(false, tokenEmail);
      }
    })
    .catch((error) => {
      console.error("Error verifying token owner:", error);
      callback(false);
    });
}

// Function to clear token for a specific user
function clearUserToken(userEmail, callback) {
  chrome.storage.local.get("userTokens", (result) => {
    const userTokens = result.userTokens || {};
    if (userTokens[userEmail]) {
      console.log(`Clearing token for ${userEmail}`);
      delete userTokens[userEmail];
      chrome.storage.local.set({ userTokens }, () => {
        if (callback) callback();
      });
    } else {
      if (callback) callback();
    }
  });
}

// Function to clear all tokens
function clearAllTokens(callback) {
  console.log("Clearing all authentication tokens");
  chrome.storage.local.set({ userTokens: {} }, () => {
    if (callback) callback();
  });
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log("Message received:", request);

  // Handle token clearing requests
  if (request.action === "clearUserToken" && request.email) {
    clearUserToken(request.email, () => {
      sendResponse({ success: true });
    });
    return true;
  }

  if (request.action === "clearAuthTokens") {
    clearAllTokens(() => {
      sendResponse({ success: true });
    });
    return true;
  }

  if (request.action === "fetchThread") {
    chrome.tabs.query({ url: "https://mail.google.com/*" }, (tabs) => {
      if (!tabs || tabs.length === 0) {
        console.error("No Gmail tabs found");
        sendResponse({
          error: "Please open Gmail in a tab before analyzing emails",
          errorType: ERROR_TYPES.GMAIL,
        });
        return;
      }
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
            sendResponse({
              error: `Can't access Gmail: ${chrome.runtime.lastError.message}`,
              errorType: ERROR_TYPES.GMAIL,
            });
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
                sendResponse({
                  error:
                    "Failed to communicate with Gmail tab. Please refresh the page.",
                  errorType: ERROR_TYPES.GMAIL,
                });
                return;
              }
              if (response && response.threadId && response.email) {
                console.log(
                  "✅ Thread ID:",
                  response.threadId,
                  "Email:",
                  response.email
                );

                // Use forceRefresh if requested
                const forceRefresh = request.forceRefresh === true;
                getAuthToken(
                  response.email,
                  (token, error) => {
                    if (token) {
                      fetchThreadData(
                        token,
                        response.threadId,
                        response.email,
                        request.tasks, // Pass tasks from popup
                        sendResponse
                      );
                    } else {
                      console.error(
                        "❌ Failed to get auth token for",
                        response.email,
                        error
                      );
                      sendResponse({
                        error: error
                          ? error.message
                          : "Failed to get auth token",
                        errorType: error
                          ? error.type
                          : ERROR_TYPES.AUTHENTICATION,
                      });
                    }
                  },
                  forceRefresh
                );
              } else {
                console.warn("❌ No thread ID or email found");
                sendResponse({
                  error: "No email selected. Please open an email first.",
                  errorType: ERROR_TYPES.GMAIL,
                });
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

function fetchThreadData(token, threadId, email, tasks, sendResponse) {
  fetch(`https://gmail.googleapis.com/gmail/v1/users/me/threads/${threadId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
    .then((res) => {
      if (!res.ok) {
        if (res.status === 401) {
          console.log(
            "Token invalid (401 Unauthorized). Clearing token and retrying"
          );

          // Clear the invalid token
          clearUserToken(email, () => {
            // Get a fresh token
            getAuthToken(
              email,
              (newToken, error) => {
                if (newToken) {
                  console.log("Got new token after 401, retrying fetch");
                  fetchThreadData(
                    newToken,
                    threadId,
                    email,
                    tasks,
                    sendResponse
                  );
                } else {
                  console.error("Failed to get new token after 401", error);
                  sendResponse({
                    error: error
                      ? error.message
                      : "Your session has expired. Please sign in again.",
                    errorType: ERROR_TYPES.AUTHENTICATION,
                  });
                }
              },
              true
            ); // Force refresh
          });
          return;
        }
        if (res.status === 404) {
          throw new Error(`Thread not found (ID: ${threadId})`);
        }
        throw new Error(`HTTP error: ${res.status}`);
      }
      return res.json();
    })
    .then((threadData) => {
      if (!threadData) return; // Skip if we're re-authenticating

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
        userEmail: email || null,
        messageId: message.id || null,
        date: headers["Date"] || null,
        from: headers["From"] || null,
        to: headers["To"] || null,
        subject: headers["Subject"] || null,
        body: body || null,
        messagesCount: threadData.messages.length || null,
        threadId: threadId || null,
        tasks: tasks || [], // Include selected tasks
      };

      console.log("Data with tasks:", data);

      fetch(
        "https://email-assistant-673808915782.us-central1.run.app/fetch_gmail_thread",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        }
      )
        .then((res) => {
          if (!res.ok) {
            throw new Error(`Server error: ${res.status}`);
          }
          return res.json();
        })
        .then((data) => {
          console.log("✅ Server Response:", data);
          chrome.storage.local.set({ threadData: data }, () => {
            sendResponse({ success: "Thread data fetched and stored" });
          });
        })
        .catch((err) => {
          console.error("🚨 Fetch error:", err);
          sendResponse({
            error: `Server unavailable: ${err.message}. Check your server connection.`,
            errorType: ERROR_TYPES.SERVER,
          });
        });
    })
    .catch((err) => {
      console.error("🚨 Gmail API error:", err);
      sendResponse({
        error: `Email data couldn't be retrieved: ${err.message}`,
        errorType: ERROR_TYPES.API,
      });
    });
}
