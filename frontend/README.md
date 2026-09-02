<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Run and deploy your AI Studio app

This contains everything you need to run your app locally.

View your app in AI Studio: https://ai.studio/apps/d2a5b7e7-c094-4b84-bb4d-a260b665b483

## Run Locally

**Prerequisites:**  Node.js


1. Install dependencies:
   `npm install`
2. Configure optional frontend runtime values in [.env.local](.env.local) (for example `VITE_WS_URL`). WebSocket credentials are fetched from the backend and kept only in memory.
3. Run the app:
   `npm run dev`
