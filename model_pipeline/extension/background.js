chrome.action.onClicked.addListener((tab) => {
  // Ensure the content script is injected into the correct tab
  chrome.scripting.executeScript(
    {
      target: { tabId: tab.id },
      func: checkGmailOpen, // Function to check if Gmail is open
    },
    () => {
      chrome.tabs.sendMessage(tab.id, { action: "getThreadId" }, (response) => {
        if (chrome.runtime.lastError) {
          console.error("🚨 Error: ", chrome.runtime.lastError);
          return;
        }

        if (response && response.threadId) {
          console.log("✅ Thread ID detected:", response.threadId);

          // Here you should pass the email address
          const email = "user@example.com"; // Replace with actual email retrieval logic (could be fetched from Gmail if possible)

          fetchThreadData(response.threadId, email);
        } else {
          console.warn("❌ No thread ID found.");
        }
      });
    }
  );
});

// Function to ensure Gmail is open in the tab
function checkGmailOpen() {
  if (window.location.hostname.includes("mail.google.com")) {
    console.log("📧 Gmail is open!");
  } else {
    console.error("❌ Gmail is not open in this tab.");
  }
}

// Function to fetch thread data
function fetchThreadData(threadId, email) {
  fetch("http://127.0.0.1:5000/process_thread", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ threadId, email }),
  })
    .then((res) => res.json())
    .then((data) => {
      console.log("✅ Server Response:", data);
      chrome.storage.local.set({ threadData: data });
    })
    .catch((err) => console.error("🚨 Failed to send request:", err));
}
