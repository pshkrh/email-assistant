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

document.getElementById("analyzeButton").addEventListener("click", () => {
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
    status.style.display = "block";
    status.textContent = "Please select at least one task.";
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

  chrome.runtime.sendMessage({ action: "fetchThread", tasks }, (response) => {
    if (chrome.runtime.lastError) {
      status.textContent = "Error: Could not analyze email.";
      logger.log(`Error: ${chrome.runtime.lastError.message}`);
      analyzeButton.disabled = false;
      return;
    }
    if (response.error) {
      status.textContent = response.error;
      logger.log(`Error: ${response.error}`);
      analyzeButton.disabled = false;
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
        status.textContent = "Error: No analysis data available.";
        logger.log("No analysis data found");
      }
      analyzeButton.disabled = false;
    });
  });
});

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
    });
}
