OrdonAI is an AI tool to help patients better understand and follow their prescriptions.
In France, patients often receive prescriptions via paper or platforms like Doctolib, and then have to manually interpret instructions, organize treatments, and remember when and how to take multiple medications. This process is often confusing and error-prone.
OrdonAI turns prescriptions into a clear, structured treatment plan. Users upload their prescription and are given a simple daily schedule showing what to take, when, and how, along with reminders. The goal is to reduce confusion, improve adherence, and make treatment management more reliable.

  ## Tech Stack
  - **Frontend** — Vanilla HTML/CSS/JS (single file, no
  framework)
  - **AI** — Claude Sonnet (claude-sonnet-4-5) via Anthropic API
   for prescription parsing
  - **Backend** — Vercel Serverless Function (`api/proxy.js`) to
   proxy API calls
  - **Export** — ICS calendar file generation (client-side)
  - **Hosting** — Vercel
