# Chat App

Real-time browser chat application with public rooms and private direct messages.

The app serves a static frontend from `public/` on port `3000` and runs a WebSocket server on port `3001` for live messaging.

## Features

- Username-based login with duplicate-name protection
- Public chat rooms with default rooms: `general`, `random`, and `tech`
- Create and join new rooms from the UI
- Private direct messages between online users
- Live online user list
- In-memory message flow with system join/leave notifications
- Unread conversation highlighting in the sidebar

## Tech Stack

- Backend: Python, `asyncio`, `websockets`, and the built-in `http.server`
- Frontend: HTML, CSS, and vanilla JavaScript
- State storage: in-memory only

## Project Structure

```text
Chatt-App/
|-- public/
|   `-- index.html
|-- server.py
|-- package.json
`-- README.md
```

## Prerequisites

- Python 3.10 or newer recommended
- `pip` available in your environment

## Installation

1. Open the project folder.
2. Install the Python dependency:

```bash
pip install websockets
```

## Run Locally

Start the server:

```bash
python server.py
```

After startup:

- Frontend: `http://localhost:3000`


Open `http://localhost:3000` in your browser, enter a username, and start chatting.

## How It Works

- The HTTP server serves the frontend from `public/`.
- The WebSocket server manages connected clients, room membership, and private messages.
- Rooms and connected users are stored in memory, so all state resets when the server stops.

## Notes

- The current backend entry point is `server.py`.
- `package.json` exists in the repository, but the active server implementation is Python-based.
- There is no database or persistent message history.

## Possible Improvements

- Add persistent storage for users, rooms, and chat history
- Add authentication instead of username-only login
- Add reconnect handling and better offline state recovery
- Add tests and dependency pinning
