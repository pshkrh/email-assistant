// Log utility
class Logger {
  constructor() {
    this.logs = [];
  }

  log(message) {
    const timestamp = new Date().toLocaleTimeString();
    this.logs.push(`[${timestamp}] ${message}`);
    this.updateLogsUI();
  }

  updateLogsUI() {
    document.getElementById("logs").textContent = this.logs.join("\n");
  }
}

const logger = new Logger();

document.getElementById("fetchButton").addEventListener("click", () => {
  const status = document.getElementById("status");
  const result = document.getElementById("result");
  const fetchButton = document.getElementById("fetchButton");

  fetchButton.disabled = true;
  status.textContent = "Fetching thread...";
  result.textContent = "";
  logger.log("Button clicked: Starting thread fetch");

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs || tabs.length === 0) {
      status.textContent = "Error: No active tab found";
      logger.log("Error: No active tab available");
      fetchButton.disabled = false;
      return;
    }

    chrome.tabs.sendMessage(
      tabs[0].id,
      { action: "getThreadInfo" },
      (response) => {
        if (chrome.runtime.lastError) {
          status.textContent = "Error: Could not access Gmail page";
          logger.log(
            `Content script error: ${chrome.runtime.lastError.message}`
          );
          fetchButton.disabled = false;
          return;
        }

        if (!response) {
          status.textContent = "Error: No response from Gmail page";
          logger.log("Error: No response received from content script");
          fetchButton.disabled = false;
          return;
        }

        const { threadId, email } = response;
        if (!threadId || !email) {
          status.textContent = "Error: Missing thread ID or email";
          logger.log(`Missing data - Thread ID: ${threadId}, Email: ${email}`);
          fetchButton.disabled = false;
          return;
        }

        logger.log(`Thread ID: ${threadId}, Email: ${email}`);

        fetch("http://localhost:8000/fetch_gmail_thread", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ threadId, email }),
        })
          .then((response) => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
          })
          .then((data) => {
            if (data.error) {
              status.textContent = `Error: ${data.error}`;
              logger.log(`Backend error: ${data.error}`);
            } else {
              status.textContent = "Thread fetched successfully!";
              result.textContent = formatThreadData(data);
              logger.log("Thread data fetched successfully");
            }
          })
          .catch((error) => {
            status.textContent = "Error: Failed to fetch thread";
            logger.log(`Fetch error: ${error.message}`);
          })
          .finally(() => {
            fetchButton.disabled = false;
          });
      }
    );
  });
});

function formatThreadData(data) {
  let output = `Thread ID: ${data.threadId}\n\n`;
  data.messages.forEach((msg, index) => {
    output += `Message ${index + 1}:\n`;
    output += `  From: ${msg.From}\n`;
    output += `  To: ${msg.To}\n`;
    output += `  Subject: ${msg.Subject}\n`;
    output += `  Date: ${msg.Date}\n`;
    output += `  Body: ${msg.Body.slice(0, 100)}...\n\n`;
  });
  return output;
}
