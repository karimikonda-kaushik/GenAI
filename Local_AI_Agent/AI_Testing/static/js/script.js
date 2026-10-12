document.addEventListener("DOMContentLoaded", () => {
  const mainDisplay = document.getElementById("main-display");
  const expressionDisplay = document.getElementById("expression-display");
  const errorBadge = document.getElementById("error-badge");
  const scientificPanel = document.getElementById("scientific-panel");
  const toggleSciBtn = document.getElementById("toggle-sci-btn");
  const historyPanel = document.getElementById("history-panel");
  const toggleHistoryBtn = document.getElementById("toggle-history-btn");
  const closeHistoryBtn = document.getElementById("close-history-btn");
  const clearHistoryBtn = document.getElementById("clear-history-btn");
  const historyList = document.getElementById("history-list");

  let expression = "";
  let lastEvaluated = false;

  // Initialize
  updateDisplay();
  loadHistory();

  // Button clicks
  document.querySelectorAll(".btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      const val = btn.dataset.val;

      handleAction(action, val);
    });
  });

  // Action dispatcher
  function handleAction(action, val) {
    clearError();

    switch (action) {
      case "num":
        appendNumber(val);
        break;
      case "op":
        appendOperator(val);
        break;
      case "func":
        appendFunction(val);
        break;
      case "paren":
        appendParen(val);
        break;
      case "clear":
        clearAll();
        break;
      case "backspace":
        backspace();
        break;
      case "calculate":
        calculate();
        break;
    }
    updateDisplay();
  }

  function appendNumber(val) {
    if (lastEvaluated) {
      expression = "";
      lastEvaluated = false;
    }
    // Prevent consecutive decimals in the current token
    if (val === ".") {
      const parts = expression.split(/[\+\−\×\÷\%\^\(\)\s]/);
      const currentToken = parts[parts.length - 1] || "";
      if (currentToken.includes(".")) return;
      if (currentToken === "") val = "0.";
    }
    expression += val;
  }

  function appendOperator(val) {
    lastEvaluated = false;
    if (expression === "") {
      if (val === "−") {
        expression = "-";
        return;
      }
      return;
    }
    const lastChar = expression.slice(-1);
    const ops = ["+", "−", "×", "÷", "%", "^", "-", "*", "/"];

    if (ops.includes(lastChar)) {
      expression = expression.slice(0, -1) + val;
    } else {
      expression += val;
    }
  }

  function appendFunction(fn) {
    if (lastEvaluated) {
      expression = "";
      lastEvaluated = false;
    }
    expression += fn;
  }

  function appendParen(paren) {
    if (lastEvaluated && paren === "(") {
      expression = "";
      lastEvaluated = false;
    }
    expression += paren;
  }

  function clearAll() {
    expression = "";
    expressionDisplay.textContent = "\u00A0";
    lastEvaluated = false;
    clearError();
  }

  function backspace() {
    if (lastEvaluated) {
      clearAll();
      return;
    }
    // Check if removing a function name (e.g. "sqrt(", "sin(")
    const funcs = ["sqrt(", "log10(", "log(", "sin(", "cos(", "tan(", "fact("];
    for (const f of funcs) {
      if (expression.endsWith(f)) {
        expression = expression.slice(0, -f.length);
        return;
      }
    }
    expression = expression.slice(0, -1);
  }

  function updateDisplay() {
    if (!expression) {
      mainDisplay.textContent = "0";
    } else {
      mainDisplay.textContent = expression;
    }
  }

  function showError(msg) {
    errorBadge.textContent = msg;
    errorBadge.classList.add("visible");
  }

  function clearError() {
    errorBadge.textContent = "";
    errorBadge.classList.remove("visible");
  }

  async function calculate() {
    if (!expression.trim()) return;

    const exprToSend = expression;
    try {
      const res = await fetch("/api/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expression: exprToSend }),
      });

      const data = await res.json();
      if (data.success) {
        expressionDisplay.textContent = exprToSend + " =";
        expression = String(data.result);
        lastEvaluated = true;
        updateDisplay();
        loadHistory();
      } else {
        showError(data.error || "Evaluation failed");
      }
    } catch (err) {
      showError("Connection error");
    }
  }

  // Keyboard navigation
  window.addEventListener("keydown", (e) => {
    if (e.key >= "0" && e.key <= "9") {
      handleAction("num", e.key);
    } else if (e.key === ".") {
      handleAction("num", ".");
    } else if (e.key === "+") {
      handleAction("op", "+");
    } else if (e.key === "-") {
      handleAction("op", "−");
    } else if (e.key === "*") {
      handleAction("op", "×");
    } else if (e.key === "/") {
      e.preventDefault();
      handleAction("op", "÷");
    } else if (e.key === "%") {
      handleAction("op", "%");
    } else if (e.key === "^") {
      handleAction("op", "^");
    } else if (e.key === "(" || e.key === ")") {
      handleAction("paren", e.key);
    } else if (e.key === "Enter" || e.key === "=") {
      e.preventDefault();
      handleAction("calculate");
    } else if (e.key === "Backspace") {
      handleAction("backspace");
    } else if (e.key === "Escape") {
      handleAction("clear");
    }
  });

  // Toggle scientific panel
  toggleSciBtn.addEventListener("click", () => {
    scientificPanel.classList.toggle("open");
    toggleSciBtn.classList.toggle("active");
  });

  // Toggle history drawer
  toggleHistoryBtn.addEventListener("click", () => {
    historyPanel.classList.toggle("hidden");
    toggleHistoryBtn.classList.toggle("active");
  });

  closeHistoryBtn.addEventListener("click", () => {
    historyPanel.classList.add("hidden");
    toggleHistoryBtn.classList.remove("active");
  });

  // History API
  async function loadHistory() {
    try {
      const res = await fetch("/api/history");
      const data = await res.json();
      if (data.success) {
        renderHistory(data.history);
      }
    } catch (err) {
      console.error("Failed to load history", err);
    }
  }

  function renderHistory(items) {
    if (!items || items.length === 0) {
      historyList.innerHTML = '<p class="empty-state">No calculations yet</p>';
      return;
    }

    historyList.innerHTML = "";
    items.forEach((item) => {
      const div = document.createElement("div");
      div.className = "history-item";
      div.innerHTML = `
        <div class="item-expr">${escapeHtml(item.expression)} =</div>
        <div class="item-res">${escapeHtml(item.result)}</div>
      `;
      div.addEventListener("click", () => {
        expression = item.result;
        expressionDisplay.textContent = item.expression + " =";
        lastEvaluated = true;
        updateDisplay();
      });
      historyList.appendChild(div);
    });
  }

  clearHistoryBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/history", { method: "DELETE" });
      const data = await res.json();
      if (data.success) {
        renderHistory([]);
      }
    } catch (err) {
      showError("Could not clear history");
    }
  });

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
