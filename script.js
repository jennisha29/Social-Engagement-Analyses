const header = document.querySelector("[data-header]");
const nav = document.querySelector("[data-nav]");
const navToggle = document.querySelector(".nav-toggle");
const year = document.querySelector("[data-year]");

if (year) {
  year.textContent = new Date().getFullYear();
}

const syncHeader = () => {
  if (!header) return;
  header.classList.toggle("is-scrolled", window.scrollY > 12);
};

syncHeader();
window.addEventListener("scroll", syncHeader, { passive: true });

if (nav && navToggle) {
  navToggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  nav.addEventListener("click", (event) => {
    if (event.target instanceof HTMLAnchorElement) {
      nav.classList.remove("is-open");
      navToggle.setAttribute("aria-expanded", "false");
    }
  });
}

const chatToggle = document.querySelector("[data-chat-toggle]");
const chatClose = document.querySelector("[data-chat-close]");
const chatPanel = document.querySelector("[data-chat-panel]");
const chatForm = document.querySelector("[data-chat-form]");
const chatInput = document.querySelector("[data-chat-input]");
const chatMessages = document.querySelector("[data-chat-messages]");
const quickPrompts = document.querySelectorAll("[data-prompt]");

const knowledgeBase = [
  {
    keywords: ["summary", "about", "intro", "who", "profile", "jennisha"],
    answer:
      "Jennisha Martin is a Boston-based Data Engineer and Applied AI builder with 3+ years of professional experience. She builds ETL pipelines, dimensional models, cloud analytics platforms, BI dashboards, and AI workflows that make data clean, reliable, and business-ready.",
  },
  {
    keywords: ["skills", "tools", "tech", "stack", "technology"],
    answer:
      "Jennisha works with Python, SQL, Java, JavaScript, Bash, Airflow, PySpark, Hadoop, HDFS, Databricks, dbt, AWS Glue, Snowpipe, Snowflake, Redshift, PostgreSQL, Power BI, Tableau, Looker Studio, Scikit-Learn, SpaCy, PyTorch, LangChain, LangGraph, RAG, Langfuse, LiteLLM, and Pinecone.",
  },
  {
    keywords: ["experience", "work", "roles", "jobs", "professional"],
    answer:
      "Jennisha has worked as an AI Engineer Intern at IpserLab and as a Data Engineer plus Data Engineer Intern at Infosys Limited. Her work includes voice assistants, RAG pipelines, ETL platforms, Redshift and Snowflake data marts, Airflow orchestration, SQL optimization, and executive dashboards.",
  },
  {
    keywords: ["ipserlab", "ai engineer", "voice", "mortgage", "livekit", "deepgram", "twilio", "langgraph"],
    answer:
      "At IpserLab, Jennisha built an AI voice assistant for mortgage prequalification using LiveKit, Deepgram, Twilio SIP, LangGraph, NLP intent classification, PostgreSQL checkpointing, LangChain, FastAPI, Node.js, Langfuse, Prometheus, and Grafana.",
  },
  {
    keywords: ["infosys", "data engineer", "etl", "erp", "tableau", "redshift"],
    answer:
      "At Infosys, Jennisha built large-scale ETL pipelines using AWS Glue, PySpark, HDFS, and SQL to ingest 10M+ ERP records into Snowflake, modeled Redshift data marts for 25+ workflows, optimized 50+ SQL queries, orchestrated 15+ Airflow pipelines, and shipped 25+ Tableau dashboards.",
  },
  {
    keywords: ["projects", "portfolio", "built", "project"],
    answer:
      "Jennisha’s featured projects are AutoMend, SupplyFlow, HealthSync, and TweetPulse. They cover autonomous MLOps remediation, AWS supply-chain analytics, healthcare claims pipelines, and real-time social media analytics.",
  },
  {
    keywords: ["automend", "mlops", "google", "incident", "bert", "llama"],
    answer:
      "AutoMend is Jennisha’s autonomous MLOps remediation platform. It won 3rd place at Google Boston and used BERT, Llama-3, Airflow, Ray, Polars, Docker, DVC, Fairlearn, and Slack alerting to reduce ML incident response time by 40%.",
  },
  {
    keywords: ["supplyflow", "supply", "chain", "aws", "logistics"],
    answer:
      "SupplyFlow is an AWS supply-chain analytics platform using S3, Lambda, Glue, Redshift, PySpark, and Power BI. Jennisha designed a serverless ETL pipeline and a nine-table snowflake-schema warehouse for profitability, carrier performance, and delivery-risk analytics.",
  },
  {
    keywords: ["healthsync", "healthcare", "medicare", "claims", "snowflake", "dbt"],
    answer:
      "HealthSync is a healthcare data platform that ingests CMS Medicare claims into a Snowflake star schema using medallion architecture, dbt models, and SQL transformations. It identifies opioid overprescription, duplicate claims, billing outliers, and provider benchmarks.",
  },
  {
    keywords: ["tweetpulse", "twitter", "social", "azure", "snowpipe", "sentiment"],
    answer:
      "TweetPulse is Jennisha’s real-time social media analytics pipeline. It streams Twitter feeds through Azure Blob Storage, EventGrid, and Snowpipe into Snowflake, then powers 30-minute auto-refresh dashboards for engagement, trending topics, and sentiment patterns.",
  },
  {
    keywords: ["education", "school", "degree", "northeastern", "anna"],
    answer:
      "Jennisha earned a Master’s in Computer Science from Northeastern University’s Khoury College of Computer Sciences in Boston and a Bachelor’s in Computer Science and Engineering from Anna University in Chennai, India.",
  },
  {
    keywords: ["award", "achievement", "recognition", "google", "rising", "insta"],
    answer:
      "Jennisha’s recognitions include 3rd Place at Google Boston for AutoMend, the Infosys Rising Star Award in 2023, and the Infosys Insta Award in 2022.",
  },
  {
    keywords: ["contact", "email", "phone", "linkedin", "github", "reach", "hire"],
    answer:
      "You can contact Jennisha at jennishamartin163@gmail.com or 857-506-3916. Her LinkedIn is linkedin.com/in/jennisha-martin and her GitHub is github.com/jennisha-martin.",
  },
  {
    keywords: ["resume", "cv", "download"],
    answer:
      "Jennisha’s resume is available from the Resume link in the navigation and the Download Resume button in the hero section.",
  },
  {
    keywords: ["why", "hire", "fit", "candidate", "strength"],
    answer:
      "Jennisha is a strong fit for data engineering and applied AI roles because she combines production ETL experience, cloud data warehousing, BI delivery, SQL performance optimization, MLOps projects, and modern AI workflow tooling. She can build the data foundation and connect it to measurable business outcomes.",
  },
];

