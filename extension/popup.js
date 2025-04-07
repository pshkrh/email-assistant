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
  if (!container) return; // Safety check

  const errorHtml = `
    <header>
      <div class="logo-container">
        <img src="logo.png" alt="MailMate" class="logo" />
      </div>
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
      if (
        errorType === "Authentication Error" ||
        errorType === "Account Mismatch Error"
      ) {
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
  if (container && container.dataset.originalContent) {
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
  status.innerHTML = '<span class="loading-spinner"></span> Analyzing email...';
  result.style.display = "none";
  result.textContent = "";

  // Remove results container if it exists from a previous analysis
  const resultsContainer = document.getElementById("resultsContainer");
  if (resultsContainer) {
    resultsContainer.remove();
  }

  // Remove all task-result-blocks from previous analysis
  document.querySelectorAll(".task-result-block").forEach((el) => el.remove());

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
          displayResults(data.threadData, tasks);
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

// Display results in a modern card-based UI with interleaved feedback
function displayResults(data, tasks) {
  // Create a results container
  const resultsContainer = document.createElement("div");
  resultsContainer.id = "resultsContainer";
  resultsContainer.className = "results-container";
  resultsContainer.style.display = "block";

  // Create a card for each result type
  const taskLabels = {
    summary: "Summary",
    action_items: "Action Items",
    draft_reply: "Draft Reply",
  };

  // Append the results container to the main container
  const container = document.querySelector(".container");
  container.appendChild(resultsContainer);

  // Add each task result that was requested with its feedback
  tasks.forEach((task) => {
    if (data.result && data.result[task]) {
      // Create a block to hold both result and feedback
      const taskBlock = document.createElement("div");
      taskBlock.className = "task-result-block";

      // Create result card
      const resultCard = createResultCard(
        taskLabels[task] || task,
        data.result[task]
      );
      taskBlock.appendChild(resultCard);

      // Create feedback for this specific task
      const feedbackDiv = createFeedbackForTask(data, task);
      taskBlock.appendChild(feedbackDiv);

      // Add the block to the container
      container.appendChild(taskBlock);
    }
  });
}

// Create a card for each result type
function createResultCard(title, content) {
  const card = document.createElement("div");
  card.className = "result-card";

  // Format content based on result type
  let formattedContent = content;

  // For action items, format as list if needed
  if (
    title === "Action Items" &&
    !content.includes("<li>") &&
    !content.includes("* ")
  ) {
    // Check if content appears to be a list with line breaks
    if (content.includes("\n")) {
      const items = content
        .split("\n")
        .filter((item) => item.trim().length > 0);
      if (items.length > 1) {
        formattedContent = `<ul>${items
          .map((item) => `<li>${item.trim()}</li>`)
          .join("")}</ul>`;
      }
    }
  }

  card.innerHTML = `
    <div class="result-header">
      <h3 class="result-title">${title}</h3>
      <div class="result-actions">
        <button class="action-btn copy-btn" title="Copy to clipboard">
          <i class="fas fa-copy"></i>
        </button>
      </div>
    </div>
    <div class="result-content">${formatContent(formattedContent)}</div>
  `;

  // Add event listener for copy button
  setTimeout(() => {
    const copyBtn = card.querySelector(".copy-btn");
      copyBtn.addEventListener("click", () => {
        copyToClipboard(content);
        showToast("Copied to clipboard!");
      });
  }, 0);

  return card;
}

// Create feedback element for a specific task
function createFeedbackForTask(data, task) {
  const taskName = task
    .replace("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

  const feedbackDiv = document.createElement("div");
  feedbackDiv.className = "feedback-item";
  feedbackDiv.innerHTML = `
    <p>Rate "${taskName}":</p>
    <div>
      <button class="feedback-btn thumbs-up" data-task="${task}">
        <i class="fas fa-thumbs-up"></i>
      </button>
      <button class="feedback-btn thumbs-down" data-task="${task}">
        <i class="fas fa-thumbs-down"></i>
      </button>
    </div>
  `;

  // Add event listeners for feedback buttons
  const thumbsUp = feedbackDiv.querySelector(".thumbs-up");
  const thumbsDown = feedbackDiv.querySelector(".thumbs-down");

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

  return feedbackDiv;
}

// Format content for better display
function formatContent(content) {
  if (!content) return "No content available";

  // If content already has HTML formatting, return as is
  if (content.includes("<")) return content;

  // Replace line breaks with paragraph tags
  return content
    .split("\n\n")
    .map((para) => `<p>${para.replace(/\n/g, "<br>")}</p>`)
    .join("");
}

// Helper function to copy text to clipboard
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(
    () => {
      logger.log("Content copied to clipboard");
    },
    (err) => {
      logger.log(`Could not copy text: ${err}`);
    }
  );
}

// Show a toast notification
function showToast(message, duration = 2000) {
  // Remove existing toast if present
  const existingToast = document.querySelector(".toast");
  if (existingToast) {
    existingToast.remove();
  }

  // Create and show the toast
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  document.body.appendChild(toast);

  // Trigger animation
  setTimeout(() => {
    toast.classList.add("show");
  }, 10);

  // Hide after duration
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => {
      toast.remove();
    }, 300);
  }, duration);
}

// Helper to truncate text with ellipsis
function truncateText(text, maxLength) {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength) + "...";
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
      showToast("Feedback submitted!");
    })
    .catch((err) => {
      logger.log(`Error storing feedback: ${err.message}`);
      showToast("Failed to submit feedback", 3000);
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
