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
    const logsElement = document.getElementById("logs");
    if (logsElement) {
      logsElement.textContent = this.logs.join("\n");
    }
  }
}

const logger = new Logger();

// Error handling function
function showError(errorMessage, errorType) {
  const container = document.querySelector(".container");
  const errorHtml = `
    <header>
      <h1>MailMate</h1>
      <p>Smart Email Insights</p>
    </header>
    <div class="error-banner">
      <p class="error-title">${errorType || "Error"}</p>
      <p class="error-message">${errorMessage}</p>
    </div>
    <div class="task-container">
      <div class="task-card disabled">
        <input type="checkbox" id="summary" disabled />
        <label for="summary">Generate Summary</label>
      </div>
      <div class="task-card disabled">
        <input type="checkbox" id="actionItems" disabled />
        <label for="actionItems">List Action Items</label>
      </div>
      <div class="task-card disabled">
        <input type="checkbox" id="draftReply" disabled />
        <label for="draftReply">Draft a Reply</label>
      </div>
    </div>
    <button id="retryButton" data-error-type="${errorType || ""}">Retry</button>
    <details>
      <summary>View Logs <span class="arrow">›</span></summary>
      <pre id="logs" class="logs"></pre>
    </details>
  `;

  // Save the original content if it's the first error
  if (!container.dataset.originalContent) {
    container.dataset.originalContent = container.innerHTML;
  }

  // Show error UI
  container.innerHTML = errorHtml;
  logger.log(`Error displayed: ${errorType || "Error"} - ${errorMessage}`);

  // Update logs display
  logger.updateLogsUI();

  // Add retry button listener
  document.getElementById("retryButton").addEventListener("click", () => {
    const errorType = document
      .getElementById("retryButton")
      .getAttribute("data-error-type");

    // For authentication errors, clear tokens before retrying
    if (errorType === "Authentication Error") {
      logger.log("Authentication error detected, clearing tokens before retry");
      // Send message to background script to clear all tokens
      chrome.runtime.sendMessage({ action: "clearAuthTokens" }, () => {
        resetUI();
      });
    } else {
      resetUI();
    }
  });
}

// Reset UI to original state
function resetUI() {
  const container = document.querySelector(".container");
  if (container.dataset.originalContent) {
    logger.log("UI reset to original state");

    // Restore the original content
    container.innerHTML = container.dataset.originalContent;

    // Re-attach all event listeners
    attachEventListeners();

    // IMPORTANT: Reset all UI elements to their initial state
    const status = document.getElementById("status");
    const result = document.getElementById("result");
    const feedback = document.getElementById("feedback");
    const analyzeButton = document.getElementById("analyzeButton");

    // Reset button state
    analyzeButton.disabled = false;

    // Reset status display
    status.style.display = "none";
    status.textContent = "";

    // Reset result area
    result.style.display = "none";
    result.textContent = "";

    // Reset feedback area
    feedback.style.display = "none";
    feedback.innerHTML = "";

    // Update logs display
    logger.updateLogsUI();
  }
}

// Function to attach all event listeners to the UI
function attachEventListeners() {
  document
    .getElementById("analyzeButton")
    .addEventListener("click", performAnalysis);
}

function performAnalysis() {
  const status = document.getElementById("status");
  const result = document.getElementById("result");
  const feedback = document.getElementById("feedback");
  const analyzeButton = document.getElementById("analyzeButton");

  const tasks = [];
  if (document.getElementById("summary").checked) tasks.push("summary");
  if (document.getElementById("actionItems").checked)
    tasks.push("action_items");
  if (document.getElementById("draftReply").checked) tasks.push("draft_reply");

  if (tasks.length === 0) {
    showError("Please select at least one task.", "Input Error");
    logger.log("No tasks selected");
    return;
  }

  analyzeButton.disabled = true;
  status.style.display = "block";
  status.textContent = "Analyzing email...";
  result.style.display = "none";
  result.textContent = "";
  feedback.style.display = "none";
  feedback.innerHTML = "";
  logger.log(`Starting analysis with tasks: ${tasks.join(", ")}`);

  try {
    chrome.runtime.sendMessage({ action: "fetchThread", tasks }, (response) => {
      // Handle no response from background script
      if (!response) {
        showError(
          "Extension encountered an error. Please try again.",
          "Extension Error"
        );
        logger.log("No response from background script");
        return;
      }

      if (chrome.runtime.lastError) {
        showError(
          `Could not analyze email: ${chrome.runtime.lastError.message}`,
          "Extension Error"
        );
        logger.log(`Error: ${chrome.runtime.lastError.message}`);
        return;
      }

      if (response && response.error) {
        showError(response.error, response.errorType || "Unknown Error");
        logger.log(
          `Error: ${response.error} (Type: ${response.errorType || "Unknown"})`
        );
        return;
      }

      chrome.storage.local.get("threadData", (data) => {
        if (data.threadData) {
          status.textContent = "Analysis complete!";
          result.style.display = "block";
          result.textContent = formatThreadData(data.threadData);
          displayFeedbackOptions(data.threadData, tasks);
          logger.log("Analysis results displayed");
        } else {
          showError("No analysis data available.", "Data Error");
          logger.log("No analysis data found");
        }
        analyzeButton.disabled = false;
      });
    });
  } catch (err) {
    showError(`Unexpected error: ${err.message}`, "System Error");
    logger.log(`Exception: ${err.message}`);
    analyzeButton.disabled = false;
  }
}

