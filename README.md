# Send Video Message — OpenClaw skill

Your Openclaw agent can **send you a video message in chat**: a character speaks a script, using [Runway Character API]([https://dev.runwayml.com](https://runwayml.com/news/introducing-runway-characters)).

---

## Demo
You: "Send me a video message of your standup notes."
Your agent: reply with a video message.
<video src="https://github.com/user-attachments/assets/06d78388-68b2-4142-a60c-79e83eaee9a1" width="600" controls></video>

It works with many different characters. You can choose one by saying "Use the lobster/alien/cat image as the character", upload an image in the chat, or ask the agent to generate an image for you.

## Quick setup

1. **Ask your OpenClaw agent** to install this skill from ClawHub: **[https://clawhub.ai/yining1023/send-video-message](https://clawhub.ai/yining1023/send-video-message)**

2. **Create a Runway API key** at [dev.runwayml.com](https://dev.runwayml.com) and give it to your agent (it needs to be available as **`RUNWAY_API_SECRET`** where the agent runs).

When signing up, you will get 600 free credits = 30 minutes of video messages.

[Get started with Runway API key](https://docs.dev.runwayml.com/characters/quickstart/#2-create-a-new-api-key)
Go to the Manage tab in the top bar, then click the New API key button in the top-right corner.

<img src="https://runway-static-assets.s3.us-east-1.amazonaws.com/devportal/avatars/quickstart/3.png" width="600" />

Give your key a name and share it with your OpenClaw agent

<img src="https://runway-static-assets.s3.us-east-1.amazonaws.com/devportal/avatars/quickstart/4.png" width="600" />

3. **Ask your agent to send you video messages.** The agent follows the installed skill’s instructions.
In the chat app, send messages like:

```
Send me a video recap of what you did today.
```
```
What is on my to-do list today? Send me a video message.
```
```
Send me a video message about the weather every day at 9am.
```
```
Send me a video message and explain this blog post: https://runwayml.com/product/characters
```
```
Summarize this PR in a video message: https://github.com/org/repo/pull/42
```
```
Send me a video walkthrough of what changed in the last deploy.
```
```
Record a video congratulating the team on shipping v2.0.
```

---

## Source & docs

- [ClawHub skill: Send Video Message](https://clawhub.ai/yining1023/send-video-message)
- [Runway Characters API](https://runwayml.com/product/characters)
- [Runway dev portal](https://dev.runwayml.com/)