const fallbackAnswer =
  "I can answer best about Jennisha’s resume, projects, skills, experience, education, awards, and contact details. Try asking: “What is AutoMend?”, “What are her data engineering skills?”, or “How can I contact Jennisha?”";

const normalize = (value) => value.toLowerCase().replace(/[^a-z0-9+#.\s-]/g, " ");

const getBotAnswer = (question) => {
  const normalizedQuestion = normalize(question);
  const ranked = knowledgeBase
    .map((entry) => ({
      entry,
      score: entry.keywords.reduce((total, keyword) => total + (normalizedQuestion.includes(keyword) ? 1 : 0), 0),
    }))
    .sort((left, right) => right.score - left.score);

  return ranked[0]?.score > 0 ? ranked[0].entry.answer : fallbackAnswer;
};

const addMessage = (text, sender) => {
  if (!chatMessages) return;
  const message = document.createElement("div");
  message.className = `message ${sender}`;
  message.textContent = text;
  chatMessages.appendChild(message);
  chatMessages.scrollTop = chatMessages.scrollHeight;
};

const openChat = () => {
  if (!chatPanel || !chatToggle) return;
  chatPanel.classList.add("is-open");
  chatPanel.setAttribute("aria-hidden", "false");
  chatToggle.setAttribute("aria-expanded", "true");
  chatToggle.style.display = "none";
  setTimeout(() => chatInput?.focus(), 80);
};

const closeChat = () => {
  if (!chatPanel || !chatToggle) return;
  chatPanel.classList.remove("is-open");
  chatPanel.setAttribute("aria-hidden", "true");
  chatToggle.setAttribute("aria-expanded", "false");
  chatToggle.style.display = "flex";
};

chatToggle?.addEventListener("click", openChat);
chatClose?.addEventListener("click", closeChat);

chatForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = chatInput?.value.trim();
  if (!question) return;
  addMessage(question, "user");
  chatInput.value = "";
  window.setTimeout(() => addMessage(getBotAnswer(question), "bot"), 180);
});

quickPrompts.forEach((button) => {
  button.addEventListener("click", () => {
    const prompt = button.getAttribute("data-prompt") || "";
    if (!prompt) return;
    addMessage(prompt, "user");
    window.setTimeout(() => addMessage(getBotAnswer(prompt), "bot"), 180);
  });
});