function formatThreadData(data) {
  let output = `Thread ID: ${data.threadId || "N/A"}\n`;
  output += `User Email: ${data.userEmail || "N/A"}\n`;
  if (data.summary) output += `\nSummary:\n${data.summary}\n`;
  if (data.action_items) output += `\nAction Items:\n${data.action_items}\n`;
  if (data.draft_reply) output += `\nDraft Reply:\n${data.draft_reply}\n`;
  return output.trim();
}

function displayFeedbackOptions(data, tasks) {
  const feedbackContainer = document.getElementById("feedback");
  feedbackContainer.style.display = "block";
  feedbackContainer.innerHTML = ""; // Clear previous feedback

  tasks.forEach((task) => {
    const taskName = task
      .replace("_", " ")
      .replace(/\b\w/g, (c) => c.toUpperCase()); // e.g., "action_items" -> "Action Items"
    const feedbackDiv = document.createElement("div");
    feedbackDiv.className = "feedback-item";
    feedbackDiv.innerHTML = `
      <p>Rate "${taskName}":</p>
      <button class="feedback-btn thumbs-up" data-task="${task}">
        <i class="fas fa-thumbs-up"></i>
      </button>
      <button class="feedback-btn thumbs-down" data-task="${task}">
        <i class="fas fa-thumbs-down"></i>
      </button>
    `;
    feedbackContainer.appendChild(feedbackDiv);
  });

  // Add event listeners for feedback buttons
  document.querySelectorAll(".feedback-item").forEach((item) => {
    const thumbsUp = item.querySelector(".thumbs-up");
    const thumbsDown = item.querySelector(".thumbs-down");
    const task = thumbsUp.getAttribute("data-task");

    thumbsUp.addEventListener("click", () => {
      logger.log(`Submitting feedback for task: ${task}, rating: thumbs_up`);
      sendFeedback(data, task, "thumbs_up");
      thumbsUp.disabled = true;
      thumbsDown.disabled = true;
      thumbsUp.classList.add("selected");
    });

    thumbsDown.addEventListener("click", () => {
      logger.log(`Submitting feedback for task: ${task}, rating: thumbs_down`);
      sendFeedback(data, task, "thumbs_down");
      thumbsUp.disabled = true;
      thumbsDown.disabled = true;
      thumbsDown.classList.add("selected");
    });
  });
}

function sendFeedback(data, task, rating) {
  const feedbackData = {
    userEmail: data.userEmail || "unknown",
    threadId: data.threadId || "unknown",
    task: task,
    rating: rating,
    docId: data.docId,
    timestamp: new Date().toISOString(),
  };

  logger.log(`Sending feedback payload: ${JSON.stringify(feedbackData)}`);

  fetch("http://127.0.0.1:8000/store_feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(feedbackData),
  })
    .then((res) => {
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      return res.json();
    })
    .then((response) => {
      logger.log(`Feedback stored successfully: ${JSON.stringify(response)}`);
    })
    .catch((err) => {
      logger.log(`Error storing feedback: ${err.message}`);
      showError(`Failed to submit feedback: ${err.message}`, "API Error");
    });
}

// Initialize the UI
document.addEventListener("DOMContentLoaded", function () {
  attachEventListeners();

  // Clear any existing status messages on fresh load
  const status = document.getElementById("status");
  if (status) {
    status.style.display = "none";
    status.textContent = "";
  }
});
