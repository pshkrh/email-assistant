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

document.getElementById("testAuth").addEventListener("click", () => {
  console.clear(); // Clear previous logs
  console.log("Testing OAuth only...");

  chrome.identity.getAuthToken({ interactive: true, scopes: ["https://www.googleapis.com/auth/gmail.readonly"] }, (token) => {
    if (chrome.runtime.lastError) {
      console.error("AUTH ERROR:", chrome.runtime.lastError.message);
    } else {
      console.log("TOKEN SUCCESS:", token.substring(0, 5) + "...");
    }
  });
});

document.getElementById("fetchButton").addEventListener("click", () => {
  // Fixed: addListener -> addEventListener
  const status = document.getElementById("status");
  const result = document.getElementById("result");
  const fetchButton = document.getElementById("fetchButton");

  fetchButton.disabled = true;
  status.textContent = "Fetching thread...";
  result.textContent = "";
  logger.log("Button clicked: Starting thread fetch");

  chrome.runtime.sendMessage({ action: "fetchThread" }, (response) => {
    if (chrome.runtime.lastError) {
      status.textContent = "Error: Could not fetch thread";
      logger.log(`Error: ${chrome.runtime.lastError.message}`);
      fetchButton.disabled = false;
      return;
    }

    chrome.storage.local.get("threadData", (data) => {
      if (data.threadData) {
        status.textContent = "Thread fetched successfully!";
        result.textContent = formatThreadData(data.threadData);
        logger.log("Thread data displayed");
      } else {
        status.textContent = "Error: No thread data available";
        logger.log("No thread data found");
      }
      fetchButton.disabled = false;
    });
  });
});

function formatThreadData(data) {
  let output = `Thread ID: ${data.threadId}\n\n`;
  output += `Messages: ${data.messages || "N/A"}\n`;
  output += `Summary: ${data.summary || "N/A"}\n`;
  output += `Action Items: ${data.action_items || "N/A"}\n`;
  output += `Draft Reply: ${data.draft_reply || "N/A"}\n`;
  return output;
}
